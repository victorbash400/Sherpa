import type { VoiceTask, VoiceTaskUpdate } from "../hooks/useVoiceSession";
import { TaskUpdateList } from "./TaskUpdateList";
import { TaskPreview } from "./TaskPreview";
import "./TaskDetails.css";

export function TaskDetails({ active, task }: { active: boolean; task: VoiceTask }) {
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
      <div className="task-details__updates">
        {entries.length ? <TaskUpdateList updates={entries} /> : null}
      </div>
      <TaskPreview
        active={active}
        cursor={task.previewCursor}
        revision={task.previewRevision}
        target={task.previewTarget}
        taskId={task.id}
      />
    </div>
  );
}
