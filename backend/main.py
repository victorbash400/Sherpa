import json
import os
import asyncio
from contextlib import suppress

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from google.adk.agents import LiveRequestQueue, RunConfig
from google.adk.agents.run_config import StreamingMode
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from pydantic import BaseModel, Field

os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "true")
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "sherpa-20260813")
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "global")

from backend.credential_store import load_gemini_api_key

voice_api_key = load_gemini_api_key()
if voice_api_key:
    os.environ.setdefault("GEMINI_API_KEY", voice_api_key)

from backend.agents.sherpa_agent import sherpa_app
from backend.agents.voice_agent import voice_app

sessions = InMemorySessionService()
runner = Runner(app=sherpa_app, session_service=sessions)
voice_sessions = InMemorySessionService()
voice_runner = Runner(app=voice_app, session_service=voice_sessions)

app = FastAPI(title="Sherpa API")
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
                        "result": response.response or {},
                    }
                )
        yield sse({"type": "done"})
    except Exception as error:
        yield sse({"type": "error", "error": str(error)})


@app.websocket("/voice/{session_id}")
async def voice(websocket: WebSocket, session_id: str, voice: str = "Kore") -> None:
    await websocket.accept()
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
    session = await voice_sessions.get_session(
        app_name="sherpa_voice",
        user_id="local-user",
        session_id=session_id,
    )
    if not session:
        await voice_sessions.create_session(
            app_name="sherpa_voice",
            user_id="local-user",
            session_id=session_id,
        )
    requests = LiveRequestQueue()
    config = RunConfig(
        streaming_mode=StreamingMode.BIDI,
        response_modalities=[types.Modality.AUDIO],
        input_audio_transcription=types.AudioTranscriptionConfig(),
        output_audio_transcription=types.AudioTranscriptionConfig(),
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice)
            )
        ),
    )
    await websocket.send_json({"type": "ready"})

    async def receive_audio() -> None:
        try:
            while True:
                message = await websocket.receive()
                if audio := message.get("bytes"):
                    requests.send_realtime(
                        types.Blob(data=audio, mime_type="audio/pcm;rate=16000")
                    )
                elif text := message.get("text"):
                    payload = json.loads(text)
                    if payload.get("type") == "preview":
                        requests.send_content(
                            types.Content(
                                role="user",
                                parts=[types.Part.from_text(
                                    text="Say only: Hi, I'm Sherpa. Nice to meet you."
                                )],
                            )
                        )
                elif message.get("type") == "websocket.disconnect":
                    break
        except WebSocketDisconnect:
            pass
        finally:
            requests.close()

    async def send_events() -> None:
        try:
            async for event in voice_runner.run_live(
                user_id="local-user",
                session_id=session_id,
                live_request_queue=requests,
                run_config=config,
            ):
                if event.error_message:
                    await websocket.send_json({"type": "error", "error": event.error_message})
                if event.interrupted:
                    await websocket.send_json({"type": "interrupted"})
                if event.input_transcription and event.input_transcription.text:
                    await websocket.send_json(
                        {"type": "input_transcript", "text": event.input_transcription.text}
                    )
                if event.output_transcription and event.output_transcription.text:
                    await websocket.send_json(
                        {"type": "output_transcript", "text": event.output_transcription.text}
                    )
                if event.content:
                    for part in event.content.parts or []:
                        if part.inline_data and part.inline_data.data:
                            await websocket.send_bytes(part.inline_data.data)
                if event.turn_complete:
                    await websocket.send_json({"type": "turn_complete"})
        except Exception as error:
            await websocket.send_json({"type": "error", "error": str(error)})

    receiver = asyncio.create_task(receive_audio())
    sender = asyncio.create_task(send_events())
    done, pending = await asyncio.wait(
        {receiver, sender}, return_when=asyncio.FIRST_COMPLETED
    )
    requests.close()
    for task in pending:
        task.cancel()
    for task in done | pending:
        with suppress(asyncio.CancelledError, WebSocketDisconnect):
            await task


def sse(event: dict[str, object]) -> str:
    return f"data: {json.dumps(event, default=str)}\n\n"
