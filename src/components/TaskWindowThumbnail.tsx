import type { CSSProperties } from "react";
import type { VoiceTask } from "../hooks/useVoiceSession";
import { TaskPreview } from "./TaskPreview";
import "./TaskWindowThumbnail.css";

type TaskWindowThumbnailProps = {
  index: number;
  onSelect: () => void;
  task: VoiceTask;
};

export function TaskWindowThumbnail({ index, onSelect, task }: TaskWindowThumbnailProps) {
  const label = task.previewTarget?.title || task.previewTarget?.window_title || task.previewTarget?.app || task.instruction;

  return (
    <button
      className="task-window-thumbnail"
      style={{ "--thumbnail-index": index } as CSSProperties}
      type="button"
      aria-label={`Show ${label}`}
      onClick={onSelect}
    >
      <TaskPreview
        active={false}
        apiActivity={task.apiActivity}
        revision={task.previewRevision}
        target={task.previewTarget}
        taskId={task.id}
      />
    </button>
  );
}
