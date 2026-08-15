import {
  AppWindow,
  CalendarDays,
  Cloud,
  FileText,
  Globe,
  Mail,
  MessageCircle,
  Presentation,
  Sheet,
} from "lucide-react";

const icons = {
  "chrome-web-workflows": Globe,
  "google-cloud-operations": Cloud,
  "native-macos-apps": AppWindow,
  "native-whatsapp": MessageCircle,
  "workspace-documents": FileText,
  "workspace-email": Mail,
  "workspace-presentations": Presentation,
  "workspace-scheduling": CalendarDays,
  "workspace-spreadsheets": Sheet,
};

export function SkillIcon({ id }: { id: string }) {
  const Icon = icons[id as keyof typeof icons] || FileText;
  return <Icon aria-hidden="true" />;
}
