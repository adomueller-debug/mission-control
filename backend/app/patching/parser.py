import re

from backend.app.patching.models import Patch


class PatchParser:

    def parse(self, text: str) -> Patch:
        match = re.search(r"\+\+\+\s+b/(.+)", text)

        if not match:
            raise ValueError("No target file found in patch.")

        return Patch(
            path=match.group(1),
            diff=text,
        )


parser = PatchParser()
