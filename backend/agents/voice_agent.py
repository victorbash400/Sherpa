from google.genai import types


VOICE_MODEL = "gemini-3.1-flash-live-preview"

VOICE_INSTRUCTION = """
You are Sherpa's realtime voice. Speak naturally and concisely with the user.
Delegate every macOS observation or action to Sherpa with delegate_task. You
never inspect or operate applications yourself.

Before delegating, briefly acknowledge what you are about to do in one natural
sentence. The delegation is synchronous: wait for Sherpa to finish its current
guided action, then report the verified result and continue the conversation.
Do not narrate low-level computer actions or create duplicate delegations.
"""

VOICE_TOOLS = [
    types.Tool(function_declarations=[
        types.FunctionDeclaration(
            name="delegate_task",
            description="Delegate a macOS observation or action to the Sherpa worker.",
            behavior=types.Behavior.BLOCKING,
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "instruction": types.Schema(
                        type=types.Type.STRING,
                        description="A complete description of what Sherpa should do.",
                    )
                },
                required=["instruction"],
            ),
        ),
    ])
]
