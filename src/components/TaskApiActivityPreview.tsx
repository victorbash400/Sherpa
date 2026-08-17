import { Brain, CalendarDays, Cloud, FileQuestion, FileSpreadsheet, FileText, ListChecks, Mail, Video } from "lucide-react";
import type { TaskApiActivity } from "../hooks/useVoiceSession";
import "./TaskApiActivityPreview.css";

function activityDetails(tool: string) {
  const normalized = tool.toLowerCase();
  if (normalized.includes("sheet") || normalized.includes("excel")) {
    return { Icon: FileSpreadsheet, service: normalized.includes("excel") ? "Excel" : "Google Sheets" };
  }
  if (normalized.includes("doc") || normalized.includes("drive")) {
    return { Icon: FileText, service: normalized.includes("doc") ? "Google Docs" : "Google Drive" };
  }
  if (normalized.includes("gmail") || normalized.includes("mail")) {
    return { Icon: Mail, service: "Gmail" };
  }
  if (normalized.includes("calendar")) return { Icon: CalendarDays, service: "Google Calendar" };
  if (normalized.includes("tasks")) return { Icon: ListChecks, service: "Google Tasks" };
  if (normalized.includes("forms")) return { Icon: FileQuestion, service: "Google Forms" };
  if (normalized.includes("meet")) return { Icon: Video, service: "Google Meet" };
  if (normalized.includes("memory")) return { Icon: Brain, service: "Sherpa Memory" };
  return { Icon: Cloud, service: "Connected service" };
}

export function TaskApiActivityPreview({ activity }: { activity: TaskApiActivity }) {
  const { Icon, service } = activityDetails(activity.tool);

  return (
    <section className="task-api-activity" aria-label={`${service}: ${activity.message}`} aria-live="polite">
      <div className="task-api-activity__mark">
        <Icon aria-hidden="true" />
      </div>
      <div className="task-api-activity__copy">
        <span>{service}</span>
        <strong>{activity.message}</strong>
      </div>
      <div className="task-api-activity__shimmer" aria-hidden="true" />
    </section>
  );
}
