import { Mic, Settings } from "lucide-react";
import { CursorDock } from "./CursorDock";
import "./ControlRail.css";

interface ControlRailProps {
  activeView: "voice" | "chat" | "voices" | "tasks" | "memory";
  computerActive: boolean;
  onOpenMemory: () => void;
  onOpenTasks: () => void;
  onOpenVoices: () => void;
  onOpenSettings: () => void;
}

export function ControlRail({ activeView, computerActive, onOpenMemory, onOpenTasks, onOpenVoices, onOpenSettings }: ControlRailProps) {
  return (
    <nav className="control-rail" aria-label="Sherpa controls">
      <span className="control-rail__title">Sherpa</span>
      <div className="control-rail__actions">
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
        <CursorDock active={computerActive} />
      </div>
    </nav>
  );
}
