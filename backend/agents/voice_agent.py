import os

from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.genai import types

VOICE_MODEL = "gemini-3.1-flash-live-preview"

voice_agent = Agent(
    name="voice_agent",
    description="Owns Sherpa's realtime voice conversation.",
    model=Gemini(
        model=VOICE_MODEL,
        client_kwargs={
            "api_key": os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"),
            "vertexai": False,
        },
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    generate_content_config=types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(thinking_level="minimal"),
    ),
    instruction="Speak naturally and concisely with the user.",
    tools=[],
)

voice_app = App(name="sherpa_voice", root_agent=voice_agent)
