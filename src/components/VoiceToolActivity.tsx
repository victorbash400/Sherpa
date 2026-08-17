import type { CSSProperties } from "react";
import type { VoiceContextUsage, VoiceToolActivity as Activity } from "../hooks/useVoiceSession";
import "./VoiceToolActivity.css";

export function VoiceToolActivity({ activities, context }: {
  activities: Activity[];
  context: VoiceContextUsage;
}) {
  const activity = activities.at(-1);
  if (!activity && context.tokens === null && !context.compacting) return null;

  const ratio = context.tokens === null ? 0 : Math.min(1, context.tokens / context.limit);
  const remaining = context.tokens === null ? null : Math.max(0, context.limit - context.tokens);

  return (
    <div className="voice-tool-activity" aria-live="polite">
      <span className="voice-context-gauge" style={{ "--context-progress": ratio } as CSSProperties}>
        <svg viewBox="0 0 20 20" aria-hidden="true">
          <circle cx="10" cy="10" r="8" />
          <circle cx="10" cy="10" r="8" pathLength="1" />
        </svg>
      </span>
      <span className="voice-activity-copy">
        {context.compacting ? (
          <strong className="voice-activity-label" data-status="running">
            <img src="/compress-svgrepo-com%20(1).svg" alt="" />
            Compacting
          </strong>
        ) : activity ? (
          <strong className="voice-activity-label" data-status={activity.status}>
            {activityLabel(activity)}
          </strong>
        ) : null}
        <small>{context.tokens === null
          ? "Measuring next context"
          : `${formatTokens(context.tokens)} context · ${formatTokens(remaining)} remaining`}</small>
      </span>
    </div>
  );
}

function formatTokens(tokens: number | null) {
  if (tokens === null) return "—";
  return new Intl.NumberFormat("en").format(tokens);
}

function activityLabel(activity: Activity) {
  if (activity.status === "error" && activity.error) return activity.error;
  const value = firstText(activity.args.name, activity.args.to, activity.args.query, activity.args.app_target);
  const action = typeof activity.args.action === "string" ? activity.args.action : "";

  if (activity.name === "computer_app") {
    if (action === "launch" || action === "open") return `Opening ${value || "app"}`;
    if (action === "focus" || action === "switch") return `Focusing ${value || "app"}`;
    if (action === "quit") return `Closing ${value || "app"}`;
    if (action === "list") return "Checking apps";
  }
  if (activity.name === "computer_see" || activity.name === "computer_inspect_ui") {
    return `Checking ${value || "screen"}`;
  }
  if (activity.name === "computer_click") return `Clicking ${value || "control"}`;
  if (activity.name === "computer_type") return "Typing";
  if (activity.name === "computer_scroll") return "Scrolling";
  if (activity.name === "computer_menu") return `Using ${value || "menu"}`;
  if (activity.name === "computer_window") return `Managing ${value || "window"}`;
  if (activity.name === "computer_dialog") return "Checking dialog";
  if (activity.name === "computer_press") return "Pressing key";
  if (activity.name === "computer_drag") return "Dragging";
  if (activity.name === "computer_set_value") return `Setting ${value || "value"}`;
  if (activity.name === "computer_action") return `Using ${value || "control"}`;
  if (activity.name === "browser_snapshot" || activity.name === "browser_find") return "Reading page";
  if (activity.name === "browser_navigate") return `Opening ${firstText(activity.args.url) || "page"}`;
  if (activity.name === "browser_click") return `Clicking ${firstText(activity.args.element) || "page control"}`;
  if (activity.name === "browser_type" || activity.name === "browser_fill_form") return "Typing in page";
  if (activity.name === "browser_tabs") return "Checking browser tabs";
  if (activity.name === "browser_wait_for") return "Waiting for page";
  return activity.name.replace(/^(computer|browser)_/, "").replaceAll("_", " ");
}

function firstText(...values: unknown[]) {
  return values.find((value): value is string => typeof value === "string" && value.length > 0);
}
