import { Mic, Square } from "lucide-react";
import type { CSSProperties } from "react";
import "./PetVoiceButton.css";

type PetVoiceButtonProps = {
  active: boolean;
  hue: number;
  onToggle: () => void;
};

export function PetVoiceButton({ active, hue, onToggle }: PetVoiceButtonProps) {
  return (
    <button
      className="pet-voice-button"
      data-active={active}
      style={{ "--pet-voice-hue": hue } as CSSProperties}
      type="button"
      aria-label={active ? "Stop voice" : "Start voice"}
      onClick={onToggle}
    >
      {active ? <Square aria-hidden="true" /> : <Mic aria-hidden="true" />}
    </button>
  );
}
