from backend.app.core.skill import Skill


class SkillRegistry:
    def __init__(self):
        self.skills = {}

    def register(self, skill: Skill):
        self.skills[skill.name] = skill

    def get(self, name: str):
        return self.skills[name]

    def all(self):
        return list(self.skills.values())


skill_registry = SkillRegistry()
