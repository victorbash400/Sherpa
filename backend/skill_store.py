import re
from dataclasses import dataclass
from pathlib import Path


SKILLS_ROOT = Path(__file__).with_name("skills")
SKILL_TRIGGERS = {
    "native-whatsapp": ("whatsapp",),
    "google-workspace": (
        "gmail",
        "google calendar",
        "google contacts",
        "google doc",
        "google drive",
        "google sheet",
        "google slide",
        "workspace",
    ),
}
SKILL_DISPLAY_NAMES = {
    "native-whatsapp": "Native WhatsApp",
    "google-workspace": "Google Workspace",
}
FRONTMATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n(.*)\Z", re.DOTALL)


@dataclass(frozen=True)
class SherpaSkill:
    id: str
    name: str
    description: str
    instructions: str

    def snapshot(self) -> dict[str, str | bool]:
        return {
            "id": self.id,
            "name": SKILL_DISPLAY_NAMES.get(self.id, self.name),
            "description": self.description,
            "built_in": True,
        }


class SkillStore:
    def all(self) -> list[SherpaSkill]:
        skills: list[SherpaSkill] = []
        for skill_file in sorted(SKILLS_ROOT.glob("*/SKILL.md")):
            skill = parse_skill(skill_file)
            if skill:
                skills.append(skill)
        return skills

    def context_for(self, instruction: str) -> str:
        normalized = instruction.casefold()
        selected = [
            skill
            for skill in self.all()
            if any(trigger in normalized for trigger in SKILL_TRIGGERS.get(skill.id, ()))
        ]
        if not selected:
            return ""
        sections = [f"## {skill.name}\n{skill.instructions.strip()}" for skill in selected]
        return "Relevant Sherpa skills:\n\n" + "\n\n".join(sections)


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
