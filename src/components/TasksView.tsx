import type { VoiceTask } from "../hooks/useVoiceSession";
import { TaskItem } from "./TaskItem";
import "./TasksView.css";

export function TasksView({ tasks }: { tasks: VoiceTask[] }) {
  const visibleTasks = tasks.filter((task) => task.kind === "worker");
  const running = visibleTasks.filter((task) => task.status === "running");
  const finished = visibleTasks.filter((task) => task.status !== "running");
  const orderedTasks = [...running, ...finished];

  return (
    <section className="tasks-view" aria-label="Sherpa tasks">
      <div className="tasks-view__sheet">
        <h1>Tasks</h1>
        {orderedTasks.length ? (
          <div className="tasks-view__list">
            {orderedTasks.map((task) => (
              <TaskItem key={task.id} task={task} />
            ))}
          </div>
        ) : null}
      </div>
    </section>
  );
}
