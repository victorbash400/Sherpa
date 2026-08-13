import { useCallback, useEffect, useRef, useState } from "react";
import { applyChatEvent, finishReasoning } from "../chat/chatEvents";
import { createSherpaChat, loadSherpaChats, saveSherpaChats } from "../chat/chatStorage";
import { streamChat } from "../chat/chatStream";
import type { ChatMessage, SherpaChat } from "../chat/chatTypes";

export function useSherpaChat() {
  const [chats, setChats] = useState<SherpaChat[]>(() => {
    const stored = loadSherpaChats();
    return stored.length ? stored : [createSherpaChat()];
  });
  const [activeChatId, setActiveChatId] = useState(() => chats[0].id);
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState<string>();
  const controllerRef = useRef<AbortController | undefined>(undefined);
  const activeChat = chats.find((chat) => chat.id === activeChatId) ?? chats[0];

  useEffect(() => saveSherpaChats(chats), [chats]);
  useEffect(() => () => controllerRef.current?.abort(), []);

  const updateMessages = useCallback((chatId: string, update: (messages: ChatMessage[]) => ChatMessage[]) => {
    setChats((current) => current.map((chat) => chat.id === chatId ? {
      ...chat,
      messages: update(chat.messages),
      updatedAt: Date.now(),
    } : chat));
  }, []);

  const newChat = useCallback(() => {
    controllerRef.current?.abort();
    const chat = createSherpaChat();
    setChats((current) => [chat, ...current]);
    setActiveChatId(chat.id);
    setStreaming(false);
    setError(undefined);
  }, []);

  const selectChat = useCallback((id: string) => {
    if (streaming) return;
    setActiveChatId(id);
    setError(undefined);
  }, [streaming]);

  const deleteChat = useCallback((id: string) => {
    if (streaming) return;
    const remaining = chats.filter((chat) => chat.id !== id);
    const next = remaining.length ? remaining : [createSherpaChat()];
    setChats(next);
    if (activeChatId === id) setActiveChatId(next[0].id);
  }, [activeChatId, chats, streaming]);

  const send = useCallback(async (content: string) => {
    const message = content.trim();
    if (!message || streaming || !activeChat) return;
    const chatId = activeChat.id;
    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      blocks: [{ id: crypto.randomUUID(), kind: "text", content: message }],
    };
    setChats((current) => current.map((chat) => chat.id === chatId ? {
      ...chat,
      title: chat.messages.length ? chat.title : message.slice(0, 42),
      messages: [...chat.messages, userMessage],
      updatedAt: Date.now(),
    } : chat));
    setStreaming(true);
    setError(undefined);
    const controller = new AbortController();
    controllerRef.current = controller;
    try {
      await streamChat({
        message,
        sessionId: chatId,
        signal: controller.signal,
        onEvent: (event) => updateMessages(chatId, (current) => applyChatEvent(current, event)),
      });
    } catch (reason) {
      if (!(reason instanceof DOMException && reason.name === "AbortError")) {
        setError(reason instanceof Error ? reason.message : "Sherpa chat failed");
      }
    } finally {
      updateMessages(chatId, finishReasoning);
      setStreaming(false);
      controllerRef.current = undefined;
    }
  }, [activeChat, streaming, updateMessages]);

  return { activeChat, activeChatId, chats, deleteChat, error, newChat, selectChat, send, streaming };
}
