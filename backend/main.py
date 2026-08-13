import json
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from google.adk.agents import RunConfig
from google.adk.agents.run_config import StreamingMode
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from pydantic import BaseModel, Field

os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "true")
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "sherpa-20260813")
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "global")

from backend.agents.sherpa_agent import sherpa_app

sessions = InMemorySessionService()
runner = Runner(app=sherpa_app, session_service=sessions)

app = FastAPI(title="Sherpa API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


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


def sse(event: dict[str, object]) -> str:
    return f"data: {json.dumps(event, default=str)}\n\n"
