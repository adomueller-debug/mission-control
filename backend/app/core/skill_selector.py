from backend.app.core.skill_registry import skill_registry


class SkillSelector:
    def select(self, name: str):
        return skill_registry.get(name)


skill_selector = SkillSelector()
