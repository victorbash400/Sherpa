import { useLayoutEffect, useRef } from "react";
import { ChatContext } from "./ChatContext";
import { SendButton } from "./SendButton";
import "./ChatInput.css";

interface ChatInputProps {
  disabled: boolean;
  input: string;
  onInputChange: (value: string) => void;
  onSend: () => void;
}

export function ChatInput({ disabled, input, onInputChange, onSend }: ChatInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const canSend = input.trim().length > 0 && !disabled;

  useLayoutEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;
    textarea.style.height = "auto";
    textarea.style.height = `${textarea.scrollHeight}px`;
  }, [input]);

  return (
    <form
      className="chat-input-form"
      onSubmit={(event) => {
        event.preventDefault();
        if (canSend) onSend();
      }}
    >
      <ChatContext label="Gemini 3.7 Flash" />
      <section className="chat-input">
        <textarea
          aria-label="Message Sherpa"
          disabled={disabled}
          onChange={(event) => onInputChange(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              if (canSend) onSend();
            }
          }}
          placeholder="Ask Sherpa anything"
          ref={textareaRef}
          rows={2}
          value={input}
        />
        <footer className="chat-input__toolbar">
          <SendButton disabled={!canSend} />
        </footer>
      </section>
    </form>
  );
}
