import { useEffect, useRef, useState } from "react";
import type { PreviewBounds, PreviewCursor, PreviewTarget } from "../types/sherpaOverlay";
import { TaskPreviewCursor } from "./TaskPreviewCursor";
import "./TaskPreview.css";

type TaskPreviewProps = {
  active: boolean;
  cursor?: PreviewCursor;
  revision?: string;
  target?: PreviewTarget;
  taskId: string;
};

export function TaskPreview({ active, cursor, revision, target, taskId }: TaskPreviewProps) {
  const [frame, setFrame] = useState<string>();
  const [error, setError] = useState<string>();
  const [bounds, setBounds] = useState<PreviewBounds>();
  const frameUrl = useRef<string | undefined>(undefined);
  const capturedTarget = useRef<string | undefined>(undefined);
  const retryPending = useRef(false);
  const targetKey = target ? `${target.app || ""}:${target.pid || ""}:${target.window_id || ""}:${target.window_title || ""}` : "";
  const shouldCapture = active || capturedTarget.current !== targetKey;

  useEffect(() => {
    const bridge = window.sherpaPreview;
    if (!shouldCapture || !bridge || !target) return;
    setError(undefined);
    const removeFrame = bridge.onFrame((frameTaskId, nextFrame) => {
      if (frameTaskId !== taskId) return;
      if (frameUrl.current) URL.revokeObjectURL(frameUrl.current);
      const bytes = new Uint8Array(nextFrame);
      frameUrl.current = URL.createObjectURL(new Blob([bytes.buffer], { type: "image/jpeg" }));
      capturedTarget.current = targetKey;
      setFrame(frameUrl.current);
      retryPending.current = false;
    });
    const removeError = bridge.onError((errorTaskId, message) => {
      if (errorTaskId === taskId) {
        retryPending.current = true;
        setError(message);
      }
    });
    const removeMetadata = bridge.onMetadata((metadataTaskId, nextBounds) => {
      if (metadataTaskId === taskId) setBounds(nextBounds);
    });
    void bridge.start(taskId, target).then((started) => {
      if (!started) {
        retryPending.current = true;
        setError("This window cannot be previewed.");
      }
    });
    return () => {
      bridge.stop(taskId);
      removeFrame();
      removeError();
      removeMetadata();
    };
  }, [shouldCapture, targetKey, target?.app, target?.pid, target?.window_id, target?.window_title, taskId]);

  useEffect(() => () => {
    if (frameUrl.current) URL.revokeObjectURL(frameUrl.current);
    frameUrl.current = undefined;
  }, []);

  useEffect(() => {
    if (!shouldCapture || !revision || !target || !retryPending.current) return;
    retryPending.current = false;
    void window.sherpaPreview?.start(taskId, target);
  }, [shouldCapture, revision, target?.app, target?.pid, target?.window_id, target?.window_title, taskId]);

  const label = target?.window_title || target?.app || (target?.pid ? `Process ${target.pid}` : "Assigned window");
  const cursorPosition = cursor && bounds ? {
    left: `${Math.max(0, Math.min(100, ((cursor.x - bounds.x) / bounds.width) * 100))}%`,
    top: `${Math.max(0, Math.min(100, ((cursor.y - bounds.y) / bounds.height) * 100))}%`,
  } : undefined;

  return (
    <section className="task-preview" aria-label={`${label} preview`}>
      <div className="task-preview__screen">
        {frame ? <img alt={`Live view of ${label}`} src={frame} /> : (
          <p>{error || (target ? "Connecting to window" : "Waiting for a window")}</p>
        )}
        {cursorPosition && cursor ? <TaskPreviewCursor cursor={cursor} position={cursorPosition} /> : null}
      </div>
    </section>
  );
}
