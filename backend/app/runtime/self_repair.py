from backend.app.providers.factory import provider
from backend.app.services.coding_service import coding_service


class SelfRepairLoop:

    def repair(self, path: str, error: str, attempts: int = 3):

        history = []

        for attempt in range(1, attempts + 1):

            result = coding_service.improve_file(path)

            history.append(
                {
                    "attempt": attempt,
                    "success": result.success,
                    "message": result.message,
                }
            )

            if result.success:
                return history

            prompt = f"""
The previous patch failed.

Error:

{result.message}

Original build error:

{error}

Generate a better patch.
"""

            provider.generate(
                prompt=prompt,
                system_prompt="You are fixing build failures."
            )

        return history


repair_loop = SelfRepairLoop()
