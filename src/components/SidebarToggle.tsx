import { PanelLeft } from "lucide-react";
import "./SidebarToggle.css";

interface SidebarToggleProps {
  open: boolean;
  onToggle: () => void;
}

export function SidebarToggle({ open, onToggle }: SidebarToggleProps) {
  return (
    <button
      className="sidebar-toggle"
      type="button"
      aria-label={open ? "Close sidebar" : "Open sidebar"}
      aria-expanded={open}
      onClick={onToggle}
    >
      <PanelLeft aria-hidden="true" />
    </button>
  );
}
