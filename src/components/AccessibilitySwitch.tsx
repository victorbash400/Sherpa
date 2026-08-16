interface AccessibilitySwitchProps {
  checked: boolean;
  label: string;
  onChange: (checked: boolean) => void;
}

export function AccessibilitySwitch({ checked, label, onChange }: AccessibilitySwitchProps) {
  return (
    <label className="accessibility-switch">
      <input
        aria-label={label}
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
        type="checkbox"
      />
      <span />
    </label>
  );
}
