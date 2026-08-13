import { useState } from "react";
import type { ChatMessage } from "../chat/chatTypes";
import { ChatInput } from "./ChatInput";
import { MessageList } from "./MessageList";
import "./ChatShell.css";

interface ChatShellProps {
  error?: string;
  messages: ChatMessage[];
  onSend: (content: string) => void;
  streaming: boolean;
}

export function ChatShell({ error, messages, onSend, streaming }: ChatShellProps) {
  const [input, setInput] = useState("");

  const submit = () => {
    const content = input.trim();
    if (!content || streaming) return;
    setInput("");
    onSend(content);
  };

  return (
    <section className="chat-shell" aria-label="Sherpa chat">
      <MessageList messages={messages} waiting={streaming && messages.at(-1)?.role === "user"} />
      {error ? <p className="chat-shell__error" role="alert">{error}</p> : null}
      <ChatInput
        disabled={streaming}
        input={input}
        onInputChange={setInput}
        onSend={submit}
      />
    </section>
  );
}
