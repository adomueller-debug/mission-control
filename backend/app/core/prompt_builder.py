class PromptBuilder:
    def build(self, role: str, instruction: str, context: str = ""):
        return f"""
Role:
{role}

Context:
{context}

Task:
{instruction}
"""
