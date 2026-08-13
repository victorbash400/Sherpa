import { FolderOpen } from "lucide-react";
import "./ChatContext.css";

export function ChatContext({ label }: { label: string }) {
  return (
    <header className="chat-context">
      <FolderOpen aria-hidden="true" />
      <span>{label}</span>
    </header>
  );
}
