import { ChevronLeft, ChevronRight } from "lucide-react";
import type { PointerEventHandler } from "react";
import "./TaskWindowSwitcher.css";

type TaskWindowSwitcherProps = {
  current: number;
  label: string;
  onNext: () => void;
  onPointerCancel: PointerEventHandler<HTMLDivElement>;
  onPointerDown: PointerEventHandler<HTMLDivElement>;
  onPointerMove: PointerEventHandler<HTMLDivElement>;
  onPointerUp: PointerEventHandler<HTMLDivElement>;
  onPrevious: () => void;
  total: number;
};

export function TaskWindowSwitcher({
  current,
  label,
  onNext,
  onPointerCancel,
  onPointerDown,
  onPointerMove,
  onPointerUp,
  onPrevious,
  total,
}: TaskWindowSwitcherProps) {
  return (
    <div
      className="task-window-switcher"
      onPointerCancel={onPointerCancel}
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
    >
      <button type="button" aria-label="Show previous task window" onClick={onPrevious} disabled={total < 2}>
        <ChevronLeft aria-hidden="true" />
      </button>
      <div className="task-window-switcher__label" title={label} aria-live="polite">
        <strong>{label}</strong>
        <span>{current + 1} of {total}</span>
      </div>
      <button type="button" aria-label="Show next task window" onClick={onNext} disabled={total < 2}>
        <ChevronRight aria-hidden="true" />
      </button>
    </div>
  );
}
