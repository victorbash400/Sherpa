import { ChevronDown, ChevronRight } from "lucide-react";
import { useEffect, useState } from "react";
import type { ChatBlock } from "../chat/chatTypes";
import { Markdown } from "./Markdown";
import "./ThinkingIndicator.css";

type ReasoningBlock = Extract<ChatBlock, { kind: "reasoning" }>;

export function ThinkingIndicator({ block }: { block: ReasoningBlock }) {
  const [open, setOpen] = useState(false);
  const [now, setNow] = useState(() => Date.now());
  const streaming = !block.finishedAt;

  useEffect(() => {
    if (!streaming) return;
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, [streaming]);

  const expanded = streaming || open;
  const seconds = Math.max(1, Math.round(((block.finishedAt || now) - block.startedAt) / 1000));

  return (
    <section className="thinking-indicator">
      <button type="button" onClick={() => setOpen((value) => !value)}>
        {expanded ? <ChevronDown aria-hidden="true" /> : <ChevronRight aria-hidden="true" />}
        {streaming ? "Thinking" : `Thought for ${seconds}s`}
        {streaming ? <i aria-hidden="true" /> : null}
      </button>
      {expanded ? <Markdown content={block.content} /> : null}
    </section>
  );
}
