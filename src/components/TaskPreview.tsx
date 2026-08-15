import { Maximize2, Minimize2, Monitor } from "lucide-react";
import { useEffect, useState } from "react";
import type { PreviewTarget } from "../types/sherpaOverlay";
import "./TaskPreview.css";

type TaskPreviewProps = {
  active: boolean;
  interactionMode?: "background" | "foreground";
  target?: PreviewTarget;
  taskId: string;
};

export function TaskPreview({ active, interactionMode, target, taskId }: TaskPreviewProps) {
  const [expanded, setExpanded] = useState(false);
  const [frame, setFrame] = useState<string>();
  const [error, setError] = useState<string>();

  useEffect(() => {
    const bridge = window.sherpaPreview;
    if (!active || !bridge || !target) return;
    setError(undefined);
    void bridge.start(taskId, target).then((started) => {
      if (!started) setError("This window cannot be previewed.");
    });
    const removeFrame = bridge.onFrame((frameTaskId, nextFrame) => {
      if (frameTaskId === taskId) setFrame(nextFrame);
    });
    const removeError = bridge.onError((errorTaskId, message) => {
      if (errorTaskId === taskId) setError(message);
    });
    return () => {
      bridge.stop(taskId);
      removeFrame();
      removeError();
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

  return (
    <section className="task-preview" data-expanded={expanded} aria-label={`${label} preview`}>
      <header>
        <span><Monitor aria-hidden="true" />{label}</span>
        {frame ? (
          <button
            type="button"
            aria-label={expanded ? "Collapse window preview" : "Expand window preview"}
            onClick={() => setExpanded((current) => !current)}
          >
            {expanded ? <Minimize2 aria-hidden="true" /> : <Maximize2 aria-hidden="true" />}
          </button>
        ) : null}
      </header>
      <div className="task-preview__screen">
        {frame ? <img alt={`Live view of ${label}`} src={frame} /> : (
          <p>{error || (target ? "Connecting to window" : "Waiting for a window")}</p>
        )}
      </div>
      <footer>{interactionMode === "foreground" ? "Foreground control" : "Background control"}</footer>
    </section>
  );
}
