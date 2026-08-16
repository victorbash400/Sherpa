const backendUrl = "http://127.0.0.1:8000";

export async function generateChatTitle(userMessage: string, assistantMessage: string) {
  const response = await fetch(`${backendUrl}/chat/title`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_message: userMessage, assistant_message: assistantMessage }),
  });
  const body = await response.json() as { detail?: string; title?: string };
  if (!response.ok || !body.title) throw new Error(body.detail || "Could not name this chat.");
  return body.title;
}
