import type { VoiceToolActivity as Activity } from "../hooks/useVoiceSession";
import "./VoiceToolActivity.css";

export function VoiceToolActivity({ activities }: { activities: Activity[] }) {
  if (!activities.length) return null;

  return (
    <div className="voice-tool-activity" aria-live="polite">
      {activities.map((activity) => (
        <span data-status={activity.status} key={activity.id}>
          {activityLabel(activity)}
        </span>
      ))}
    </div>
  );
}

function activityLabel(activity: Activity) {
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
