import { ArrowUp } from "lucide-react";
import "./SendButton.css";

export function SendButton({ disabled }: { disabled: boolean }) {
  return (
    <button className="send-button" aria-label="Send" disabled={disabled} type="submit">
      <ArrowUp aria-hidden="true" />
    </button>
  );
}
