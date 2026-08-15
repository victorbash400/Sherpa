import { Circle, Mic } from "lucide-react";
import { CursorDock } from "./CursorDock";
import "./ControlRail.css";

interface ControlRailProps {
  activeView: "voice" | "chat" | "voices" | "tasks" | "memory" | "plugins" | "workspace" | "accessibility";
  computerActive: boolean;
  expanded: boolean;
  onOpenVoice: () => void;
  onOpenMemory: () => void;
  onOpenTasks: () => void;
  onOpenVoices: () => void;
  onOpenPlugins: () => void;
  onOpenWorkspace: () => void;
  onOpenAccessibility: () => void;
}

export function ControlRail({ activeView, computerActive, expanded, onOpenAccessibility, onOpenMemory, onOpenPlugins, onOpenTasks, onOpenVoice, onOpenVoices, onOpenWorkspace }: ControlRailProps) {
  return (
    <nav className="control-rail" data-expanded={expanded} aria-label="Sherpa controls">
      <span className="control-rail__title">Sherpa</span>
      <div className="control-rail__actions">
        <button
          type="button"
          aria-label="Voice chat"
          aria-pressed={activeView === "voice"}
          title="Voice chat"
          onClick={onOpenVoice}
        >
          <Circle aria-hidden="true" />
          <span>Voice</span>
        </button>
        <button
          type="button"
          aria-label="Choose voice"
          aria-pressed={activeView === "voices"}
          title="Voice"
          onClick={onOpenVoices}
        >
          <Mic aria-hidden="true" />
          <span>Voices</span>
        </button>
        <button type="button" aria-label="Plugins" aria-pressed={activeView === "plugins"} title="Plugins" onClick={onOpenPlugins}>
          <img alt="" aria-hidden="true" src="/plugin-svgrepo-com (2).svg" />
          <span>Plugins</span>
        </button>
        <button type="button" aria-label="Google Workspace" aria-pressed={activeView === "workspace"} title="Google Workspace" onClick={onOpenWorkspace}>
          <img alt="" aria-hidden="true" src="/gnome-panel-workspace-switcher-svgrepo-com.svg" />
          <span>Workspace</span>
        </button>
        <button
          type="button"
          aria-label="Tasks"
          aria-pressed={activeView === "tasks"}
          title="Tasks"
          onClick={onOpenTasks}
        >
          <img alt="" aria-hidden="true" src="/task-square-svgrepo-com.svg" />
          <span>Tasks</span>
        </button>
        <button
          type="button"
          aria-label="Memory"
          aria-pressed={activeView === "memory"}
          title="Memory"
          onClick={onOpenMemory}
        >
          <img alt="" aria-hidden="true" src="/brain-fill-svgrepo-com.svg" />
          <span>Memory</span>
        </button>
        <button
          type="button"
          aria-label="Accessibility"
          aria-pressed={activeView === "accessibility"}
          title="Accessibility"
          onClick={onOpenAccessibility}
        >
          <img alt="" aria-hidden="true" src="/accessibility-svgrepo-com.svg" />
          <span>Accessibility</span>
        </button>
        {computerActive ? <CursorDock /> : null}
      </div>
    </nav>
  );
}
