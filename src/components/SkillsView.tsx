import type { SherpaSkill } from "../hooks/useSkills";
import { SkillRow } from "./SkillRow";
import "./SkillsView.css";

type SkillsViewProps = {
  error?: string;
  skills: SherpaSkill[];
  onSave: (id: string, instructions: string) => Promise<void>;
};

export function SkillsView({ error, skills, onSave }: SkillsViewProps) {
  return (
    <>
      <h1 className="skills-view__title">Skills</h1>
      <section className="skills-view" aria-label="Sherpa skills">
        {error ? <p className="skills-view__error" role="alert">{error}</p> : null}
        <div className="skills-view__rows">
          {skills.map((skill) => <SkillRow key={skill.id} skill={skill} onSave={onSave} />)}
        </div>
      </section>
    </>
  );
}
