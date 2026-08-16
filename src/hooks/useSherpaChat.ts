import { useCallback, useEffect, useRef, useState } from "react";
import { applyChatEvent, finishReasoning } from "../chat/chatEvents";
import { createSherpaChat, loadSherpaChats, saveSherpaChats } from "../chat/chatStorage";
import { streamChat } from "../chat/chatStream";
import { generateChatTitle } from "../chat/chatTitle";
import type { ChatMessage, SherpaChat, VoiceTranscriptEntry } from "../chat/chatTypes";

export function useSherpaChat() {
  const [chats, setChats] = useState<SherpaChat[]>(() => {
    const stored = loadSherpaChats();
    return stored.length ? stored : [createSherpaChat()];
  });
  const [activeChatId, setActiveChatId] = useState(() => chats[0].id);
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState<string>();
  const controllerRef = useRef<AbortController | undefined>(undefined);
  const namingChatIdsRef = useRef(new Set<string>());
  const chatsRef = useRef(chats);
  chatsRef.current = chats;
  const activeChat = chats.find((chat) => chat.id === activeChatId) ?? chats[0];

  useEffect(() => saveSherpaChats(chats), [chats]);
  useEffect(() => () => controllerRef.current?.abort(), []);

  const nameChat = useCallback(async (chatId: string, userText: string, assistantText: string) => {
    const chat = chatsRef.current.find((item) => item.id === chatId);
    if (
      !chat
      || chat.titleStatus !== "pending"
      || namingChatIdsRef.current.has(chatId)
      || !userText.trim()
      || !assistantText.trim()
    ) return;
    namingChatIdsRef.current.add(chatId);
    setChats((current) => current.map((item) => item.id === chatId
      ? { ...item, titleStatus: "naming" }
      : item));
    try {
      const title = await generateChatTitle(userText, assistantText);
      setChats((current) => current.map((item) => item.id === chatId
        ? { ...item, title, titleStatus: "complete", updatedAt: Date.now() }
        : item));
    } catch {
      setChats((current) => current.map((item) => item.id === chatId
        ? { ...item, titleStatus: "failed" }
        : item));
    }
  }, []);

  const updateMessages = useCallback((chatId: string, update: (messages: ChatMessage[]) => ChatMessage[]) => {
    setChats((current) => current.map((chat) => chat.id === chatId ? {
      ...chat,
      messages: update(chat.messages),
      updatedAt: Date.now(),
    } : chat));
  }, []);

  const appendTranscript = useCallback((chatId: string, role: VoiceTranscriptEntry["role"], text: string) => {
    if (!text) return;
    const nextChats = chatsRef.current.map((chat) => {
      if (chat.id !== chatId) return chat;
      const latest = chat.transcript.at(-1);
      const transcript = latest?.role === role
        ? [...chat.transcript.slice(0, -1), { ...latest, text: mergeTranscript(latest.text, text) }]
        : [...chat.transcript, { id: crypto.randomUUID(), role, text }];
      return {
        ...chat,
        title: chat.transcript.length || role !== "user" ? chat.title : text.slice(0, 42),
        transcript,
        updatedAt: Date.now(),
      };
    });
    chatsRef.current = nextChats;
    setChats(nextChats);
  }, []);

  const completeVoiceTurn = useCallback((chatId: string) => {
    const transcript = chatsRef.current.find((chat) => chat.id === chatId)?.transcript ?? [];
    let assistantIndex = -1;
    for (let index = transcript.length - 1; index >= 0; index -= 1) {
      if (transcript[index].role === "assistant" && transcript[index].text.trim()) {
        assistantIndex = index;
        break;
      }
    }
    if (assistantIndex < 0) return;
    let user: VoiceTranscriptEntry | undefined;
    for (let index = assistantIndex - 1; index >= 0; index -= 1) {
      if (transcript[index].role === "user" && transcript[index].text.trim()) {
        user = transcript[index];
        break;
      }
    }
    const assistant = transcript[assistantIndex];
    if (user && assistant) void nameChat(chatId, user.text, assistant.text);
  }, [nameChat]);

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
    let assistantText = "";
    try {
      await streamChat({
        message,
        sessionId: chatId,
        signal: controller.signal,
        onEvent: (event) => {
          if (event.type === "content") assistantText += event.content;
          updateMessages(chatId, (current) => applyChatEvent(current, event));
        },
      });
      await nameChat(chatId, message, assistantText);
    } catch (reason) {
      if (!(reason instanceof DOMException && reason.name === "AbortError")) {
        setError(reason instanceof Error ? reason.message : "Sherpa chat failed");
      }
    } finally {
      updateMessages(chatId, finishReasoning);
      setStreaming(false);
      controllerRef.current = undefined;
    }
  }, [activeChat, nameChat, streaming, updateMessages]);

  return { activeChat, activeChatId, appendTranscript, chats, completeVoiceTurn, deleteChat, error, newChat, selectChat, send, streaming };
}

function mergeTranscript(current: string, incoming: string) {
  if (current === incoming || current.endsWith(incoming)) return current;
  if (incoming.startsWith(current)) return incoming;
  const needsSpace = !current.endsWith(" ") && !incoming.startsWith(" ");
  return `${current}${needsSpace ? " " : ""}${incoming}`;
}
