from pathlib import Path
from typing import Literal

from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.genai import types
from pydantic import BaseModel, Field


class TaskOperation(BaseModel):
    action: Literal["create", "reuse", "steer", "cancel"]
    task_id: str = Field(
        description="Existing task ID for reuse, steer, or cancel; empty for create."
    )
    title: str = Field(
        description="Required concise task-board title for create; empty otherwise."
    )
    instruction: str = Field(
        description=(
            "Required detailed operational instruction for create or steer; "
            "empty otherwise."
        )
    )
    skill_ids: list[str] = Field(default_factory=list, max_length=4)
    key: str = Field(
        description="Required unique dependency key for create; empty otherwise."
    )
    depends_on: list[str] = Field(default_factory=list, max_length=3)
    required_inputs: list[str] = Field(default_factory=list, max_length=8)
    expected_outputs: list[str] = Field(default_factory=list, max_length=8)


class TaskPlan(BaseModel):
    message: str = Field(description="Short natural status for the voice agent")
    operations: list[TaskOperation] = Field(min_length=1, max_length=6)


PLANNING_SKILL = Path(__file__).resolve().parents[1].joinpath(
    "task_planning_skill.md"
).read_text()


task_planner = Agent(
    name="task_planner",
    description="Maintains Sherpa's ordered task queue without running work itself.",
    model=Gemini(
        model="gemini-3.7-flash",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    mode="chat",
    output_schema=TaskPlan,
    generate_content_config=types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(thinking_level="low"),
    ),
    instruction=f"""
    Follow this planner-only task skill exactly:

    {PLANNING_SKILL}

    You maintain an ordered, strictly sequential task queue. Read the user's new
    request together with every running or queued task before making changes.

    Create one task by default. Create two or three only under the skill's split
    rules. Each create needs a short unique key. Dependencies reference earlier
    create keys, never generated task IDs. Never create child agents or parallel
    work; the runtime executes created tasks one at a time.

    Reuse an existing task when it already covers the requested outcome. Steer a
    task when the user is refining that same task. Cancel only when the user's
    wording clearly stops or replaces existing work. Do not cancel merely to
    prioritize new work. Do not duplicate overlapping outcomes.

    A create operation needs a short task-list title and a detailed operational
    instruction containing the exact app or service, target object, actions,
    constraints, completion evidence, required inputs, and expected outputs.
    Select zero or more skill IDs from the supplied skill catalog for each
    create operation.
    Skills contain execution procedures, not separate jobs: attach every skill
    needed for a cross-tool outcome to that one task. Never invent a skill ID.
    Do not select a skill for a simple task that does not benefit from one.

    A steer operation needs the target task ID and the changed instruction. It
    may also replace that task's skill IDs when the refinement changes the tools
    or workflow it needs. Reuse and cancel need a valid task ID from the supplied
    ledger. Keep operations in the exact order they should be applied and keep
    the message under twenty words.
    """,
)

task_planner_app = App(name="task_planner", root_agent=task_planner)
