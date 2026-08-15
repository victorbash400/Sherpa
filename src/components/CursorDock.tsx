import "./CursorDock.css";

interface CursorDockProps {
  active: boolean;
}

export function CursorDock({ active }: CursorDockProps) {
  return (
    <span className="cursor-dock" data-active={active} aria-label="Sherpa computer control" title="Computer control">
      <img alt="" aria-hidden="true" src="/cursor-alt-svgrepo-com.svg?v=2" />
    </span>
  );
}
