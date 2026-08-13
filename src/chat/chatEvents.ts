import type { ChatBlock, ChatMessage, ChatStreamEvent, ToolCall } from "./chatTypes";

export function applyChatEvent(messages: ChatMessage[], event: ChatStreamEvent) {
  if (event.type === "done") return finishReasoning(messages);
  const current = ensureAssistant(messages);
  if (event.type === "content" || event.type === "reasoning") {
    return updateLast(current, (blocks) =>
      appendText(blocks, event.type === "content" ? "text" : "reasoning", event.content),
    );
  }
  if (event.type === "tool_call") {
    return updateLast(current, (blocks) =>
      upsertTool(blocks, { id: event.id, name: event.name, status: "running" }),
    );
  }
  if (event.type === "tool_response") {
    return updateLast(current, (blocks) =>
      upsertTool(blocks, {
        id: event.id,
        name: event.name,
        status: event.result.status === "failed" ? "error" : "done",
      }),
    );
  }
  return updateLast(current, (blocks) => [
    ...finishBlocks(blocks),
    { id: crypto.randomUUID(), kind: "text", content: `Error: ${event.error}` },
  ]);
}

export function finishReasoning(messages: ChatMessage[]) {
  return messages.map((message) =>
    message.role === "assistant" ? { ...message, blocks: finishBlocks(message.blocks) } : message,
  );
}

function ensureAssistant(messages: ChatMessage[]) {
  if (messages.at(-1)?.role === "assistant") return messages;
  return [...messages, { id: crypto.randomUUID(), role: "assistant" as const, blocks: [] }];
}

function updateLast(messages: ChatMessage[], update: (blocks: ChatBlock[]) => ChatBlock[]) {
  return messages.map((message, index) =>
    index === messages.length - 1 ? { ...message, blocks: update(message.blocks) } : message,
  );
}

function appendText(blocks: ChatBlock[], kind: "text" | "reasoning", content: string) {
  const current = kind === "text" ? finishBlocks(blocks) : blocks;
  const last = current.at(-1);
  if (last?.kind === kind) {
    return current.map((block, index) =>
      index === current.length - 1 ? { ...last, content: last.content + content } : block,
    );
  }
  return [
    ...current,
    {
      id: crypto.randomUUID(),
      kind,
      content,
      ...(kind === "reasoning" ? { startedAt: Date.now() } : {}),
    } as ChatBlock,
  ];
}

function upsertTool(blocks: ChatBlock[], tool: ToolCall) {
  const current = finishBlocks(blocks);
  const blockId = `tool-${tool.id}`;
  if (current.some((block) => block.id === blockId)) {
    return current.map((block): ChatBlock =>
      block.id === blockId ? { id: blockId, kind: "tool", tool } : block,
    );
  }
  return [...current, { id: blockId, kind: "tool" as const, tool }];
}

function finishBlocks(blocks: ChatBlock[]) {
  const now = Date.now();
  return blocks.map((block) =>
    block.kind === "reasoning" && !block.finishedAt ? { ...block, finishedAt: now } : block,
  );
}
