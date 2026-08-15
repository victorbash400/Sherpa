import { useEffect, useRef, useState, type PointerEvent as ReactPointerEvent } from "react";
import type { VoiceTask } from "../hooks/useVoiceSession";
import { TaskWindowCard } from "./TaskWindowCard";
import { TaskWindowThumbnail } from "./TaskWindowThumbnail";
import "./TaskWindowStack.css";

type Position = { x: number; y: number };

type TaskWindowStackProps = {
  onSelect: (taskId: string) => void;
  selectedTaskId?: string;
  tasks: VoiceTask[];
};

export function TaskWindowStack({ onSelect, selectedTaskId, tasks }: TaskWindowStackProps) {
  const [expanded, setExpanded] = useState(false);
  const [position, setPosition] = useState<Position>({ x: 0, y: 0 });
  const stackRef = useRef<HTMLDivElement>(null);
  const dragRef = useRef<{ origin: Position; pointer: Position } | undefined>(undefined);

  useEffect(() => {
    if (!expanded) return;
    const close = (event: KeyboardEvent) => {
      if (event.key === "Escape") setExpanded(false);
    };
    window.addEventListener("keydown", close);
    return () => window.removeEventListener("keydown", close);
  }, [expanded]);

  if (!tasks.length) return null;

  const selectedTask = tasks.find((task) => task.id === selectedTaskId) || tasks[0];
  const thumbnails = tasks.filter((task) => task.id !== selectedTask.id);

  const handlePointerDown = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (expanded || (event.target as HTMLElement).closest("button")) return;
    dragRef.current = { origin: position, pointer: { x: event.clientX, y: event.clientY } };
    event.currentTarget.setPointerCapture(event.pointerId);
  };

  const handlePointerMove = (event: ReactPointerEvent<HTMLDivElement>) => {
    const drag = dragRef.current;
    const stack = stackRef.current;
    const parent = stack?.parentElement;
    if (!drag || !stack || !parent) return;
    const parentBounds = parent.getBoundingClientRect();
    const stackBounds = stack.getBoundingClientRect();
    const nextX = drag.origin.x + event.clientX - drag.pointer.x;
    const nextY = drag.origin.y + event.clientY - drag.pointer.y;
    setPosition({
      x: Math.max(-parentBounds.width + stackBounds.width, Math.min(0, nextX)),
      y: Math.max(-84, Math.min(parentBounds.height - stackBounds.height - 24, nextY)),
    });
  };

  const stopDragging = () => { dragRef.current = undefined; };

  return (
    <div
      ref={stackRef}
      className="task-window-stack"
      data-expanded={expanded}
      data-has-rail={thumbnails.length > 0}
      onPointerCancel={stopDragging}
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={stopDragging}
      style={expanded ? undefined : { transform: `translate(${position.x}px, ${position.y}px)` }}
    >
      <div className="task-window-stack__active">
        <TaskWindowCard
          active
          expanded={expanded}
          onExpand={() => setExpanded((current) => !current)}
          task={selectedTask}
        />
      </div>
      {thumbnails.length ? (
        <div className="task-window-stack__rail" aria-label="Other task windows">
          {thumbnails.map((task, index) => (
            <TaskWindowThumbnail
              index={index}
              key={task.id}
              onSelect={() => onSelect(task.id)}
              task={task}
            />
          ))}
        </div>
      ) : null}
    </div>
  );
}
