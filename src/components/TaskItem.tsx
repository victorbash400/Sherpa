import { useState } from "react";
import { Check, ChevronDown, LoaderCircle } from "lucide-react";
import type { VoiceTask } from "../hooks/useVoiceSession";
import { TaskDetails } from "./TaskDetails";
import "./TaskItem.css";

export function TaskItem({ onSelect, selected, task }: { onSelect: () => void; selected: boolean; task: VoiceTask }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <article className="task-item" data-expanded={expanded} data-phase={task.phase} data-selected={selected} data-status={task.status}>
      <button
        type="button"
        aria-expanded={expanded}
        aria-label={`${task.instruction}, ${statusLabel(task.status)}`}
        onClick={() => {
          onSelect();
          setExpanded((current) => !current);
        }}
      >
        <span className="task-item__marker" data-status={task.status} aria-hidden="true">
          {task.status === "completed" ? <Check /> : null}
          {task.status === "running" && task.phase !== "queued" ? <LoaderCircle /> : null}
        </span>
        <span className="task-item__copy">
          <strong>{task.instruction}</strong>
        </span>
        <ChevronDown className="task-item__chevron" aria-hidden="true" />
      </button>
      <div className="task-item__reveal" aria-hidden={!expanded} inert={!expanded}>
        <div>
          <TaskDetails task={task} />
        </div>
      </div>
    </article>
  );
}

function statusLabel(status: VoiceTask["status"]) {
  if (status === "running") return "Working";
  if (status === "queued") return "Queued";
  if (status === "blocked") return "Waiting for input";
  if (status === "completed") return "Completed";
  if (status === "cancelled") return "Cancelled";
  return "Failed";
}
