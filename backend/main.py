import json
import os
import asyncio
import logging
import traceback
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from google import genai
from google.adk.agents import RunConfig
from google.adk.agents.run_config import StreamingMode
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from pydantic import BaseModel, Field

os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "true")
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "sherpa-20260813")
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "global")

logging.basicConfig(
    level=os.getenv("SHERPA_LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("sherpa.voice")

from backend.credential_store import load_gemini_api_key

voice_api_key = load_gemini_api_key()
if voice_api_key:
    os.environ.setdefault("GEMINI_API_KEY", voice_api_key)

from backend.agents.sherpa_agent import sherpa_app, sherpa_computer_tools
from backend.agents.voice_agent import VOICE_INSTRUCTION, VOICE_MODEL, VOICE_TOOLS
from backend.sherpa_tasks import sherpa_tasks

sessions = InMemorySessionService()
runner = Runner(app=sherpa_app, session_service=sessions)

@asynccontextmanager
async def lifespan(_: FastAPI):
    await asyncio.gather(
        sherpa_computer_tools.get_tools(),
    )
    yield
    await sherpa_tasks.close()
    await sherpa_computer_tools.close()


app = FastAPI(title="Sherpa API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

LIVE_VOICES = {
    "Kore", "Aoede", "Leda", "Zephyr", "Puck", "Charon", "Fenrir", "Orus", "Sulafat"
}


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=1)
    message: str = Field(min_length=1)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/chat")
async def chat(body: ChatRequest) -> StreamingResponse:
    session = await sessions.get_session(
        app_name="sherpa",
        user_id="local-user",
        session_id=body.session_id,
    )
    if not session:
        await sessions.create_session(
            app_name="sherpa",
            user_id="local-user",
            session_id=body.session_id,
        )
    return StreamingResponse(
        stream_chat(body),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )


async def stream_chat(body: ChatRequest):
    try:
        message = types.Content(
            role="user",
            parts=[types.Part.from_text(text=body.message)],
        )
        config = RunConfig(streaming_mode=StreamingMode.SSE)
        async for event in runner.run_async(
            user_id="local-user",
            session_id=body.session_id,
            new_message=message,
            run_config=config,
        ):
            if event.error_message:
                yield sse({"type": "error", "error": event.error_message})
                continue
            if event.partial and event.content:
                for part in event.content.parts or []:
                    if part.text:
                        yield sse(
                            {
                                "type": "reasoning" if part.thought else "content",
                                "content": part.text,
                            }
                        )
                continue
            for call in event.get_function_calls():
                yield sse(
                    {
                        "type": "tool_call",
                        "id": call.id or call.name,
                        "name": call.name,
                        "args": call.args or {},
                    }
                )
            for response in event.get_function_responses():
                yield sse(
                    {
                        "type": "tool_response",
                        "id": response.id or response.name,
                        "name": response.name,
                        "result": public_tool_result(response.response),
                    }
                )
        yield sse({"type": "done"})
    except Exception as error:
        yield sse({"type": "error", "error": str(error)})


@app.websocket("/voice/{session_id}")
async def voice(websocket: WebSocket, session_id: str, voice: str = "Kore") -> None:
    await websocket.accept()
    logger.info("session.accepted session=%s voice=%s", session_id, voice)
    if voice not in LIVE_VOICES:
        await websocket.send_json({"type": "error", "error": "Unsupported Sherpa voice."})
        await websocket.close(code=1008)
        return
    if not (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")):
        await websocket.send_json(
            {"type": "error", "error": "GEMINI_API_KEY is required for Sherpa voice."}
        )
        await websocket.close(code=1011)
        return
    audio_frames = 0
    audio_bytes = 0
    config = types.LiveConnectConfig(
        response_modalities=[types.Modality.AUDIO],
        input_audio_transcription=types.AudioTranscriptionConfig(),
        output_audio_transcription=types.AudioTranscriptionConfig(),
        realtime_input_config=types.RealtimeInputConfig(
            activity_handling=types.ActivityHandling.START_OF_ACTIVITY_INTERRUPTS,
            automatic_activity_detection=types.AutomaticActivityDetection(
                disabled=False,
                start_of_speech_sensitivity=types.StartSensitivity.START_SENSITIVITY_HIGH,
                prefix_padding_ms=20,
                end_of_speech_sensitivity=types.EndSensitivity.END_SENSITIVITY_LOW,
                silence_duration_ms=300,
            ),
        ),
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice)
            )
        ),
        thinking_config=types.ThinkingConfig(thinking_budget=0),
        enable_affective_dialog=True,
        system_instruction=VOICE_INSTRUCTION,
        tools=VOICE_TOOLS,
    )
    client = genai.Client(
        api_key=os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"),
        vertexai=False,
    )

    async with client.aio.live.connect(model=VOICE_MODEL, config=config) as live:
        await websocket.send_json({"type": "ready"})
        logger.info("session.ready session=%s model=%s tools=3", session_id, VOICE_MODEL)
        pending_calls: dict[str, dict[str, str]] = {}

        async def receive_audio() -> None:
            nonlocal audio_frames, audio_bytes
            try:
                while True:
                    message = await websocket.receive()
                    if audio := message.get("bytes"):
                        audio_frames += 1
                        audio_bytes += len(audio)
                        if audio_frames == 1 or audio_frames % 250 == 0:
                            logger.info(
                                "audio.received session=%s frames=%d bytes=%d frame_bytes=%d",
                                session_id, audio_frames, audio_bytes, len(audio),
                            )
                        await live.send_realtime_input(
                            audio=types.Blob(data=audio, mime_type="audio/pcm;rate=16000")
                        )
                    elif text := message.get("text"):
                        payload = json.loads(text)
                        if payload.get("type") == "preview":
                            await live.send_realtime_input(
                                text="Say only: Hi, I'm Sherpa. Nice to meet you."
                            )
                    elif message.get("type") == "websocket.disconnect":
                        break
            except WebSocketDisconnect:
                logger.info("client.disconnected session=%s", session_id)
            except Exception:
                logger.exception("audio.receiver_failed session=%s", session_id)

        async def send_function_response(
            call_id: str,
            name: str,
            response: dict,
            scheduling: types.FunctionResponseScheduling | None = None,
        ) -> None:
            await live.send_tool_response(function_responses=[types.FunctionResponse(
                id=call_id,
                name=name,
                response=response,
                scheduling=scheduling,
            )])

        async def handle_function_call(call: types.FunctionCall) -> None:
            call_id = call.id or call.name or "unknown"
            args = call.args or {}
            logger.info(
                "model.tool_call session=%s call=%s name=%s args=%s",
                session_id, call_id, call.name, json.dumps(args, default=str),
            )
            if call.name == "delegate_task":
                instruction = str(args.get("instruction", "")).strip()
                if not instruction:
                    await send_function_response(
                        call_id, call.name, {"error": "instruction is required"},
                        types.FunctionResponseScheduling.WHEN_IDLE,
                    )
                    return
                task = sherpa_tasks.start(session_id, instruction)
                pending_calls[task.id] = {
                    "call_id": call_id,
                    "name": call.name,
                    "instruction": instruction,
                }
                logger.info("task.delegated session=%s task=%s call=%s", session_id, task.id, call_id)
                return
            task_id = str(args.get("task_id", ""))
            task = sherpa_tasks.get(task_id)
            if call.name == "get_task_status":
                result = (
                    {"task_id": task.id, "status": task.status, "summary": task.summary}
                    if task else {"task_id": task_id, "status": "not_found"}
                )
                await send_function_response(call_id, call.name, result)
            elif call.name == "cancel_task":
                cancelled = sherpa_tasks.cancel(task_id)
                await send_function_response(call_id, call.name, {
                    "task_id": task_id,
                    "status": "cancelled" if cancelled else "not_running",
                })
            else:
                await send_function_response(call_id, call.name or "unknown", {
                    "error": "Unknown voice tool",
                })

        async def send_events() -> None:
            try:
                while True:
                    async for response in live.receive():
                        if response.tool_call:
                            for call in response.tool_call.function_calls or []:
                                await handle_function_call(call)
                        if response.tool_call_cancellation:
                            cancelled_ids = set(response.tool_call_cancellation.ids or [])
                            for task_id, pending in list(pending_calls.items()):
                                if pending["call_id"] in cancelled_ids:
                                    sherpa_tasks.cancel(task_id)
                        content = response.server_content
                        if not content:
                            continue
                        if content.interrupted:
                            await websocket.send_json({"type": "interrupted"})
                        if content.input_transcription and content.input_transcription.text:
                            await websocket.send_json({
                                "type": "input_transcript",
                                "text": content.input_transcription.text,
                            })
                        if content.output_transcription and content.output_transcription.text:
                            await websocket.send_json({
                                "type": "output_transcript",
                                "text": content.output_transcription.text,
                            })
                        if content.model_turn:
                            for part in content.model_turn.parts or []:
                                if part.inline_data and part.inline_data.data:
                                    await websocket.send_bytes(part.inline_data.data)
                        if content.turn_complete:
                            logger.info("model.turn_complete session=%s", session_id)
                            await websocket.send_json({"type": "turn_complete"})
            except Exception as error:
                logger.error(
                    "model.live_failed session=%s type=%s error=%s\n%s",
                    session_id, type(error).__name__, error, traceback.format_exc(),
                )
                with suppress(RuntimeError, WebSocketDisconnect):
                    await websocket.send_json({
                        "type": "error",
                        "error": f"Voice session failed: {type(error).__name__}: {error}",
                    })

        async def relay_sherpa_events() -> None:
            event_queue = sherpa_tasks.subscribe(session_id)
            terminal_events = {"task_completed", "task_failed", "task_cancelled"}
            while True:
                event = await event_queue.get()
                task_id = str(event.get("task_id", ""))
                logger.info(
                    "task.event session=%s task=%s type=%s message=%s",
                    session_id, task_id, event.get("type"), event.get("message"),
                )
                if event["type"] in {"tool_call", "tool_response"}:
                    await websocket.send_json(event)
                if event["type"] not in terminal_events:
                    continue
                pending = pending_calls.pop(task_id, None)
                if not pending:
                    continue
                await send_function_response(
                    pending["call_id"],
                    pending["name"],
                    {
                        "task_id": task_id,
                        "originating_instruction": pending["instruction"],
                        "status": event["type"].removeprefix("task_"),
                        "result": event.get("message", ""),
                    },
                    types.FunctionResponseScheduling.WHEN_IDLE,
                )
                logger.info(
                    "task.result_sent session=%s task=%s call=%s scheduling=WHEN_IDLE",
                    session_id, task_id, pending["call_id"],
                )

        receiver = asyncio.create_task(receive_audio())
        sender = asyncio.create_task(send_events())
        relay = asyncio.create_task(relay_sherpa_events())
        done, pending = await asyncio.wait(
            {receiver, sender, relay}, return_when=asyncio.FIRST_COMPLETED
        )
        for task in pending:
            task.cancel()
        for task in done | pending:
            with suppress(asyncio.CancelledError, WebSocketDisconnect):
                await task


def sse(event: dict[str, object]) -> str:
    return f"data: {json.dumps(event, default=str)}\n\n"


def public_tool_result(result: dict | None) -> dict[str, str]:
    if result and (
        result.get("isError")
        or result.get("error")
        or result.get("status") == "failed"
    ):
        return {"status": "failed"}
    return {"status": "done"}
