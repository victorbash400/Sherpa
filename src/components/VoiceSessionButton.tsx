import type { VoiceStatus } from "../hooks/useVoiceSession";
import "./VoiceSessionButton.css";

interface VoiceSessionButtonProps {
  hue: number;
  onStart: () => void;
  onStop: () => void;
  status: VoiceStatus;
}

export function VoiceSessionButton({ hue, onStart, onStop, status }: VoiceSessionButtonProps) {
  const active = status === "connecting" || status === "listening" || status === "speaking";

  return (
    <button
      className="voice-session-button"
      aria-label={active ? "Stop voice session" : "Start voice session"}
      data-active={active}
      disabled={status === "connecting"}
      onClick={active ? onStop : onStart}
      type="button"
    >
      {active ? (
        <img alt="" aria-hidden="true" src="/stop-svgrepo-com.svg" />
      ) : (
        <span
          aria-hidden="true"
          className="voice-session-button__start-icon"
          style={{ color: `hsl(${(hue + 258) % 360} 62% 51%)` }}
        />
      )}
    </button>
  );
}
