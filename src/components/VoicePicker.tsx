import { ChevronLeft, ChevronRight } from "lucide-react";
import { Orb } from "./Orb";
import type { VoiceOption } from "../voice/voiceOptions";
import { voiceOptions } from "../voice/voiceOptions";
import "./VoicePicker.css";

interface VoicePickerProps {
  error?: string;
  onPreview: () => void;
  onSelect: (voice: VoiceOption) => void;
  previewing: boolean;
  selected: VoiceOption;
}

export function VoicePicker({ error, onPreview, onSelect, previewing, selected }: VoicePickerProps) {
  const selectedIndex = voiceOptions.findIndex((voice) => voice.id === selected.id);
  const move = (direction: number) => {
    const nextIndex = (selectedIndex + direction + voiceOptions.length) % voiceOptions.length;
    onSelect(voiceOptions[nextIndex]);
  };

  return (
    <section className="voice-picker" aria-label="Choose voice">
      <header>Voice</header>
      <div className="voice-picker__carousel">
        <button aria-label="Previous voice" onClick={() => move(-1)} type="button"><ChevronLeft aria-hidden="true" /></button>
        <div className="voice-picker__orb"><Orb audioLevel={0} hue={selected.hue} mode="idle" /></div>
        <button aria-label="Next voice" onClick={() => move(1)} type="button"><ChevronRight aria-hidden="true" /></button>
      </div>
      <strong>{selected.name}</strong>
      <span>{selected.description}</span>
      <button className="voice-picker__preview" disabled={previewing} onClick={onPreview} type="button">
        {previewing ? "Playing" : "Try this voice"}
      </button>
      {error ? <p role="alert">{error}</p> : null}
      <nav aria-label="Voice choices">
        {voiceOptions.map((voice) => (
          <button
            aria-label={`Choose ${voice.name}`}
            aria-current={voice.id === selected.id ? "true" : undefined}
            key={voice.id}
            onClick={() => onSelect(voice)}
            type="button"
          />
        ))}
      </nav>
    </section>
  );
}
