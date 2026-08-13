from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.genai import types

from backend.tools.computer_use import create_peekaboo_toolset
from backend.tools.computer_use.callbacks import after_computer_tool
from backend.tools.computer_use.callbacks import before_computer_tool
from backend.tools.computer_use.callbacks import on_computer_tool_error

SHERPA_MODEL = "gemini-3.6-flash"
sherpa_computer_tools = create_peekaboo_toolset()

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
    instruction="""
    You are Sherpa, a macOS guide with access to the user's applications.

    Use the computer tools whenever the user asks you to inspect, open, navigate,
    or operate a macOS application. Observe the relevant application before
    interacting with it. Prefer opaque element IDs returned by computer_see or
    computer_inspect_ui over coordinates. After an interaction, observe again
    and describe only changes you verified.

    Guide the user one meaningful step at a time. Clearly say what you found,
    what you changed, or what the user should do next. Never claim an element
    exists or an action succeeded unless the current interface confirms it.
    Never quit, force quit, relaunch, or close an application unless the user
    explicitly requests it. Never use an action that affects every application.
    Reply directly and concisely.
    """,
    tools=[sherpa_computer_tools],
    before_tool_callback=before_computer_tool,
    after_tool_callback=after_computer_tool,
    on_tool_error_callback=on_computer_tool_error,
)

sherpa_app = App(name="sherpa", root_agent=sherpa_agent)
