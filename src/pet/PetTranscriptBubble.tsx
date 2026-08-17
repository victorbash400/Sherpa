import type { CSSProperties } from "react";
import type { PetActivity } from "../types/sherpaOverlay";
import "../components/TranscriptGlass.css";
import "./PetTranscriptBubble.css";

export function PetTranscriptBubble({ transcript }: { transcript: PetActivity["transcript"] }) {
  const text = transcript.entries.at(-1)?.text.trim()
    || (transcript.status === "listening" ? "Listening…" : transcript.status === "speaking" ? "Speaking…" : "Sherpa is ready.");

  return (
    <aside
      className="pet-transcript-bubble transcript-glass"
      aria-live="polite"
      style={{ "--transcript-hue": transcript.hue } as CSSProperties}
    >
      <span>{text}</span>
    </aside>
  );
}
