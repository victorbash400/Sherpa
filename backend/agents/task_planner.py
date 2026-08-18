from pathlib import Path
from typing import Literal

from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.genai import types
from pydantic import BaseModel, Field


class TaskOperation(BaseModel):
    action: Literal["create", "reuse", "update", "steer", "cancel"]
    task_id: str = Field(
        description="Existing task ID for reuse, update, steer, or cancel; empty for create."
    )
    title: str = Field(
        description="Required concise task-board title for create; empty otherwise."
    )
    instruction: str = Field(
        description=(
            "Required detailed operational instruction for create, update, or steer; "
            "empty otherwise."
        )
    )
    skill_ids: list[str] = Field(default_factory=list)
    key: str = Field(
        description="Required unique dependency key for create; empty otherwise."
    )
    depends_on: list[str] = Field(default_factory=list)
    required_inputs: list[str] = Field(default_factory=list)
    expected_outputs: list[str] = Field(default_factory=list)


class TaskPlan(BaseModel):
    message: str = Field(description="Short natural status for the voice agent")
    operations: list[TaskOperation] = Field(min_length=1)


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

    Create one task by default and split only under the skill's rules. Each
    create needs a short unique key. Dependencies reference earlier
    create keys, never generated task IDs. Never create child agents or parallel
    work; the runtime executes created tasks one at a time.

    Reuse a task that already covers the outcome. Update a queued task's stored
    plan. Steer a running or blocked task at its next tool boundary. Cancel only
    when the user clearly stops or replaces work. Never duplicate outcomes.

    A create operation needs a short task-list title and a detailed operational
    instruction containing the exact app or service, target object, actions,
    constraints, completion evidence, required inputs, and expected outputs.
    Select zero or more skill IDs from the supplied skill catalog for each
    create operation. Skills provide execution procedures but never restrict
    tool access; workers discover tools from the registry while they work.
    Skills are not separate jobs: attach every useful procedural skill for a
    cross-tool outcome to that one task. Never invent a skill ID or select an
    unrelated one.

    Update and steer need the task ID and complete revised instruction. Include
    every skill the revised task needs. Reuse and cancel need a valid task ID.
    Keep operations in application order and the message brief.
    """,
)

task_planner_app = App(name="task_planner", root_agent=task_planner)
