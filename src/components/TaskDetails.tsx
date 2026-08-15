import type { VoiceTask, VoiceTaskUpdate } from "../hooks/useVoiceSession";
import { TaskUpdateList } from "./TaskUpdateList";
import "./TaskDetails.css";

export function TaskDetails({ task }: { task: VoiceTask }) {
  const updates: VoiceTaskUpdate[] = task.result
    ? task.updates.filter((update) => update.message.trim() !== task.result?.trim())
    : task.updates;
  const entries = task.result ? [
    ...updates,
    {
      phase: task.status,
      progress: 100,
      message: task.result,
      nextStep: "",
      createdAt: `result-${task.id}`,
    },
  ] : updates;

  return (
    <div className="task-details">
      {entries.length ? <TaskUpdateList updates={entries} /> : null}
    </div>
  );
}
