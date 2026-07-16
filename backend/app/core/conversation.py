from dataclasses import dataclass, field


@dataclass
class Conversation:
    id: str

    messages: list = field(default_factory=list)

    def add(self, role: str, content: str):
        self.messages.append(
            {
                "role": role,
                "content": content,
            }
        )
