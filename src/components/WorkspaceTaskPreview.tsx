import { useState } from "react";
import type { PreviewTarget } from "../types/sherpaOverlay";

export function WorkspaceTaskPreview({ target }: { target: PreviewTarget }) {
  const [failed, setFailed] = useState(false);
  const label = target.title || "Workspace document";
  const revision = encodeURIComponent(target.revision || "current");
  const source = `http://127.0.0.1:8000/workspace/previews/${encodeURIComponent(target.resource_id || "")}?revision=${revision}`;

  return (
    <section className="task-preview" aria-label={`${label} preview`}>
      <div className="task-preview__screen">
        {failed ? <p>Preview unavailable for this Workspace file</p> : (
          <img alt={`Preview of ${label}`} onError={() => setFailed(true)} src={source} />
        )}
      </div>
    </section>
  );
}
