import type { VoiceTask } from "../hooks/useVoiceSession";
import { TaskItem } from "./TaskItem";
import "./TasksView.css";

export function TasksView({ tasks }: { tasks: VoiceTask[] }) {
  const running = tasks.filter((task) => task.status === "running");
  const recent = tasks.filter((task) => task.status !== "running");

  return (
    <section className="tasks-view" aria-label="Sherpa tasks">
      <header>
        <h1>Tasks</h1>
        <span>{running.length} running</span>
      </header>
      {!tasks.length ? (
        <p className="tasks-view__empty">Tasks you give Sherpa will appear here.</p>
      ) : (
        <>
          {running.length ? <div className="tasks-view__list">{running.map((task) => <TaskItem key={task.id} task={task} />)}</div> : null}
          {recent.length ? <h2>Recent</h2> : null}
          {recent.length ? <div className="tasks-view__list">{recent.map((task) => <TaskItem key={task.id} task={task} />)}</div> : null}
        </>
      )}
    </section>
  );
}
