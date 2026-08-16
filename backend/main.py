import json
import os
import asyncio
import html
import logging
import re
import time
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from urllib.parse import urlparse

from backend.logging_config import add_token_usage, configure_logging, log_text

configure_logging()

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response, StreamingResponse
import httpx
from google import genai
from google.adk.agents import RunConfig
from google.adk.agents.run_config import StreamingMode
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from backend.permission_store import permission_store

load_dotenv(Path(__file__).with_name(".env"))

os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "true")
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "sherpa-20260813")
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "global")

logger = logging.getLogger("sherpa.voice")
chat_logger = logging.getLogger("sherpa.conversation")

from backend.credential_store import load_gemini_api_key
from backend.credential_store import load_playwright_extension_token
from backend.connections import connection_snapshot
from backend.google_auth import GoogleConnection, google_auth
from backend.memory_manager import memory_manager
from backend.memory_store import memory_store
from backend.skill_store import skill_store

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
    sherpa_google_tools,
)
from backend.agents.voice_agent import VOICE_INSTRUCTION, VOICE_MODEL
from backend.sherpa_tasks import sherpa_tasks
from backend.tools.voice_tools import VOICE_TOOLS, handle_voice_tool_call
from backend.voice_notifications import task_state_notification
from backend.tools.google_tools import run_with_google_tool_scope

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
    await asyncio.gather(*(toolset.close() for toolset in sherpa_google_tools))


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


class ChatTitleRequest(BaseModel):
    user_message: str = Field(min_length=1, max_length=8_000)
    assistant_message: str = Field(min_length=1, max_length=8_000)


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


class SkillRequest(BaseModel):
    instructions: str = Field(min_length=1, max_length=30_000)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/connections")
async def connections() -> dict[str, object]:
    return await connection_snapshot()


connection_event_queues: set[asyncio.Queue[dict[str, object]]] = set()


async def emit_connection_event(event: dict[str, object]) -> None:
    for queue in tuple(connection_event_queues):
        await queue.put(dict(event))


@app.get("/connections/events")
async def connection_events() -> StreamingResponse:
    queue: asyncio.Queue[dict[str, object]] = asyncio.Queue()
    connection_event_queues.add(queue)

    async def stream():
        try:
            while True:
                event = await queue.get()
                yield f"data: {json.dumps(event)}\n\n"
        finally:
            connection_event_queues.discard(queue)

    return StreamingResponse(stream(), media_type="text/event-stream")


@app.post("/oauth/google/{connection}/start")
def start_google_connection(connection: GoogleConnection) -> dict[str, str]:
    try:
        return {"authorization_url": google_auth.begin(connection)}
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@app.get("/oauth/google/callback", response_class=HTMLResponse)
async def finish_google_connection(
    state: str,
    code: str | None = None,
    error: str | None = None,
) -> HTMLResponse:
    if error or not code:
        return HTMLResponse(
            "<h2>Sherpa was not connected.</h2><p>You can close this window.</p>",
            status_code=400,
        )
    try:
        connection = await google_auth.finish(state, code)
    except (ValueError, RuntimeError, httpx.HTTPError) as connection_error:
        return HTMLResponse(
            f"<h2>Sherpa was not connected.</h2><p>{html.escape(str(connection_error))}</p>",
            status_code=400,
        )
    await emit_connection_event({"type": "connection_changed", "connection": connection})
    return HTMLResponse(
        "<h2>Sherpa is connected.</h2><p>You can close this window.</p>"
        "<script>window.close()</script>"
    )


@app.delete("/oauth/google/{connection}")
async def disconnect_google(connection: GoogleConnection) -> dict[str, object]:
    google_auth.disconnect(connection)
    await emit_connection_event({"type": "connection_changed", "connection": connection})
    return {"connection": connection, "connected": False}


@app.get("/oauth/google/workspace/avatar")
async def google_workspace_avatar() -> Response:
    picture = google_auth.snapshot("workspace").get("picture")
    hostname = urlparse(picture).hostname if isinstance(picture, str) else None
    if not hostname or not hostname.endswith(".googleusercontent.com"):
        raise HTTPException(status_code=404, detail="Google profile photo is unavailable.")
    async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
        response = await client.get(picture)
        response.raise_for_status()
    content_type = response.headers.get("content-type", "")
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=502, detail="Google returned an invalid profile photo.")
    return Response(
        content=response.content,
        media_type=content_type,
        headers={"Cache-Control": "private, max-age=3600"},
    )


@app.get("/workspace/previews/{file_id}")
async def google_workspace_preview(file_id: str) -> Response:
    from backend.tools.google_tools.workspace import google_resource_id

    try:
        resource_id = google_resource_id(file_id)
    except RuntimeError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    token = await google_auth.access_token("workspace")
    if not token:
        raise HTTPException(status_code=401, detail="Google Workspace is not connected.")
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        metadata = await client.get(
            f"https://www.googleapis.com/drive/v3/files/{resource_id}",
            headers=headers,
            params={"fields": "thumbnailLink"},
        )
        if metadata.is_error:
            raise HTTPException(status_code=metadata.status_code, detail="Google Drive preview metadata is unavailable.")
        thumbnail_link = metadata.json().get("thumbnailLink")
        if not thumbnail_link:
            raise HTTPException(status_code=404, detail="This Drive file does not provide a rendered preview.")
        thumbnail = await client.get(thumbnail_link, headers=headers)
    content_type = thumbnail.headers.get("content-type", "")
    if thumbnail.is_error or not content_type.startswith("image/"):
        raise HTTPException(status_code=502, detail="Google Drive returned an invalid preview image.")
    return Response(
        content=thumbnail.content,
        media_type=content_type,
        headers={"Cache-Control": "private, no-store"},
    )


@app.put("/permissions/{permission_id:path}")
def update_permission(permission_id: str, body: PermissionRequest) -> dict[str, object]:
    permission_store.set(permission_id, body.enabled)
    return {"id": permission_id, "enabled": body.enabled}


@app.get("/memory")
def memory() -> dict[str, object]:
    return memory_store.snapshot()


@app.get("/skills")
def skills() -> dict[str, object]:
    return {"skills": [skill.snapshot() for skill in skill_store.all()]}


@app.patch("/skills/{skill_id}")
def update_skill(skill_id: str, body: SkillRequest) -> dict[str, object]:
    try:
        return skill_store.update(skill_id, body.instructions).snapshot()
    except KeyError as error:
        raise HTTPException(status_code=404, detail="Skill not found") from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


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


@app.post("/chat/title")
async def chat_title(body: ChatTitleRequest) -> dict[str, str]:
    if not permission_store.enabled("google.models"):
        raise HTTPException(status_code=403, detail="Gemini models are turned off in Sherpa Plugins.")
    prompt = (
        "Name this chat in no more than five words. Return only the title, "
        "without quotes or punctuation.\n\n"
        f"User: {body.user_message[:1600]}\n"
        f"Assistant: {body.assistant_message[:1600]}"
    )
    response = await genai.Client(
        vertexai=True,
        project=os.environ["GOOGLE_CLOUD_PROJECT"],
        location=os.environ["GOOGLE_CLOUD_LOCATION"],
    ).aio.models.generate_content(
        model="gemini-3.7-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            max_output_tokens=128,
            temperature=0.2,
            thinking_config=types.ThinkingConfig(thinking_level="low"),
        ),
    )
    words = re.findall(r"[\w’'-]+", (response.text or "").strip(), flags=re.UNICODE)[:5]
    if not words:
        raise HTTPException(status_code=502, detail="Gemini returned an empty chat title.")
    return {"title": " ".join(words)[:60]}


async def stream_chat(body: ChatRequest):
    started_at = time.perf_counter()
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
        tool_calls = 0
        token_usage = {"input": 0, "output": 0, "thinking": 0, "total": 0}
        async for event in run_with_google_tool_scope(
            runner,
            body.message,
            user_id="local-user",
            session_id=body.session_id,
            new_message=message,
            run_config=config,
        ):
            add_token_usage(token_usage, getattr(event, "usage_metadata", None))
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
                tool_calls += 1
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
        chat_logger.info(
            'turn channel=text session=%s duration_ms=%d tools=%d tokens_in=%d tokens_out=%d tokens_thinking=%d tokens_total=%d user="%s" assistant="%s"',
            body.session_id,
            round((time.perf_counter() - started_at) * 1000),
            tool_calls,
            token_usage["input"],
            token_usage["output"],
            token_usage["thinking"],
            token_usage["total"],
            log_text(body.message),
            log_text(assistant_text),
        )
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
                silence_duration_ms=1000,
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
        live_closed = asyncio.Event()
        model_idle = True
        playback_drained = True
        user_speaking = False
        notification_in_flight = False
        pending_notifications: list[dict] = []
        in_flight_notifications: list[dict] = []
        notification_lock = asyncio.Lock()
        voice_user_text: list[str] = []
        voice_assistant_text: list[str] = []
        turn_user_text: list[str] = []
        turn_assistant_text: list[str] = []
        transcript_sequence = 0
        input_transcript_id: str | None = None
        output_transcript_id: str | None = None
        input_transcript_sequence = 0
        output_transcript_sequence = 0
        input_transcript_text = ""
        output_transcript_text = ""

        await websocket.send_json({"type": "ready"})
        logger.info("session.ready session=%s model=%s tools=7", session_id, VOICE_MODEL)
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
                notification_in_flight = True
                model_idle = False
                await live.send_realtime_input(text=task_state_notification(
                    events,
                    [
                        sherpa_tasks.snapshot(task)
                        for task in sherpa_tasks.list_for_chat(session_id)
                    ],
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
            except Exception as error:
                if live_closed.is_set() or is_expected_live_close(error):
                    logger.info("session.input_closed session=%s", session_id)
                else:
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

        async def send_events() -> None:
            nonlocal model_idle, playback_drained, notification_in_flight
            nonlocal in_flight_notifications, transcript_sequence
            nonlocal input_transcript_id, output_transcript_id
            nonlocal input_transcript_sequence, output_transcript_sequence
            nonlocal input_transcript_text, output_transcript_text
            try:
                while True:
                    async for response in live.receive():
                        if response.tool_call:
                            for call in response.tool_call.function_calls or []:
                                await handle_voice_tool_call(
                                    call,
                                    session_id,
                                    send_function_response,
                                )
                        content = response.server_content
                        if not content:
                            continue
                        if content.interrupted:
                            if notification_in_flight:
                                pending_notifications[:0] = in_flight_notifications
                                in_flight_notifications = []
                                notification_in_flight = False
                            await websocket.send_json({"type": "interrupted"})
                        interim = content.interim_input_transcription
                        if interim and interim.text:
                            if input_transcript_id is None:
                                transcript_sequence += 1
                                input_transcript_sequence = transcript_sequence
                                input_transcript_id = f"voice-user-{transcript_sequence}"
                            input_transcript_text = interim.text
                            await websocket.send_json({
                                "type": "transcript_update",
                                "id": input_transcript_id,
                                "role": "user",
                                "sequence": input_transcript_sequence,
                                "text": interim.text,
                                "final": False,
                            })
                        transcription = content.input_transcription
                        if transcription and transcription.text:
                            if input_transcript_id is None:
                                transcript_sequence += 1
                                input_transcript_sequence = transcript_sequence
                                input_transcript_id = f"voice-user-{transcript_sequence}"
                            input_transcript_text = merge_transcript_text(
                                input_transcript_text,
                                transcription.text,
                            )
                            await websocket.send_json({
                                "type": "transcript_update",
                                "id": input_transcript_id,
                                "role": "user",
                                "sequence": input_transcript_sequence,
                                "text": input_transcript_text,
                                "final": bool(transcription.finished),
                            })
                            if transcription.finished:
                                voice_user_text.append(input_transcript_text)
                                turn_user_text.append(input_transcript_text)
                                input_transcript_id = None
                                input_transcript_text = ""
                        transcription = content.output_transcription
                        if transcription and transcription.text:
                            if output_transcript_id is None:
                                transcript_sequence += 1
                                output_transcript_sequence = transcript_sequence
                                output_transcript_id = f"voice-assistant-{transcript_sequence}"
                            output_transcript_text = merge_transcript_text(
                                output_transcript_text,
                                transcription.text,
                            )
                            await websocket.send_json({
                                "type": "transcript_update",
                                "id": output_transcript_id,
                                "role": "assistant",
                                "sequence": output_transcript_sequence,
                                "text": output_transcript_text,
                                "final": bool(transcription.finished),
                            })
                            if transcription.finished:
                                voice_assistant_text.append(output_transcript_text)
                                turn_assistant_text.append(output_transcript_text)
                                output_transcript_id = None
                                output_transcript_text = ""
                        if content.model_turn:
                            model_idle = False
                            for part in content.model_turn.parts or []:
                                if part.inline_data and part.inline_data.data:
                                    playback_drained = False
                                    await websocket.send_bytes(part.inline_data.data)
                        if content.turn_complete:
                            input_event = final_transcript_event(
                                input_transcript_id,
                                "user",
                                input_transcript_sequence,
                                input_transcript_text,
                            )
                            if input_event:
                                await websocket.send_json(input_event)
                                voice_user_text.append(input_transcript_text)
                                turn_user_text.append(input_transcript_text)
                            input_transcript_id = None
                            input_transcript_text = ""
                            output_event = final_transcript_event(
                                output_transcript_id,
                                "assistant",
                                output_transcript_sequence,
                                output_transcript_text,
                            )
                            if output_event:
                                await websocket.send_json(output_event)
                                voice_assistant_text.append(output_transcript_text)
                                turn_assistant_text.append(output_transcript_text)
                            output_transcript_id = None
                            output_transcript_text = ""
                            chat_logger.info(
                                'turn channel=voice session=%s user="%s" assistant="%s"',
                                session_id,
                                log_text(" ".join(turn_user_text)),
                                log_text(" ".join(turn_assistant_text)),
                            )
                            turn_user_text.clear()
                            turn_assistant_text.clear()
                            model_idle = True
                            notification_in_flight = False
                            in_flight_notifications = []
                            await websocket.send_json({"type": "turn_complete"})
                            await maybe_deliver_notification()
            except Exception as error:
                live_closed.set()
                if is_expected_live_close(error):
                    logger.info(
                        "session.ended session=%s reason=provider_duration_limit",
                        session_id,
                    )
                else:
                    logger.exception(
                        "model.live_failed session=%s type=%s error=%s",
                        session_id, type(error).__name__, error,
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
                        "task_started", "task_updated", "task_question",
                        "task_question_answered", "task_steering_queued",
                        "task_steering_applied",
                    }:
                        await websocket.send_json(event)
                    if event["type"] == "task_question":
                        question = event["question"]
                        pending_notifications.append({
                            **event,
                            "status": "needs_clarification",
                            "message": question["question"],
                        })
                        await maybe_deliver_notification()
                        continue
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


def is_expected_live_close(error: Exception) -> bool:
    message = str(error).lower()
    return "goaway" in message and "session durat" in message


def merge_transcript_text(current: str, incoming: str) -> str:
    if not current or incoming.startswith(current):
        return incoming
    if current == incoming or current.endswith(incoming):
        return current
    return f"{current.rstrip()} {incoming.lstrip()}"


def final_transcript_event(
    transcript_id: str | None,
    role: str,
    sequence: int,
    text: str,
) -> dict[str, object] | None:
    if not transcript_id or not text:
        return None
    return {
        "type": "transcript_update",
        "id": transcript_id,
        "role": role,
        "sequence": sequence,
        "text": text,
        "final": True,
    }


def public_tool_result(result: dict | None) -> dict[str, str]:
    if result and (
        result.get("isError")
        or result.get("error")
        or result.get("status") == "failed"
    ):
        return {"status": "failed"}
    return {"status": "done"}
