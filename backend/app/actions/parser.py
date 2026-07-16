from backend.app.actions.models import Action


class ActionParser:

    def parse(self, payload: dict) -> list[Action]:
        return [
            Action(
                agent=item["agent"],
                tool=item["tool"],
                operation=item["operation"],
                arguments=item["arguments"],
            )
            for item in payload.get("actions", [])
        ]


parser = ActionParser()
