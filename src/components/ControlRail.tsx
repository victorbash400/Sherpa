import { Circle, Mic, Settings } from "lucide-react";
import "./ControlRail.css";

interface ControlRailProps {
  activeView: "voice" | "chat" | "voices" | "tasks" | "memory";
  onOpenMemory: () => void;
  onOpenTasks: () => void;
  onOpenVoices: () => void;
  onToggleChat: () => void;
  onOpenSettings: () => void;
}

export function ControlRail({ activeView, onOpenMemory, onOpenTasks, onOpenVoices, onToggleChat, onOpenSettings }: ControlRailProps) {
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
          {activeView === "chat" ? <Circle aria-hidden="true" className="control-rail__orb-icon" /> : <img alt="" aria-hidden="true" src="/chat-line-svgrepo-com.svg" />}
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
        <button
          type="button"
          aria-label="Tasks"
          aria-pressed={activeView === "tasks"}
          title="Tasks"
          onClick={onOpenTasks}
        >
          <img alt="" aria-hidden="true" src="/task-square-svgrepo-com.svg" />
        </button>
        <button
          type="button"
          aria-label="Memory"
          aria-pressed={activeView === "memory"}
          title="Memory"
          onClick={onOpenMemory}
        >
          <img alt="" aria-hidden="true" src="/brain-fill-svgrepo-com.svg" />
        </button>
      </div>
    </nav>
  );
}
