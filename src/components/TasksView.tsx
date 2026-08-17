import { useState } from "react";
import type { VoiceTask } from "../hooks/useVoiceSession";
import { TaskItem } from "./TaskItem";
import { TasksPanel } from "./TasksPanel";
import { TaskWindowStack } from "./TaskWindowStack";
import "./TasksView.css";

export function TasksView({ tasks }: { tasks: VoiceTask[] }) {
  const [selectedTaskId, setSelectedTaskId] = useState<string>();
  const visibleTasks = tasks.filter((task) => task.kind === "worker");
  const running = visibleTasks.filter((task) => task.status === "running");
  const previewActive = visibleTasks.filter((task) => ["running", "blocked"].includes(task.status));
  const orderedTasks = visibleTasks;
  const previewTasks = previewActive.filter((task) => task.previewTarget || task.apiActivity);
  const effectiveSelectedTaskId = previewTasks.some((task) => task.id === selectedTaskId)
    ? selectedTaskId
    : previewTasks[0]?.id;

  return (
    <>
      <h1 className="tasks-view__title">Tasks</h1>
      <section className="tasks-view" data-has-previews={previewTasks.length > 0} aria-label="Sherpa tasks">
        <TasksPanel empty={!orderedTasks.length} working={running.length > 0}>
          {orderedTasks.map((task) => (
            <TaskItem
              key={task.id}
              onSelect={() => {
                if ((task.previewTarget || task.apiActivity) && ["running", "blocked"].includes(task.status)) setSelectedTaskId(task.id);
              }}
              selected={task.id === effectiveSelectedTaskId}
              task={task}
            />
          ))}
        </TasksPanel>
        <TaskWindowStack
          onSelect={setSelectedTaskId}
          selectedTaskId={effectiveSelectedTaskId}
          tasks={previewTasks}
        />
      </section>
    </>
  );
}
