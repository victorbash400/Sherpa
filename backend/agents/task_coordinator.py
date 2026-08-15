from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.genai import types
from typing import Literal

from pydantic import BaseModel, Field


COORDINATOR_MODEL = "gemini-3.7-flash"


class WorkerAssignment(BaseModel):
    title: str = Field(description="Short task-board title")
    instruction: str = Field(description="Complete standalone worker instruction")


class AdmissionDecision(BaseModel):
    decision: Literal["accepted", "already_active", "needs_clarification"]
    message: str = Field(description="Short natural response for the voice agent")
    existing_task_id: str | None = None
    assignments: list[WorkerAssignment] = Field(default_factory=list, max_length=3)


task_coordinator = Agent(
    name="task_coordinator",
    description="Admits requests and decomposes accepted work into independent assignments.",
    model=Gemini(
        model=COORDINATOR_MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    mode="chat",
    output_schema=AdmissionDecision,
    instruction="""
    You are Sherpa's task coordinator and admission gate. You receive the user's
    requested work plus the authoritative list of tasks currently running in
    this chat.

    Return already_active with the matching existing_task_id when the requested
    outcome is already covered by a running task. Compare intended outcomes,
    targets, and constraints rather than exact wording. Do not create duplicate
    work. Return needs_clarification only when a missing detail makes safe
    execution impossible. Otherwise return accepted and create one to three
    independent worker assignments.

    Use multiple assignments only when the user requested genuinely separate
    outcomes that can be completed independently.
    Keep dependent steps together in one assignment. Never split a single atomic
    action merely to create more workers. Each instruction must stand alone and
    contain all relevant targets, constraints, and completion criteria from the
    request. Titles must be short, specific, and written for a task list.

    Sherpa currently has one shared macOS computer-control surface. Workers may
    be dispatched together, but computer interactions will be serialized by the
    runtime so they cannot fight over the cursor or foreground application.

    For accepted, assignments must contain at least one item and
    existing_task_id must be null. For already_active, assignments must be empty
    and existing_task_id must identify the matching active task. For
    needs_clarification, assignments must be empty. Keep message under twenty
    words and make it suitable for the voice agent to say naturally.
    """,
)

task_coordinator_app = App(name="task_coordinator", root_agent=task_coordinator)
