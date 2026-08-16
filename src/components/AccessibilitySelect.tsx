interface AccessibilitySelectProps {
  disabled?: boolean;
  label: string;
  onChange: (value: string) => void;
  options: readonly { id: string; label: string }[];
  value: string;
}

export function AccessibilitySelect({ disabled, label, onChange, options, value }: AccessibilitySelectProps) {
  return (
    <label className="accessibility-select">
      <span>{label}</span>
      <select disabled={disabled} onChange={(event) => onChange(event.target.value)} value={value}>
        {options.map((option) => <option key={option.id} value={option.id}>{option.label}</option>)}
      </select>
    </label>
  );
}
