from typing import Literal

from pydantic import BaseModel, Field


ToolCapability = Literal[
    "computer",
    "browser",
    "workspace.drive",
    "workspace.docs",
    "workspace.sheets",
    "workspace.slides",
    "workspace.gmail",
    "workspace.calendar",
    "workspace.people",
    "cloud.resources",
    "cloud.cli",
]


class WorkerAssignment(BaseModel):
    key: str = Field(
        description="Short stable identifier used by dependent assignments",
        pattern=r"^[a-z][a-z0-9_]{0,31}$",
    )
    title: str = Field(description="Short task-board title")
    instruction: str = Field(description="Complete standalone worker instruction")
    tools: list[ToolCapability] = Field(
        description="Smallest tool capability set required by this assignment",
        min_length=1,
    )
    depends_on: list[str] = Field(
        default_factory=list,
        description="Assignment keys that must complete first",
        max_length=2,
    )


class AdmissionDecision(BaseModel):
    decision: Literal["accepted", "already_active", "needs_clarification"]
    message: str = Field(description="Short natural response for the voice agent")
    existing_task_id: str | None = None
    assignments: list[WorkerAssignment] = Field(default_factory=list, max_length=3)


def validate_assignment_graph(assignments: list[WorkerAssignment]) -> None:
    if not assignments:
        raise ValueError("An accepted request requires at least one assignment.")
    keys = [assignment.key for assignment in assignments]
    if len(keys) != len(set(keys)):
        raise ValueError("Assignment keys must be unique.")
    known = set(keys)
    for assignment in assignments:
        dependencies = set(assignment.depends_on)
        if assignment.key in dependencies:
            raise ValueError(f"Assignment {assignment.key} cannot depend on itself.")
        unknown = dependencies - known
        if unknown:
            raise ValueError(
                f"Assignment {assignment.key} has unknown dependencies: "
                f"{', '.join(sorted(unknown))}."
            )

    visited: set[str] = set()
    visiting: set[str] = set()
    graph = {assignment.key: assignment.depends_on for assignment in assignments}

    def visit(key: str) -> None:
        if key in visited:
            return
        if key in visiting:
            raise ValueError("Assignment dependencies must not contain a cycle.")
        visiting.add(key)
        for dependency in graph[key]:
            visit(dependency)
        visiting.remove(key)
        visited.add(key)

    for key in keys:
        visit(key)


def validate_admission_decision(admission: AdmissionDecision) -> None:
    if admission.decision == "accepted":
        if admission.existing_task_id is not None:
            raise ValueError("An accepted request cannot reference an existing task.")
        validate_assignment_graph(admission.assignments)
        return
    if admission.assignments:
        raise ValueError(f"{admission.decision} cannot include assignments.")
    if admission.decision == "already_active" and not admission.existing_task_id:
        raise ValueError("already_active requires an existing task ID.")


def dependency_context(
    assignment: WorkerAssignment,
    completed: dict[str, tuple[str, str, str]],
) -> str:
    if not assignment.depends_on:
        return assignment.instruction
    results = "\n".join(
        f"- {completed[key][0]}: {completed[key][1]}\n"
        f"  Evidence: {completed[key][2]}"
        for key in assignment.depends_on
    )
    return (
        f"Results from prerequisite assignments:\n{results}\n\n"
        f"Your assigned work:\n{assignment.instruction}\n\n"
        "Use the prerequisite results as verified context. Do not repeat their work."
    )
