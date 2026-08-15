import { useEffect, useRef, useState, type PointerEvent as ReactPointerEvent } from "react";
import type { VoiceTask } from "../hooks/useVoiceSession";
import { TaskWindowCard } from "./TaskWindowCard";
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

  const selectedIndex = Math.max(0, tasks.findIndex((task) => task.id === selectedTaskId));
  const ordered = [...tasks.slice(0, selectedIndex), ...tasks.slice(selectedIndex + 1), tasks[selectedIndex]];

  const handlePointerDown = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (expanded || (event.target as HTMLElement).closest(".task-window-card__expand")) return;
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

  return (
    <div
      ref={stackRef}
      className="task-window-stack"
      data-expanded={expanded}
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={() => { dragRef.current = undefined; }}
      style={expanded ? undefined : { transform: `translate(${position.x}px, ${position.y}px)` }}
    >
      {ordered.map((task, index) => {
        const active = index === ordered.length - 1;
        const depth = ordered.length - index - 1;
        return (
          <div
            className="task-window-stack__layer"
            key={task.id}
            style={{ transform: expanded || active ? undefined : `translate(${-depth * 11}px, ${depth * 9}px) scale(${1 - depth * .025})` }}
          >
            <TaskWindowCard
              active={active}
              expanded={expanded && active}
              onExpand={() => setExpanded((current) => !current)}
              onSelect={() => onSelect(task.id)}
              task={task}
            />
          </div>
        );
      })}
    </div>
  );
}
