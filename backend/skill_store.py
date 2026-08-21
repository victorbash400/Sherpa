import json
import re
from dataclasses import dataclass, replace
from pathlib import Path
from backend.account_context import account_context


SKILLS_ROOT = Path(__file__).with_name("skills")
FRONTMATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n(.*)\Z", re.DOTALL)


@dataclass(frozen=True)
class SherpaSkill:
    id: str
    name: str
    description: str
    instructions: str

    def catalog_entry(self) -> dict[str, str]:
        return {"id": self.id, "name": self.name, "description": self.description}

    def snapshot(self) -> dict[str, str | bool]:
        return {
            **self.catalog_entry(),
            "instructions": self.instructions.strip(),
            "built_in": True,
        }


class SkillStore:
    def __init__(self, overrides_path: Path | None = None) -> None:
        self._overrides_path = overrides_path

    def _path(self) -> Path:
        if self._overrides_path:
            return self._overrides_path
        return account_context.profile_directory() / "skills.json"

    def all(self) -> list[SherpaSkill]:
        overrides = self._load_overrides()
        skills: list[SherpaSkill] = []
        for skill_file in sorted(SKILLS_ROOT.glob("*/SKILL.md")):
            skill = parse_skill(skill_file)
            if skill:
                skills.append(replace(skill, instructions=overrides.get(skill.id, skill.instructions)))
        return skills

    def catalog(self) -> list[dict[str, str]]:
        return [skill.catalog_entry() for skill in self.all()]

    def context_for(self, skill_ids: list[str]) -> str:
        available = {skill.id: skill for skill in self.all()}
        selected = [available[skill_id] for skill_id in skill_ids if skill_id in available]
        if not selected:
            return ""
        sections = [f"## Skill: {skill.name}\n{skill.instructions.strip()}" for skill in selected]
        return "Selected task skills:\n\n" + "\n\n".join(sections)

    def update(self, skill_id: str, instructions: str) -> SherpaSkill:
        clean = instructions.strip()
        if not clean:
            raise ValueError("Skill instructions cannot be empty.")
        if len(clean) > 30_000:
            raise ValueError("Skill instructions are too long.")
        existing = next((skill for skill in self.all() if skill.id == skill_id), None)
        if not existing:
            raise KeyError(skill_id)
        overrides = self._load_overrides()
        overrides[skill_id] = clean
        path = self._path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(overrides, indent=2) + "\n")
        return replace(existing, instructions=clean)

    def _load_overrides(self) -> dict[str, str]:
        try:
            value = json.loads(self._path().read_text())
        except (OSError, json.JSONDecodeError):
            return {}
        if not isinstance(value, dict):
            return {}
        return {
            key: content
            for key, content in value.items()
            if isinstance(key, str) and isinstance(content, str)
        }


def parse_skill(path: Path) -> SherpaSkill | None:
    try:
        content = path.read_text()
    except OSError:
        return None
    match = FRONTMATTER.match(content)
    if not match:
        return None
    metadata: dict[str, str] = {}
    for line in match.group(1).splitlines():
        key, separator, value = line.partition(":")
        if separator:
            metadata[key.strip()] = value.strip()
    name = metadata.get("name")
    description = metadata.get("description")
    if not name or not description:
        return None
    return SherpaSkill(
        id=path.parent.name,
        name=name,
        description=description,
        instructions=match.group(2),
    )


skill_store = SkillStore()
