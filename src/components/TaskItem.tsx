import type { VoiceTask } from "../hooks/useVoiceSession";
import "./TaskItem.css";

export function TaskItem({ task }: { task: VoiceTask }) {
  return (
    <article className="task-item">
      <span data-status={task.status} aria-hidden="true" />
      <div>
        <strong>{task.instruction}</strong>
        <p>{task.result || statusLabel(task.status)}</p>
      </div>
    </article>
  );
}

function statusLabel(status: VoiceTask["status"]) {
  if (status === "running") return "Working";
  if (status === "completed") return "Completed";
  if (status === "cancelled") return "Cancelled";
  return "Failed";
}
