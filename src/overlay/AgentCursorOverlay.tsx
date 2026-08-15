import { useEffect, useRef, useState } from "react";
import type { OverlayUpdate } from "../types/sherpaOverlay";
import { OverlayObservationIcon } from "./OverlayObservationIcon";
import "./AgentCursorOverlay.css";

export function AgentCursorOverlay() {
  const [action, setAction] = useState<OverlayUpdate>();
  const [animate, setAnimate] = useState(false);
  const actionRef = useRef<OverlayUpdate | undefined>(undefined);

  useEffect(() => {
    const bridge = window.sherpaOverlay;
    if (!bridge) return;
    const stopUpdates = bridge.onUpdate((nextAction) => {
      setAnimate(Boolean(actionRef.current));
      actionRef.current = nextAction;
      setAction(nextAction);
    });
    const stopHides = bridge.onHide(() => {
      actionRef.current = undefined;
      setAnimate(false);
      setAction(undefined);
    });
    bridge.ready();
    return () => {
      stopUpdates();
      stopHides();
    };
  }, []);

  return (
    <div className="overlay-surface">
      <div
        className="agent-cursor-x"
        data-animate={animate}
        style={{ transform: `translate3d(${action?.x ?? 0}px, 0, 0)` }}
      >
        <div
          className="agent-cursor"
          data-animate={animate}
          data-action={action?.action || "idle"}
          data-horizontal={action?.horizontal || "right"}
          data-visible={Boolean(action)}
          data-vertical={action?.vertical || "down"}
          style={{ transform: `translate3d(0, ${action?.y ?? 0}px, 0)` }}
        >
          <span className="agent-cursor__icon" aria-hidden="true" />
          {action?.action.includes("click") ? (
            <span key={action.id} className="agent-cursor__click" aria-hidden="true" />
          ) : null}
          <div className="agent-cursor__label">
            <span className="agent-cursor__label-heading">
              <OverlayObservationIcon action={action?.action} />
              <strong>{action?.message}</strong>
            </span>
            {action?.intent && action.intent !== action.message ? (
              <span className="agent-cursor__intent">{action.intent}</span>
            ) : null}
          </div>
        </div>
      </div>
    </div>
  );
}
