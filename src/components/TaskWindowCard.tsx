import { Maximize2, Minimize2 } from "lucide-react";
import type { VoiceTask } from "../hooks/useVoiceSession";
import { TaskPreview } from "./TaskPreview";
import "./TaskWindowCard.css";

type TaskWindowCardProps = {
  active: boolean;
  expanded: boolean;
  onExpand: () => void;
  task: VoiceTask;
};

export function TaskWindowCard({ active, expanded, onExpand, task }: TaskWindowCardProps) {
  const label = task.previewTarget?.title || task.previewTarget?.window_title || task.previewTarget?.app || "Task window";

  return (
    <article className="task-window-card" data-active={active} data-expanded={expanded} aria-label={label}>
      <TaskPreview
        active={active}
        cursor={active ? task.previewCursor : undefined}
        revision={task.previewRevision}
        target={task.previewTarget}
        taskId={task.id}
      />
      <button
        className="task-window-card__expand"
        type="button"
        aria-label={expanded ? "Collapse window preview" : "Expand window preview"}
        onClick={onExpand}
      >
        {expanded ? <Minimize2 aria-hidden="true" /> : <Maximize2 aria-hidden="true" />}
      </button>
    </article>
  );
}
