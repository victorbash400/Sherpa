import { Orb, type OrbMode } from "./Orb";
import "./FloatingVoiceOrb.css";

interface FloatingVoiceOrbProps {
  audioLevel: number;
  hue: number;
  mode: OrbMode;
}

export function FloatingVoiceOrb({
  audioLevel,
  hue,
  mode,
}: FloatingVoiceOrbProps) {
  return (
    <div className="floating-voice-orb" aria-label="Sherpa voice">
      <Orb audioLevel={audioLevel} hue={hue} mode={mode} />
    </div>
  );
}
