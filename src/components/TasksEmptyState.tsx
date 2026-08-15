import "./TasksEmptyState.css";

export function TasksEmptyState() {
  return (
    <div className="tasks-empty" aria-label="No tasks">
      <header className="tasks-empty__header">
        <strong>Active tasks</strong>
      </header>
      <div className="tasks-empty__sheet">
        <span>Active tasks will appear here</span>
      </div>
    </div>
  );
}
