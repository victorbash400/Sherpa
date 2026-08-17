from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from google.adk.apps.llm_event_summarizer import LlmEventSummarizer
from google.adk.events import Event
from google.adk.models import Gemini
from google.adk.sessions import InMemorySessionService
from google.adk.sessions import Session


COMPACTION_TOKEN_LIMIT = 300_000
COMPACTION_EVENT_RETENTION_SIZE = 20

CompactionListener = Callable[[str, int], Awaitable[None]]


@dataclass
class CompactionRegistration:
    task_id: str
    listener: CompactionListener


class CompactionEvents:
    def __init__(self) -> None:
        self._invocations: dict[str, CompactionRegistration] = {}
        self._sessions: dict[str, CompactionRegistration] = {}

    def register_session(
        self,
        session_id: str,
        task_id: str,
        listener: CompactionListener,
    ) -> None:
        self._sessions[session_id] = CompactionRegistration(
            task_id=task_id,
            listener=listener,
        )

    def register(
        self,
        invocation_id: str | None,
        task_id: str,
        listener: CompactionListener,
    ) -> None:
        if invocation_id:
            self._invocations[invocation_id] = CompactionRegistration(
                task_id=task_id,
                listener=listener,
            )

    def unregister_task(self, task_id: str) -> None:
        self._invocations = {
            invocation_id: registration
            for invocation_id, registration in self._invocations.items()
            if registration.task_id != task_id
        }
        self._sessions = {
            session_id: registration
            for session_id, registration in self._sessions.items()
            if registration.task_id != task_id
        }

    async def notify(self, events: list[Event], phase: str, tokens: int) -> None:
        registration = next((
            self._invocations[event.invocation_id]
            for event in reversed(events)
            if event.invocation_id in self._invocations
        ), None)
        if registration:
            await registration.listener(phase, tokens)

    async def completed(self, session_id: str, tokens: int) -> None:
        registration = self._sessions.get(session_id)
        if registration:
            await registration.listener("completed", tokens)


compaction_events = CompactionEvents()


class SherpaSessionService(InMemorySessionService):
    async def append_event(self, session: Session, event: Event) -> Event:
        appended = await super().append_event(session=session, event=event)
        if event.actions and event.actions.compaction:
            from google.adk.apps.compaction import _estimate_prompt_token_count

            tokens = _estimate_prompt_token_count(
                events=session.events,
                current_branch=None,
                agent_name="",
            ) or 0
            await compaction_events.completed(session.id, tokens)
        return appended


class SherpaEventSummarizer(LlmEventSummarizer):
    async def maybe_summarize_events(self, *, events: list[Event]) -> Event | None:
        await compaction_events.notify(events, "started", -1)
        try:
            compacted = await super().maybe_summarize_events(events=events)
        except Exception:
            await compaction_events.notify(events, "failed", -1)
            raise
        if compacted is None:
            await compaction_events.notify(events, "failed", -1)
        return compacted


def create_compaction_summarizer(model: Gemini) -> SherpaEventSummarizer:
    return SherpaEventSummarizer(llm=model)
