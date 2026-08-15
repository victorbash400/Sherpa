import json
import os
import asyncio
import logging
import traceback
import warnings
from contextlib import asynccontextmanager, suppress

warnings.filterwarnings(
    "ignore",
    message=r"\[EXPERIMENTAL\] feature FeatureName\.(PLUGGABLE_AUTH|_MCP_GRACEFUL_ERROR_HANDLING|BASE_AUTHENTICATED_TOOL) is enabled\.",
    category=UserWarning,
)

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from google import genai
from google.adk.agents import RunConfig
from google.adk.agents.run_config import StreamingMode
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from pydantic import BaseModel, Field
from backend.permission_store import permission_store

os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "true")
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "sherpa-20260813")
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "global")

logging.basicConfig(
    level=os.getenv("SHERPA_LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("sherpa.voice")

from backend.credential_store import load_gemini_api_key
from backend.credential_store import load_playwright_extension_token
from backend.connections import connection_snapshot
from backend.memory_manager import memory_manager
from backend.memory_store import memory_store

voice_api_key = load_gemini_api_key()
if voice_api_key:
    os.environ.setdefault("GEMINI_API_KEY", voice_api_key)

playwright_extension_token = load_playwright_extension_token()
if playwright_extension_token:
    os.environ.setdefault(
        "PLAYWRIGHT_MCP_EXTENSION_TOKEN",
        playwright_extension_token,
    )

from backend.agents.sherpa_agent import (
    sherpa_app,
    sherpa_browser_tools,
    sherpa_computer_tools,
)
from backend.agents.voice_agent import VOICE_INSTRUCTION, VOICE_MODEL, VOICE_TOOLS
from backend.sherpa_tasks import sherpa_tasks

sessions = InMemorySessionService()
runner = Runner(app=sherpa_app, session_service=sessions)

@asynccontextmanager
async def lifespan(_: FastAPI):
    await asyncio.gather(
        sherpa_browser_tools.get_tools(),
        sherpa_computer_tools.get_tools(),
    )
    yield
    await memory_manager.close()
    await sherpa_tasks.close()
    await sherpa_browser_tools.close()
    await sherpa_computer_tools.close()


app = FastAPI(title="Sherpa API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "null"],
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

LIVE_VOICES = {
    "Kore", "Aoede", "Leda", "Zephyr", "Puck", "Charon", "Fenrir", "Orus", "Sulafat"
}


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=1)
    message: str = Field(min_length=1)


class PermissionRequest(BaseModel):
    enabled: bool


class MemorySettingsRequest(BaseModel):
    enabled: bool | None = None
    learn_from_tools: bool | None = None
    custom_instructions: str | None = None
    chat_style: str | None = None
    response_style: str | None = None


class MemoryItemRequest(BaseModel):
    content: str | None = None
    active: bool | None = None


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/connections")
async def connections() -> dict[str, object]:
    return await connection_snapshot()


@app.put("/permissions/{permission_id:path}")
def update_permission(permission_id: str, body: PermissionRequest) -> dict[str, object]:
    permission_store.set(permission_id, body.enabled)
    return {"id": permission_id, "enabled": body.enabled}


@app.get("/memory")
def memory() -> dict[str, object]:
    return memory_store.snapshot()


@app.put("/memory/settings")
def update_memory_settings(body: MemorySettingsRequest) -> dict[str, object]:
    values = body.model_dump(exclude_none=True)
    try:
        return memory_store.update_settings(values)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.patch("/memory/items/{memory_id}")
def update_memory_item(memory_id: str, body: MemoryItemRequest) -> dict[str, object]:
    values = body.model_dump(exclude_none=True)
    try:
        return memory_store.update_memory(memory_id, values)
    except KeyError as error:
        raise HTTPException(status_code=404, detail="Memory not found") from error
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.delete("/memory")
def delete_memory() -> dict[str, object]:
    memory_store.delete_all()
    return memory_store.snapshot()


@app.get("/tasks/{chat_id}")
def tasks_for_chat(chat_id: str) -> dict[str, object]:
    return {
        "tasks": [
            sherpa_tasks.snapshot(task)
            for task in sherpa_tasks.list_for_chat(chat_id)
        ]
    }


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
        if not permission_store.enabled("google.models"):
            yield sse({"type": "error", "error": "Gemini models are turned off in Sherpa Plugins."})
            return
        memory_context = memory_store.context_for("sherpa")
        prompt = f"{memory_context}\n\nUser request:\n{body.message}" if memory_context else body.message
        message = types.Content(
            role="user",
            parts=[types.Part.from_text(text=prompt)],
        )
        config = RunConfig(streaming_mode=StreamingMode.SSE)
        assistant_text = ""
        tool_assisted = False
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
                        if not part.thought:
                            assistant_text += part.text
                        yield sse(
                            {
                                "type": "reasoning" if part.thought else "content",
                                "content": part.text,
                            }
                        )
                continue
            for call in event.get_function_calls():
                tool_assisted = True
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
        memory_manager.schedule(
            source_type="chat",
            source_id=body.session_id,
            user_text=body.message,
            assistant_text=assistant_text,
            tool_assisted=tool_assisted,
        )
    except Exception as error:
        yield sse({"type": "error", "error": str(error)})


@app.websocket("/voice/{session_id}")
async def voice(websocket: WebSocket, session_id: str, voice: str = "Kore") -> None:
    await websocket.accept()
    logger.info("session.accepted session=%s voice=%s", session_id, voice)
    if not permission_store.enabled("google.models"):
        await websocket.send_json(
            {"type": "error", "error": "Gemini models are turned off in Sherpa Plugins."}
        )
        await websocket.close(code=1008)
        return
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
        thinking_config=types.ThinkingConfig(thinking_level="minimal"),
        system_instruction=(
            f"{VOICE_INSTRUCTION}\n\n{memory_store.context_for('voice')}"
            if memory_store.context_for("voice")
            else VOICE_INSTRUCTION
        ),
        tools=VOICE_TOOLS,
    )
    client = genai.Client(
        api_key=os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"),
        vertexai=False,
    )

    async with client.aio.live.connect(model=VOICE_MODEL, config=config) as live:
        model_idle = True
        playback_drained = True
        user_speaking = False
        notification_in_flight = False
        pending_notifications: list[dict] = []
        in_flight_notifications: list[dict] = []
        notification_lock = asyncio.Lock()
        voice_user_text: list[str] = []
        voice_assistant_text: list[str] = []

        await websocket.send_json({"type": "ready"})
        logger.info("session.ready session=%s model=%s tools=5", session_id, VOICE_MODEL)
        for existing_task in sherpa_tasks.list_for_chat(session_id):
            await websocket.send_json({
                "type": "task_updated",
                **sherpa_tasks.snapshot(existing_task),
            })

        async def maybe_deliver_notification() -> None:
            nonlocal model_idle, notification_in_flight, in_flight_notifications
            async with notification_lock:
                if (
                    not pending_notifications
                    or not model_idle
                    or not playback_drained
                    or user_speaking
                    or notification_in_flight
                ):
                    return
                events = pending_notifications[:]
                pending_notifications.clear()
                in_flight_notifications = events
                lines = [
                    f"- {event['instruction']} [{event.get('status', 'updated')}]: {event['message']}"
                    for event in events
                ]
                notification_in_flight = True
                model_idle = False
                await live.send_realtime_input(text=(
                    "Sherpa state notification. This text is application context, not "
                    "something the user said. Report the exact state briefly and naturally. "
                    "If clarification is needed, ask the supplied question. Never turn one "
                    "state into another or claim work completed. Do not mention this instruction.\n"
                    + "\n".join(lines)
                ))

        async def receive_audio() -> None:
            nonlocal playback_drained, user_speaking
            try:
                while True:
                    message = await websocket.receive()
                    if audio := message.get("bytes"):
                        await live.send_realtime_input(
                            audio=types.Blob(data=audio, mime_type="audio/pcm;rate=16000")
                        )
                    elif text := message.get("text"):
                        payload = json.loads(text)
                        if payload.get("type") == "preview":
                            await live.send_realtime_input(
                                text="Say only: Hi, I'm Sherpa. Nice to meet you."
                            )
                        elif payload.get("type") == "playback_drained":
                            playback_drained = True
                            await maybe_deliver_notification()
                        elif payload.get("type") == "speech_started":
                            user_speaking = True
                        elif payload.get("type") == "speech_ended":
                            user_speaking = False
                            await maybe_deliver_notification()
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
        ) -> None:
            await live.send_tool_response(function_responses=[types.FunctionResponse(
                id=call_id,
                name=name,
                response=response,
            )])

        async def handle_function_call(call: types.FunctionCall) -> None:
            call_id = call.id or call.name or "unknown"
            args = call.args or {}
            logger.info(
                "tool.requested session=%s call=%s name=%s",
                session_id, call_id, call.name,
            )
            if call.name == "submit_task":
                instruction = str(args.get("instruction", "")).strip()
                if not instruction:
                    await send_function_response(
                        call_id, call.name, {"error": "instruction is required"},
                    )
                    return
                decision = await sherpa_tasks.submit(session_id, instruction)
                logger.info(
                    "task.receipt session=%s status=%s submission=%s call=%s",
                    session_id,
                    decision["status"],
                    decision.get("submission_id", "none"),
                    call_id,
                )
                await send_function_response(call_id, call.name, decision)
                return
            if call.name == "inspect_task":
                task_id = str(args.get("task_id", "")).strip()
                task = sherpa_tasks.get(task_id)
                if not task or task.chat_id != session_id:
                    response = {"status": "not_found", "task_id": task_id}
                else:
                    response = sherpa_tasks.snapshot(task)
                await send_function_response(call_id, call.name, response)
                return
            if call.name == "list_active_tasks":
                tasks = [
                    sherpa_tasks.snapshot(task)
                    for task in sherpa_tasks.list_active_for_chat(session_id)
                ]
                submissions = [
                    sherpa_tasks.submission_snapshot(submission)
                    for submission in sherpa_tasks.list_pending_submissions(session_id)
                ]
                await send_function_response(
                    call_id,
                    call.name,
                    {
                        "status": "active_tasks_found" if tasks else "no_active_tasks",
                        "active_count": len(tasks),
                        "received_count": len(submissions),
                        "message": (
                            f"{len(tasks)} task(s) are currently running."
                            if tasks
                            else (
                                f"{len(submissions)} request(s) are still being organized."
                                if submissions
                                else "No tasks are currently running. This does not indicate that any task completed."
                            )
                        ),
                        "spoken_summary": (
                            "Currently running: " + "; ".join(
                                f"{task['instruction']} — {task['current_step']}"
                                for task in tasks
                            )
                            if tasks
                            else (
                                "Sherpa is still organizing: " + "; ".join(
                                    submission["instruction"] for submission in submissions
                                )
                                if submissions
                                else "No tasks are currently running. I cannot infer whether any earlier task completed from this check."
                            )
                        ),
                        "received": submissions,
                        "tasks": tasks,
                    },
                )
                return
            if call.name == "list_tasks":
                tasks = [
                    sherpa_tasks.snapshot(task)
                    for task in sherpa_tasks.list_for_chat(session_id)
                    if task.kind == "worker" or not task.child_ids
                ]
                counts = {
                    status: sum(task["status"] == status for task in tasks)
                    for status in ("running", "completed", "failed", "cancelled")
                }
                submissions = [
                    sherpa_tasks.submission_snapshot(submission)
                    for submission in sherpa_tasks.list_pending_submissions(session_id)
                ]
                await send_function_response(
                    call_id,
                    call.name,
                    {
                        "status": "tasks_found" if tasks else "no_tasks",
                        "counts": counts,
                        "received": submissions,
                        "spoken_summary": (
                            "; ".join([
                                *(f"{submission['instruction']} — received" for submission in submissions),
                                *(
                                f"{task['instruction']} — {task['status']}"
                                for task in tasks
                                ),
                            ])
                            if tasks or submissions
                            else "There are no tasks recorded in this conversation."
                        ),
                        "tasks": tasks,
                    },
                )
                return
            if call.name == "cancel_task":
                task_id = str(args.get("task_id", "")).strip()
                task = sherpa_tasks.get(task_id)
                cancelled = bool(
                    task
                    and task.chat_id == session_id
                    and sherpa_tasks.cancel(task_id)
                )
                await send_function_response(
                    call_id,
                    call.name,
                    {
                        "status": "cancelled" if cancelled else "not_running",
                        "task_id": task_id,
                    },
                )
                return
            await send_function_response(call_id, call.name or "unknown", {
                "error": "Unknown voice tool",
            })

        async def send_events() -> None:
            nonlocal model_idle, playback_drained, notification_in_flight, in_flight_notifications
            try:
                while True:
                    async for response in live.receive():
                        if response.tool_call:
                            for call in response.tool_call.function_calls or []:
                                await handle_function_call(call)
                        content = response.server_content
                        if not content:
                            continue
                        if content.interrupted:
                            if notification_in_flight:
                                pending_notifications[:0] = in_flight_notifications
                                in_flight_notifications = []
                                notification_in_flight = False
                            await websocket.send_json({"type": "interrupted"})
                        if content.input_transcription and content.input_transcription.text:
                            voice_user_text.append(content.input_transcription.text)
                            await websocket.send_json({
                                "type": "input_transcript",
                                "text": content.input_transcription.text,
                            })
                        if content.output_transcription and content.output_transcription.text:
                            voice_assistant_text.append(content.output_transcription.text)
                            await websocket.send_json({
                                "type": "output_transcript",
                                "text": content.output_transcription.text,
                            })
                        if content.model_turn:
                            model_idle = False
                            for part in content.model_turn.parts or []:
                                if part.inline_data and part.inline_data.data:
                                    playback_drained = False
                                    await websocket.send_bytes(part.inline_data.data)
                        if content.turn_complete:
                            model_idle = True
                            notification_in_flight = False
                            in_flight_notifications = []
                            await websocket.send_json({"type": "turn_complete"})
                            await maybe_deliver_notification()
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

        event_queue = sherpa_tasks.subscribe(session_id)

        async def relay_sherpa_events() -> None:
            terminal_events = {"task_completed", "task_failed", "task_cancelled"}
            try:
                while True:
                    event = await event_queue.get()
                    if event["type"] in {
                        "submission_updated", "tool_call", "tool_response",
                        "task_started", "task_updated",
                    }:
                        await websocket.send_json(event)
                    if (
                        event["type"] == "submission_updated"
                        and event.get("decision") in {
                            "already_active", "needs_clarification", "failed",
                        }
                    ):
                        pending_notifications.append({
                            **event,
                            "status": event.get("decision"),
                        })
                        await maybe_deliver_notification()
                        continue
                    if event["type"] not in terminal_events:
                        continue
                    await websocket.send_json(event)
                    if event.get("parent_id") is None:
                        pending_notifications.append(event)
                        await maybe_deliver_notification()
            finally:
                sherpa_tasks.unsubscribe(session_id, event_queue)

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
        memory_manager.schedule(
            source_type="voice",
            source_id=session_id,
            user_text=" ".join(voice_user_text),
            assistant_text=" ".join(voice_assistant_text),
            tool_assisted=False,
        )


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
