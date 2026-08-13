import { Circle, Mic, Settings } from "lucide-react";
import "./ControlRail.css";

interface ControlRailProps {
  activeView: "voice" | "chat" | "voices";
  onOpenVoices: () => void;
  onToggleChat: () => void;
  onOpenSettings: () => void;
}

export function ControlRail({ activeView, onOpenVoices, onToggleChat, onOpenSettings }: ControlRailProps) {
  return (
    <nav className="control-rail" aria-label="Sherpa controls">
      <span className="control-rail__title">Sherpa</span>
      <div className="control-rail__actions">
        <button
          type="button"
          aria-label={activeView === "chat" ? "Open orb view" : "Open code view"}
          aria-pressed={activeView === "chat"}
          title={activeView === "chat" ? "Orb view" : "Code view"}
          onClick={onToggleChat}
        >
          {activeView === "chat" ? <Circle aria-hidden="true" className="control-rail__orb-icon" /> : <img alt="" aria-hidden="true" src="/logs-svgrepo-com.svg" />}
        </button>
        <button
          type="button"
          aria-label="Choose voice"
          aria-pressed={activeView === "voices"}
          title="Voice"
          onClick={onOpenVoices}
        >
          <Mic aria-hidden="true" />
        </button>
        <button type="button" aria-label="Settings" title="Settings" onClick={onOpenSettings}>
          <Settings aria-hidden="true" />
        </button>
      </div>
    </nav>
  );
}
