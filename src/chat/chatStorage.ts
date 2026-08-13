import type { SherpaChat } from "./chatTypes";

const storageKey = "sherpa-chats";

export function createSherpaChat(): SherpaChat {
  const now = Date.now();
  return {
    id: crypto.randomUUID(),
    title: "New chat",
    messages: [],
    transcript: [],
    createdAt: now,
    updatedAt: now,
  };
}

export function loadSherpaChats(): SherpaChat[] {
  const stored = window.localStorage.getItem(storageKey);
  if (!stored) return [];
  const parsed = JSON.parse(stored) as unknown;
  if (!Array.isArray(parsed)) throw new Error("The saved Sherpa chats are invalid.");
  return (parsed as SherpaChat[])
    .map((chat) => ({ ...chat, transcript: Array.isArray(chat.transcript) ? chat.transcript : [] }))
    .sort((left, right) => right.updatedAt - left.updatedAt);
}

export function saveSherpaChats(chats: SherpaChat[]) {
  window.localStorage.setItem(storageKey, JSON.stringify(chats));
}
