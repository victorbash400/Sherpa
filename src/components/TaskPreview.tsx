import { Maximize2, Minimize2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import type { PreviewBounds, PreviewCursor, PreviewTarget } from "../types/sherpaOverlay";
import "./TaskPreview.css";

type TaskPreviewProps = {
  active: boolean;
  cursor?: PreviewCursor;
  target?: PreviewTarget;
  taskId: string;
};

export function TaskPreview({ active, cursor, target, taskId }: TaskPreviewProps) {
  const [expanded, setExpanded] = useState(false);
  const [frame, setFrame] = useState<string>();
  const [error, setError] = useState<string>();
  const [bounds, setBounds] = useState<PreviewBounds>();
  const frameUrl = useRef<string | undefined>(undefined);

  useEffect(() => {
    const bridge = window.sherpaPreview;
    if (!active || !bridge || !target) return;
    setError(undefined);
    const removeFrame = bridge.onFrame((frameTaskId, nextFrame) => {
      if (frameTaskId !== taskId) return;
      if (frameUrl.current) URL.revokeObjectURL(frameUrl.current);
      const bytes = new Uint8Array(nextFrame);
      frameUrl.current = URL.createObjectURL(new Blob([bytes.buffer], { type: "image/jpeg" }));
      setFrame(frameUrl.current);
    });
    const removeError = bridge.onError((errorTaskId, message) => {
      if (errorTaskId === taskId) setError(message);
    });
    const removeMetadata = bridge.onMetadata((metadataTaskId, nextBounds) => {
      if (metadataTaskId === taskId) setBounds(nextBounds);
    });
    void bridge.start(taskId, target).then((started) => {
      if (!started) setError("This window cannot be previewed.");
    });
    return () => {
      bridge.stop(taskId);
      removeFrame();
      removeError();
      removeMetadata();
      if (frameUrl.current) URL.revokeObjectURL(frameUrl.current);
      frameUrl.current = undefined;
    };
  }, [active, target?.app, target?.pid, target?.window_id, target?.window_title, taskId]);

  useEffect(() => {
    if (!expanded) return;
    const close = (event: KeyboardEvent) => {
      if (event.key === "Escape") setExpanded(false);
    };
    window.addEventListener("keydown", close);
    return () => window.removeEventListener("keydown", close);
  }, [expanded]);

  const label = target?.window_title || target?.app || (target?.pid ? `Process ${target.pid}` : "Assigned window");
  const cursorPosition = cursor && bounds ? {
    left: `${Math.max(0, Math.min(100, ((cursor.x - bounds.x) / bounds.width) * 100))}%`,
    top: `${Math.max(0, Math.min(100, ((cursor.y - bounds.y) / bounds.height) * 100))}%`,
  } : undefined;

  return (
    <section className="task-preview" data-expanded={expanded} aria-label={`${label} preview`}>
      <div className="task-preview__screen">
        {frame ? <img alt={`Live view of ${label}`} src={frame} /> : (
          <p>{error || (target ? "Connecting to window" : "Waiting for a window")}</p>
        )}
        {cursorPosition && cursor ? (
          <span
            key={cursor.id}
            className="task-preview__cursor"
            data-click={cursor.action.includes("click")}
            style={cursorPosition}
            aria-hidden="true"
          />
        ) : null}
      </div>
      {frame ? (
        <button
          className="task-preview__expand"
          type="button"
          aria-label={expanded ? "Collapse window preview" : "Expand window preview"}
          onClick={() => setExpanded((current) => !current)}
        >
          {expanded ? <Minimize2 aria-hidden="true" /> : <Maximize2 aria-hidden="true" />}
        </button>
      ) : null}
    </section>
  );
}
