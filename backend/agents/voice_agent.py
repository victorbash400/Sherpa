from google.genai import types


VOICE_MODEL = "gemini-2.5-flash-native-audio-preview-12-2025"

VOICE_INSTRUCTION = """
You are Sherpa's realtime voice. Speak naturally and concisely with the user.
Delegate every macOS observation or action to Sherpa with delegate_task. You
never inspect or operate applications yourself.

Before delegating, briefly acknowledge what you are about to do in one natural
sentence. The delegation runs independently, so continue listening and talking
while Sherpa works. When its result arrives, report it once in a short natural
sentence. Do not narrate low-level computer actions and do not repeat or recreate
a delegation that is already running.
"""

VOICE_TOOLS = [
    types.Tool(function_declarations=[
        types.FunctionDeclaration(
            name="delegate_task",
            description="Delegate a macOS observation or action to the Sherpa worker.",
            behavior=types.Behavior.NON_BLOCKING,
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
        types.FunctionDeclaration(
            name="get_task_status",
            description="Get the current status of a delegated Sherpa task.",
            behavior=types.Behavior.BLOCKING,
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={"task_id": types.Schema(type=types.Type.STRING)},
                required=["task_id"],
            ),
        ),
        types.FunctionDeclaration(
            name="cancel_task",
            description="Cancel a running Sherpa task.",
            behavior=types.Behavior.BLOCKING,
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={"task_id": types.Schema(type=types.Type.STRING)},
                required=["task_id"],
            ),
        ),
    ])
]
