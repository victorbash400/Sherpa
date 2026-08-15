import type { VoiceTask } from "../hooks/useVoiceSession";
import { TasksEmptyState } from "./TasksEmptyState";
import { TaskItem } from "./TaskItem";
import "./TasksView.css";

export function TasksView({ tasks }: { tasks: VoiceTask[] }) {
  const visibleTasks = tasks.filter((task) => task.kind === "worker");
  const running = visibleTasks.filter((task) => task.status === "running");
  const finished = visibleTasks.filter((task) => task.status !== "running");
  const orderedTasks = [...running, ...finished];

  return (
    <>
      <h1 className="tasks-view__title">Tasks</h1>
      <section className="tasks-view" aria-label="Sherpa tasks">
        {orderedTasks.length ? (
          <div className="tasks-view__sheet">
          <div className="tasks-view__list">
            {orderedTasks.map((task) => (
              <TaskItem key={task.id} task={task} />
            ))}
          </div>
          </div>
        ) : <TasksEmptyState />}
      </section>
    </>
  );
}
