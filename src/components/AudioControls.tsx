import { Mic, MicOff, Volume2, VolumeOff } from "lucide-react";
import "./AudioControls.css";

interface AudioControlsProps {
  microphoneMuted: boolean;
  speakerMuted: boolean;
  volume: number;
  onMicrophoneMutedChange: (muted: boolean) => void;
  onSpeakerMutedChange: (muted: boolean) => void;
  onVolumeChange: (volume: number) => void;
}

export function AudioControls({
  microphoneMuted,
  speakerMuted,
  volume,
  onMicrophoneMutedChange,
  onSpeakerMutedChange,
  onVolumeChange,
}: AudioControlsProps) {
  return (
    <section className="audio-controls" aria-label="Audio controls">
      <button
        type="button"
        aria-label={microphoneMuted ? "Unmute microphone" : "Mute microphone"}
        aria-pressed={microphoneMuted}
        onClick={() => onMicrophoneMutedChange(!microphoneMuted)}
      >
        {microphoneMuted ? <MicOff aria-hidden="true" /> : <Mic aria-hidden="true" />}
      </button>
      <button
        type="button"
        aria-label={speakerMuted ? "Unmute speaker" : "Mute speaker"}
        aria-pressed={speakerMuted}
        onClick={() => onSpeakerMutedChange(!speakerMuted)}
      >
        {speakerMuted ? <VolumeOff aria-hidden="true" /> : <Volume2 aria-hidden="true" />}
      </button>
      <input
        type="range"
        min="0"
        max="100"
        value={speakerMuted ? 0 : volume}
        aria-label="Speaker volume"
        onChange={(event) => {
          const nextVolume = Number(event.target.value);
          onVolumeChange(nextVolume);
          onSpeakerMutedChange(nextVolume === 0);
        }}
      />
    </section>
  );
}
