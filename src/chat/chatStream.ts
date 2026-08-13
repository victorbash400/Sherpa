import type { ChatStreamEvent } from "./chatTypes";

const backendUrl = "http://127.0.0.1:8000";

export async function streamChat({
  message,
  sessionId,
  signal,
  onEvent,
}: {
  message: string;
  sessionId: string;
  signal: AbortSignal;
  onEvent: (event: ChatStreamEvent) => void;
}) {
  const response = await fetch(`${backendUrl}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
    body: JSON.stringify({ message, session_id: sessionId }),
    signal,
  });
  if (!response.ok || !response.body) {
    const body = (await response.json().catch(() => ({ detail: "Sherpa chat failed" }))) as {
      detail?: string;
    };
    throw new Error(body.detail || "Sherpa chat failed");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    buffer += decoder.decode(value, { stream: !done });
    const events = buffer.split("\n\n");
    buffer = events.pop() || "";
    for (const event of events) {
      const data = event
        .split("\n")
        .filter((line) => line.startsWith("data:"))
        .map((line) => line.slice(5).trim())
        .join("");
      if (data) onEvent(JSON.parse(data) as ChatStreamEvent);
    }
    if (done) break;
  }
}
