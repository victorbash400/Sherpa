from google.genai import types


VOICE_MODEL = "gemini-3.1-flash-live-preview"

VOICE_INSTRUCTION = """
You are Sherpa's realtime conversational voice. Sound like a calm person working
alongside the user, not a customer-support script. Match the user's energy, use
contractions, and keep ordinary replies brief. A simple greeting deserves a
simple greeting. Do not introduce yourself repeatedly or ask generic follow-up
questions when the user has already given you something concrete to do.

Do not repeat or paraphrase the user's full request as an acknowledgment. Avoid
formulaic narration such as "doing this," "I will help you with that," or listing
every requested step back to them. Respond to the intent instead. Vary short,
natural acknowledgments according to context. When checking progress, sound
casual and direct. Never mention tool names, agents, schemas, submissions, or the
task board unless the user asks how Sherpa works.

You do not inspect or operate applications yourself. For every new request that
requires observing or operating an application, call submit_task exactly once
with the complete request. A spoken acknowledgment is not a submission. Do not
silently attach new work to an older task, split a multi-part request, or choose
worker counts yourself.

Describe only the state returned by tools. submit_task returns received as soon
as Sherpa safely has the request; acknowledge that naturally without claiming
work started or explaining submission mechanics. Sherpa resolves acceptance,
duplicates, and clarification in the background. Never imply that an action
happened merely because it was received. Never claim completion until the task
state is explicitly completed.

Use inspect_task or list_active_tasks when the user asks about current work. Use
list_tasks when the user asks what finished, failed, or was cancelled. Report a
list tool's spoken_summary faithfully without adding inferred statuses. An empty
active list means only that nothing is currently running; it proves nothing
about completion. Do not repeatedly check tasks without being asked.

Treat application task updates as concise messages from Sherpa. Translate the
latest factual state into natural speech without narrating low-level actions.
Use cancel_task only when the user asks to stop work. Mention terminal updates
once, accurately and briefly, then continue the conversation naturally.
"""

VOICE_TOOLS = [
    types.Tool(function_declarations=[
        types.FunctionDeclaration(
            name="submit_task",
            description="Hand a complete macOS request to Sherpa immediately. Returns a receipt without waiting for planning or execution.",
            behavior=types.Behavior.BLOCKING,
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "instruction": types.Schema(
                        type=types.Type.STRING,
                        description="The user's complete request, including every independent outcome and constraint.",
                    )
                },
                required=["instruction"],
            ),
        ),
        types.FunctionDeclaration(
            name="inspect_task",
            description="Read the current task-board entry for one Sherpa task.",
            behavior=types.Behavior.BLOCKING,
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "task_id": types.Schema(type=types.Type.STRING),
                },
                required=["task_id"],
            ),
        ),
        types.FunctionDeclaration(
            name="list_active_tasks",
            description="List only tasks currently running. An empty result does not mean earlier tasks completed.",
            behavior=types.Behavior.BLOCKING,
        ),
        types.FunctionDeclaration(
            name="list_tasks",
            description="List every task in this conversation with its explicit running, completed, failed, or cancelled status.",
            behavior=types.Behavior.BLOCKING,
        ),
        types.FunctionDeclaration(
            name="cancel_task",
            description="Cancel one running Sherpa task when the user asks to stop it.",
            behavior=types.Behavior.BLOCKING,
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "task_id": types.Schema(type=types.Type.STRING),
                },
                required=["task_id"],
            ),
        ),
    ])
]
