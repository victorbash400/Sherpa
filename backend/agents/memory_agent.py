from typing import Literal

from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from pydantic import BaseModel, Field


class MemoryCandidate(BaseModel):
    category: Literal["identity", "preference", "project", "workflow"]
    content: str = Field(max_length=320)


class MemoryCandidates(BaseModel):
    memories: list[MemoryCandidate] = Field(default_factory=list, max_length=5)


memory_agent = Agent(
    name="memory_agent",
    description="Extracts durable, user-relevant memory candidates.",
    model=Gemini(model="gemini-3.7-flash"),
    mode="chat",
    output_schema=MemoryCandidates,
    instruction="""
    Extract only facts that will remain useful in a future Sherpa conversation:
    explicit identity facts, durable preferences, ongoing projects, or recurring
    workflow choices. Do not store one-off requests, greetings, transient app
    state, task progress, secrets, credentials, inferred traits, or anything said
    only by the assistant. Prefer no memory over an uncertain memory. Write each
    candidate as a short standalone statement without commentary.
    """,
)

memory_agent_app = App(name="memory_agent", root_agent=memory_agent)
