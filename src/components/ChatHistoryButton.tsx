import { PanelLeft } from "lucide-react";
import "./ChatHistoryButton.css";

export function ChatHistoryButton({ onClick }: { onClick: () => void }) {
  return (
    <button className="chat-history-button" aria-label="Open chat history" onClick={onClick} type="button">
      <PanelLeft aria-hidden="true" />
    </button>
  );
}
