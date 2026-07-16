class ToolSelector:
    def select(self, step: str):
        text = step.lower()

        if "file" in text:
            return "read_file"

        if "python" in text or "code" in text:
            return "python"

        if "git" in text:
            return "git"

        if "web" in text or "http" in text:
            return "web"

        return "shell"


tool_selector = ToolSelector()
