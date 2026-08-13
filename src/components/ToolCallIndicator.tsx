import { SquareTerminal } from "lucide-react";
import type { ToolCall } from "../chat/chatTypes";
import "./ToolCallIndicator.css";

export function ToolCallIndicator({ tool }: { tool: ToolCall }) {
  return (
    <span className="tool-call-indicator" data-status={tool.status}>
      <SquareTerminal aria-hidden="true" />
      <strong>{tool.name.replaceAll("_", " ")}</strong>
    </span>
  );
}
