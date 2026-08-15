import type { ReactNode } from "react";
import "./TasksPanel.css";

interface TasksPanelProps {
  children: ReactNode;
  empty: boolean;
  working: boolean;
}

export function TasksPanel({ children, empty, working }: TasksPanelProps) {
  return (
    <section className="tasks-panel" aria-label="Active tasks">
      <header className="tasks-panel__header">
        <span>Active tasks</span>
        {working ? <strong>Working</strong> : null}
      </header>
      <div className="tasks-panel__sheet">
        {empty ? <span className="tasks-panel__empty">Active tasks will appear here</span> : (
          <div className="tasks-panel__list">{children}</div>
        )}
      </div>
    </section>
  );
}
