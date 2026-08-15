import { useEffect, useState } from "react";
import type { MemorySettingsValues } from "./memoryTypes";
import "./MemoryPersonalization.css";

interface Props {
  limits: Record<"custom_instructions" | "chat_style" | "response_style", number>;
  saving: boolean;
  settings: MemorySettingsValues;
  onSave: (values: Partial<MemorySettingsValues>) => Promise<void>;
}

export function MemoryPersonalization({ limits, saving, settings, onSave }: Props) {
  const [draft, setDraft] = useState(settings);
  useEffect(() => setDraft(settings), [settings]);
  const changed = draft.custom_instructions !== settings.custom_instructions
    || draft.chat_style !== settings.chat_style
    || draft.response_style !== settings.response_style;

  return (
    <section className="memory-personalization">
      <header>
        <span><h2>Personalization</h2><p>Choose how Sherpa speaks and works with you.</p></span>
        <button type="button" disabled={!changed || saving} onClick={() => void onSave({
          custom_instructions: draft.custom_instructions,
          chat_style: draft.chat_style,
          response_style: draft.response_style,
        })}>{saving ? "Saving" : "Save"}</button>
      </header>
      <div className="memory-personalization__fields">
        <MemoryField label="Custom instructions" description="Important context Sherpa should use across conversations and tasks." limit={limits.custom_instructions} value={draft.custom_instructions} onChange={(custom_instructions) => setDraft((current) => ({ ...current, custom_instructions }))} />
        <MemoryField label="Conversation style" description="How you want voice conversations to feel." limit={limits.chat_style} value={draft.chat_style} onChange={(chat_style) => setDraft((current) => ({ ...current, chat_style }))} />
        <MemoryField label="Response style" description="How Sherpa should structure and phrase its answers." limit={limits.response_style} value={draft.response_style} onChange={(response_style) => setDraft((current) => ({ ...current, response_style }))} />
      </div>
    </section>
  );
}

function MemoryField({ description, label, limit, onChange, value }: { description: string; label: string; limit: number; onChange: (value: string) => void; value: string }) {
  return (
    <label className="memory-field">
      <span><strong>{label}</strong><small>{description}</small></span>
      <textarea maxLength={limit} value={value} onChange={(event) => onChange(event.target.value)} />
      <em>{value.length}/{limit}</em>
    </label>
  );
}
