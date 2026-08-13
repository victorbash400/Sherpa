from google.adk.agents import Agent
from google.adk.models import Gemini
from google.genai import types

VOICE_MODEL = "gemini-3.1-flash-live-preview"

voice_agent = Agent(
    name="voice_agent",
    description="Owns Sherpa's realtime voice conversation.",
    model=Gemini(
        model=VOICE_MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    generate_content_config=types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(thinking_level="minimal"),
    ),
    instruction="Speak naturally and concisely with the user.",
    tools=[],
)
