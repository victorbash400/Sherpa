import { useEffect, useState } from "react";
import type { OverlayUpdate } from "../types/sherpaOverlay";
import { OverlayObservationIcon } from "./OverlayObservationIcon";
import "./AgentCursorOverlay.css";

export function AgentCursorOverlay() {
  const [action, setAction] = useState<OverlayUpdate>();

  useEffect(() => {
    const bridge = window.sherpaOverlay;
    if (!bridge) return;
    const stopUpdates = bridge.onUpdate((nextAction) => {
      setAction(nextAction);
    });
    const stopHides = bridge.onHide(() => undefined);
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
        style={{ transform: `translate3d(${action?.x ?? 0}px, 0, 0)` }}
      >
        <div
          key={action?.id || "idle"}
          className="agent-cursor"
          data-action={action?.action || "idle"}
          data-horizontal={action?.horizontal || "right"}
          data-visible={Boolean(action)}
          data-vertical={action?.vertical || "down"}
          style={{ transform: `translate3d(0, ${action?.y ?? 0}px, 0)` }}
        >
          <span className="agent-cursor__icon" aria-hidden="true" />
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
