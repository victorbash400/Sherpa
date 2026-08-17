import type { TaskApiActivity } from "../hooks/useVoiceSession";
import type { PreviewCursor, PreviewTarget } from "../types/sherpaOverlay";
import { TaskApiActivityPreview } from "./TaskApiActivityPreview";
import { WindowTaskPreview } from "./WindowTaskPreview";
import { WorkspaceTaskPreview } from "./WorkspaceTaskPreview";
import "./TaskPreview.css";

type TaskPreviewProps = {
  active: boolean;
  cursor?: PreviewCursor;
  revision?: string;
  target?: PreviewTarget;
  taskId: string;
  apiActivity?: TaskApiActivity;
};

export function TaskPreview({ active, apiActivity, cursor, revision, target, taskId }: TaskPreviewProps) {
  if (apiActivity) return <TaskApiActivityPreview activity={apiActivity} />;
  if (target?.kind === "workspace" && target.resource_id) {
    return <WorkspaceTaskPreview key={`${target.resource_id}:${target.revision || ""}`} target={target} />;
  }
  return <WindowTaskPreview active={active} cursor={cursor} revision={revision} target={target} taskId={taskId} />;
}
