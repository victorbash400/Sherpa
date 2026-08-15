import type { CSSProperties } from "react";
import type { PreviewCursor } from "../types/sherpaOverlay";

export function TaskPreviewCursor({ cursor, position }: { cursor: PreviewCursor; position: CSSProperties }) {
  return (
    <span
      key={cursor.id}
      className="task-preview__cursor"
      data-click={cursor.action.includes("click")}
      style={position}
      aria-hidden="true"
    />
  );
}
