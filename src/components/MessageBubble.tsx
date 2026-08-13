import type { ChatMessage } from "../chat/chatTypes";
import { Markdown } from "./Markdown";
import { ThinkingIndicator } from "./ThinkingIndicator";
import { ToolCallIndicator } from "./ToolCallIndicator";
import "./MessageBubble.css";

export function MessageBubble({ message }: { message: ChatMessage }) {
  return (
    <article className="message-bubble" data-role={message.role}>
      {message.blocks.map((block) => {
        if (block.kind === "reasoning") return <ThinkingIndicator block={block} key={block.id} />;
        if (block.kind === "tool") return <ToolCallIndicator key={block.id} tool={block.tool} />;
        return <Markdown content={block.content} key={block.id} />;
      })}
    </article>
  );
}
