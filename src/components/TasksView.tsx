import type { VoiceTask } from "../hooks/useVoiceSession";
import { TaskItem } from "./TaskItem";
import { TasksPanel } from "./TasksPanel";
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
        <TasksPanel empty={!orderedTasks.length} working={running.length > 0}>
          {orderedTasks.map((task) => <TaskItem key={task.id} task={task} />)}
        </TasksPanel>
      </section>
    </>
  );
}
