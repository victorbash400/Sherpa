from typing import Literal

from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.genai import types
from pydantic import BaseModel, Field


class TaskOperation(BaseModel):
    action: Literal["create", "reuse", "steer", "cancel"]
    task_id: str | None = None
    title: str | None = None
    instruction: str | None = None


class TaskPlan(BaseModel):
    message: str = Field(description="Short natural status for the voice agent")
    operations: list[TaskOperation] = Field(min_length=1, max_length=6)


task_planner = Agent(
    name="task_planner",
    description="Maintains Sherpa's ordered task queue without running work itself.",
    model=Gemini(
        model="gemini-3.7-flash",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    mode="chat",
    output_schema=TaskPlan,
    instruction="""
    You maintain an ordered, strictly sequential task queue. Read the user's new
    request together with every running or queued task before making changes.

    Create one task for a simple outcome. Create two or three tasks only when the
    request contains distinct outcomes that deserve separate task-board entries.
    Put dependent tasks in the order they must run. Never create child agents or
    parallel work; the runtime executes created tasks one at a time.

    Reuse an existing task when it already covers the requested outcome. Steer a
    task when the user is refining that same task. Cancel only when the user's
    wording clearly stops or replaces existing work. Do not cancel merely to
    prioritize new work. Do not duplicate overlapping outcomes.

    A create operation needs a short task-list title and a complete standalone
    instruction containing its constraints and completion criteria. A steer
    operation needs the target task ID and the changed instruction. Reuse and
    cancel need a valid task ID from the supplied ledger. Keep operations in the
    exact order they should be applied and keep the message under twenty words.
    """,
)

task_planner_app = App(name="task_planner", root_agent=task_planner)
