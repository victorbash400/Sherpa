import { useEffect, useRef } from "react";
import type { ChatMessage } from "../chat/chatTypes";
import { MessageBubble } from "./MessageBubble";
import { TypingIndicator } from "./TypingIndicator";
import "./MessageList.css";

export function MessageList({ messages, waiting }: { messages: ChatMessage[]; waiting: boolean }) {
  const listRef = useRef<HTMLElement>(null);

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight });
  }, [messages, waiting]);

  return (
    <section className="message-list" aria-live="polite" ref={listRef}>
      {messages.map((message) => <MessageBubble key={message.id} message={message} />)}
      {waiting ? <TypingIndicator /> : null}
    </section>
  );
}
