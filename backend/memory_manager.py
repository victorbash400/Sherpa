import asyncio
import json
import logging

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from backend.agents.memory_agent import MemoryCandidates, memory_agent_app
from backend.memory_store import memory_store


logger = logging.getLogger("sherpa.memory")


class MemoryManager:
    def __init__(self) -> None:
        self._sessions = InMemorySessionService()
        self._runner = Runner(app=memory_agent_app, session_service=self._sessions)
        self._jobs: set[asyncio.Task[None]] = set()

    def schedule(
        self,
        *,
        source_type: str,
        source_id: str,
        user_text: str,
        assistant_text: str,
        tool_assisted: bool,
    ) -> None:
        if not user_text.strip() or not memory_store.learning_enabled(tool_assisted):
            return
        job = asyncio.create_task(
            self._extract(source_type, source_id, user_text, assistant_text),
            name=f"memory:{source_type}:{source_id}",
        )
        self._jobs.add(job)
        job.add_done_callback(self._jobs.discard)

    async def _extract(
        self,
        source_type: str,
        source_id: str,
        user_text: str,
        assistant_text: str,
    ) -> None:
        session_id = f"memory:{source_type}:{source_id}:{id(asyncio.current_task())}"
        try:
            await self._sessions.create_session(
                app_name="memory_agent", user_id="local-user", session_id=session_id
            )
            response = ""
            prompt = json.dumps({
                "user_said": user_text[-6000:],
                "assistant_replied": assistant_text[-3000:],
            })
            async for event in self._runner.run_async(
                user_id="local-user",
                session_id=session_id,
                new_message=types.Content(
                    role="user", parts=[types.Part.from_text(text=prompt)]
                ),
            ):
                if event.error_message:
                    raise RuntimeError(event.error_message)
                if event.content:
                    response += "".join(
                        part.text or "" for part in event.content.parts or []
                        if not part.thought
                    )
            candidates = MemoryCandidates.model_validate_json(response)
            for candidate in candidates.memories:
                memory_store.remember(
                    category=candidate.category,
                    content=candidate.content,
                    source_type=source_type,
                    source_id=source_id,
                    editable=source_type != "task",
                )
        except Exception:
            logger.exception("memory.extraction_failed source=%s id=%s", source_type, source_id)

    async def close(self) -> None:
        jobs = tuple(self._jobs)
        if jobs:
            await asyncio.gather(*jobs, return_exceptions=True)


memory_manager = MemoryManager()
