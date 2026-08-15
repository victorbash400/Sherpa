import type { PreviewCursor, PreviewTarget } from "../types/sherpaOverlay";
import { WindowTaskPreview } from "./WindowTaskPreview";
import { WorkspaceTaskPreview } from "./WorkspaceTaskPreview";
import "./TaskPreview.css";

type TaskPreviewProps = {
  active: boolean;
  cursor?: PreviewCursor;
  revision?: string;
  target?: PreviewTarget;
  taskId: string;
};

export function TaskPreview({ active, cursor, revision, target, taskId }: TaskPreviewProps) {
  if (target?.kind === "workspace" && target.resource_id) {
    return <WorkspaceTaskPreview key={`${target.resource_id}:${target.revision || ""}`} target={target} />;
  }
  return <WindowTaskPreview active={active} cursor={cursor} revision={revision} target={target} taskId={taskId} />;
}
