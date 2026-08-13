from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.genai import types

SHERPA_MODEL = "gemini-3.6-flash"

sherpa_agent = Agent(
    name="sherpa_agent",
    description="Chats with the user and helps them use unfamiliar software.",
    model=Gemini(
        model=SHERPA_MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    generate_content_config=types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(
            include_thoughts=True,
            thinking_level="medium",
        ),
    ),
    instruction="Reply directly and helpfully to the user.",
    tools=[],
)

sherpa_app = App(name="sherpa", root_agent=sherpa_agent)
