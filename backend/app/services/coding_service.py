from dataclasses import dataclass

from backend.app.patching.applier import applier
from backend.app.providers.factory import provider
from backend.app.tools.coding import coding
from backend.app.tools.filesystem import filesystem
from backend.app.memory.repository_memory import repository_memory


@dataclass
class CodingResult:
    success: bool
    file: str
    message: str


class CodingService:

    def improve_file(self, path: str) -> CodingResult:
        repository_memory.visit(path)

        source = filesystem.read(path)

        prompt = f"""
You are a senior Python software engineer.

Return ONLY a unified git patch.

Rules:

- Use unified diff format.
- Preserve behaviour.
- Improve readability.
- Never explain anything.

Target file:

{path}

Current content:

{source}
"""

        diff = provider.generate(
            prompt=prompt,
            system_prompt="You generate git patches."
        )

        try:
            applier.apply(diff)
        except Exception as e:
            return CodingResult(
                False,
                path,
                f"Patch failed: {e}",
            )

        checks = coding.run_checks()

        errors = []

        for tool, output in checks.items():
            if output.strip():
                errors.append(f"{tool}\n{output}")

        if errors:
            from backend.app.runtime.self_repair import repair_loop

            history = repair_loop.repair(
                path,
                "\n\n".join(errors),
            )

            return CodingResult(
                history[-1]["success"],
                path,
                str(history),
            )

        repository_memory.modified(path)

        return CodingResult(
            True,
            path,
            "Patch applied successfully.",
        )


coding_service = CodingService()
