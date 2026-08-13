export type ToolCall = {
  id: string;
  name: string;
  status: "running" | "done" | "error";
};

export type ChatBlock =
  | { id: string; kind: "text"; content: string }
  | { id: string; kind: "reasoning"; content: string; startedAt: number; finishedAt?: number }
  | { id: string; kind: "tool"; tool: ToolCall };

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  blocks: ChatBlock[];
};

export type VoiceTranscriptEntry = {
  id: string;
  role: "user" | "assistant";
  text: string;
};

export type SherpaChat = {
  id: string;
  title: string;
  messages: ChatMessage[];
  transcript: VoiceTranscriptEntry[];
  createdAt: number;
  updatedAt: number;
};

export type ChatStreamEvent =
  | { type: "content"; content: string }
  | { type: "reasoning"; content: string }
  | { type: "tool_call"; id: string; name: string; args: Record<string, unknown> }
  | { type: "tool_response"; id: string; name: string; result: Record<string, unknown> }
  | { type: "error"; error: string }
  | { type: "done" };
