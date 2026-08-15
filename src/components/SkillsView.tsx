import type { SherpaSkill } from "../hooks/useSkills";
import "./SkillsView.css";

type SkillsViewProps = {
  error?: string;
  skills: SherpaSkill[];
};

export function SkillsView({ error, skills }: SkillsViewProps) {
  return (
    <>
      <h1 className="skills-view__title">Skills</h1>
      <section className="skills-view" aria-label="Sherpa skills">
        {error ? <p className="skills-view__error" role="alert">{error}</p> : null}
        {skills.map((skill) => (
          <article className="skill-row" key={skill.id}>
            <img alt="" aria-hidden="true" src="/scroll-svgrepo-com (2).svg" />
            <span>
              <strong>{skill.name}</strong>
              <small>{skill.description}</small>
            </span>
            {skill.built_in ? <small className="skill-row__type">Built in</small> : null}
          </article>
        ))}
      </section>
    </>
  );
}
