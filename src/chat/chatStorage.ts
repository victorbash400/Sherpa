import type { SherpaChat } from "./chatTypes";

function storageKey(accountId: string) {
  return `sherpa-chats:${accountId}`;
}

export function createSherpaChat(): SherpaChat {
  const now = Date.now();
  return {
    id: crypto.randomUUID(),
    title: "New chat",
    titleStatus: "pending",
    messages: [],
    transcript: [],
    createdAt: now,
    updatedAt: now,
  };
}

export function loadSherpaChats(accountId: string): SherpaChat[] {
  const stored = window.localStorage.getItem(storageKey(accountId));
  if (!stored) return [];
  const parsed = JSON.parse(stored) as unknown;
  if (!Array.isArray(parsed)) throw new Error("The saved Sherpa chats are invalid.");
  return (parsed as SherpaChat[])
    .map((chat) => ({
      ...chat,
      titleStatus: chat.titleStatus
        ? chat.titleStatus === "naming" ? "failed" : chat.titleStatus
        : chat.messages.length || chat.transcript?.length ? "complete" : "pending",
      transcript: Array.isArray(chat.transcript)
        ? chat.transcript.map((entry, index) => ({
          ...entry,
          sequence: typeof entry.sequence === "number" ? entry.sequence : index,
          final: typeof entry.final === "boolean" ? entry.final : true,
        }))
        : [],
    }))
    .sort((left, right) => right.updatedAt - left.updatedAt);
}

export function saveSherpaChats(accountId: string, chats: SherpaChat[]) {
  window.localStorage.setItem(storageKey(accountId), JSON.stringify(chats));
}
