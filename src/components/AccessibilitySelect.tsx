interface AccessibilitySelectProps {
  disabled?: boolean;
  label: string;
  onChange: (value: string) => void;
  options: readonly { id: string; label: string }[];
  value: string;
}

export function AccessibilitySelect({ disabled, label, onChange, options, value }: AccessibilitySelectProps) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const selected = options.find((option) => option.id === value) ?? options[0];

  useEffect(() => {
    if (!open) return;
    const closeOutside = (event: PointerEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    };
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    document.addEventListener("pointerdown", closeOutside);
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("pointerdown", closeOutside);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, [open]);

  return (
    <div className="accessibility-select" ref={rootRef}>
      <button aria-expanded={open} aria-haspopup="listbox" disabled={disabled} onClick={() => setOpen((current) => !current)} type="button">
        <span>{selected.label}</span>
        <ChevronDown aria-hidden="true" />
      </button>
      {open ? (
        <div aria-label={label} className="accessibility-select__menu" role="listbox">
          {options.map((option) => (
            <button
              aria-selected={option.id === value}
              key={option.id}
              onClick={() => {
                onChange(option.id);
                setOpen(false);
              }}
              role="option"
              type="button"
            >
              <span>{option.label}</span>
              {option.id === value ? <Check aria-hidden="true" /> : null}
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}
import { useEffect, useRef, useState } from "react";
import { Check, ChevronDown } from "lucide-react";
