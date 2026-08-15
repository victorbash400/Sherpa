import type { MemorySettingsValues } from "./memoryTypes";
import "./MemorySettings.css";

export function MemorySettings({ settings, onChange, onDelete }: { settings: MemorySettingsValues; onChange: (values: Partial<MemorySettingsValues>) => Promise<void>; onDelete: () => Promise<void> }) {
  return (
    <section className="memory-settings">
      <h2>Memory</h2>
      <p>Control what Sherpa retains and uses on this Mac.</p>
      <div className="memory-settings__rows">
        <SettingRow checked={settings.enabled} description="Create local memories and use them in future conversations." label="Enable local memory" onChange={(enabled) => void onChange({ enabled })} />
        <SettingRow checked={settings.learn_from_tools} description="Allow verified task outcomes to improve future work." label="Learn from tool-assisted tasks" onChange={(learn_from_tools) => void onChange({ learn_from_tools })} />
        <div className="memory-setting-row">
          <span><strong>Delete local memories</strong><small>Remove learned memories while keeping personalization settings.</small></span>
          <button type="button" className="memory-settings__delete" onClick={() => void onDelete()}>Delete</button>
        </div>
      </div>
    </section>
  );
}

function SettingRow({ checked, description, label, onChange }: { checked: boolean; description: string; label: string; onChange: (checked: boolean) => void }) {
  return (
    <label className="memory-setting-row">
      <span><strong>{label}</strong><small>{description}</small></span>
      <span className="memory-toggle"><input type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)} /><i aria-hidden="true" /></span>
    </label>
  );
}
