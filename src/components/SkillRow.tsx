import { useState } from "react";
import { Check, ChevronDown } from "lucide-react";
import type { SherpaSkill } from "../hooks/useSkills";
import { SkillIcon } from "./SkillIcon";

type SkillRowProps = {
  skill: SherpaSkill;
  onSave: (id: string, instructions: string) => Promise<void>;
};

function skillTitle(id: string) {
  return id.split("-").map((part) => part[0].toUpperCase() + part.slice(1)).join(" ");
}

export function SkillRow({ skill, onSave }: SkillRowProps) {
  const [expanded, setExpanded] = useState(false);
  const [draft, setDraft] = useState(skill.instructions);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string>();

  async function save() {
    setSaving(true);
    setError(undefined);
    try {
      await onSave(skill.id, draft);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not save this skill.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <article className="skill-row" data-expanded={expanded}>
      <button
        className="skill-row__summary"
        type="button"
        aria-expanded={expanded}
        onClick={() => setExpanded((value) => !value)}
      >
        <SkillIcon id={skill.id} />
        <span>
          <strong>{skillTitle(skill.id)}</strong>
          <small>{skill.description}</small>
        </span>
        <ChevronDown className="skill-row__chevron" aria-hidden="true" />
      </button>
      {expanded ? (
        <div className="skill-row__editor">
          <label htmlFor={`skill-${skill.id}`}>Instructions</label>
          <textarea
            id={`skill-${skill.id}`}
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            spellCheck="true"
          />
          <div className="skill-row__actions">
            {error ? <small role="alert">{error}</small> : null}
            <button
              disabled={saving || draft.trim() === skill.instructions.trim()}
              onClick={() => void save()}
              type="button"
            >
              <Check aria-hidden="true" />
              {saving ? "Saving" : "Save"}
            </button>
          </div>
        </div>
      ) : null}
    </article>
  );
}
