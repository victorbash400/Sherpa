import { Circle, Mic } from "lucide-react";
import { publicAssetUrl } from "../assets/publicAssetUrl";
import { CursorDock } from "./CursorDock";
import "./ControlRail.css";

interface ControlRailProps {
  activeView: "voice" | "chat" | "voices" | "tasks" | "memory" | "plugins" | "skills" | "workspace" | "accessibility" | "pets";
  computerActive: boolean;
  expanded: boolean;
  onOpenVoice: () => void;
  onOpenMemory: () => void;
  onOpenTasks: () => void;
  onOpenVoices: () => void;
  onOpenPlugins: () => void;
  onOpenSkills: () => void;
  onOpenWorkspace: () => void;
  onOpenAccessibility: () => void;
  onOpenPets: () => void;
}

export function ControlRail({ activeView, computerActive, expanded, onOpenAccessibility, onOpenMemory, onOpenPets, onOpenPlugins, onOpenSkills, onOpenTasks, onOpenVoice, onOpenVoices, onOpenWorkspace }: ControlRailProps) {
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
          <img alt="" aria-hidden="true" src={publicAssetUrl("plugin-svgrepo-com (2).svg")} />
          <span>Plugins</span>
        </button>
        <button type="button" aria-label="Skills" aria-pressed={activeView === "skills"} title="Skills" onClick={onOpenSkills}>
          <img alt="" aria-hidden="true" src={publicAssetUrl("scroll-svgrepo-com (2).svg")} />
          <span>Skills</span>
        </button>
        <button type="button" aria-label="Google Workspace" aria-pressed={activeView === "workspace"} title="Google Workspace" onClick={onOpenWorkspace}>
          <img className="control-rail__icon--dark" alt="" aria-hidden="true" src={publicAssetUrl("work-svgrepo-com.svg")} />
          <span>Workspace</span>
        </button>
        <button
          type="button"
          aria-label="Tasks"
          aria-pressed={activeView === "tasks"}
          title="Tasks"
          onClick={onOpenTasks}
        >
          <img alt="" aria-hidden="true" src={publicAssetUrl("task-square-svgrepo-com.svg")} />
          <span>Tasks</span>
        </button>
        <button
          type="button"
          aria-label="Memory"
          aria-pressed={activeView === "memory"}
          title="Memory"
          onClick={onOpenMemory}
        >
          <img alt="" aria-hidden="true" src={publicAssetUrl("brain-fill-svgrepo-com.svg")} />
          <span>Memory</span>
        </button>
        <button
          type="button"
          aria-label="Accessibility"
          aria-pressed={activeView === "accessibility"}
          title="Accessibility"
          onClick={onOpenAccessibility}
        >
          <img alt="" aria-hidden="true" src={publicAssetUrl("accessibility-svgrepo-com.svg")} />
          <span>Accessibility</span>
        </button>
        <button type="button" aria-label="Pets" aria-pressed={activeView === "pets"} title="Pets" onClick={onOpenPets}>
          <img className="control-rail__icon--dark" alt="" aria-hidden="true" src={publicAssetUrl("pet-svgrepo-com.svg")} />
          <span>Pets</span>
        </button>
        {computerActive ? <CursorDock /> : null}
      </div>
    </nav>
  );
}
