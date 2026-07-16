import subprocess
import tempfile
from pathlib import Path


class PatchApplier:

    def apply(self, diff: str):
        with tempfile.NamedTemporaryFile(
            suffix=".patch",
            delete=False,
            mode="w",
            encoding="utf-8",
        ) as patch:
            patch.write(diff)
            patch_path = patch.name

        subprocess.run(
            ["git", "apply", patch_path],
            check=True,
        )

        Path(patch_path).unlink(missing_ok=True)


applier = PatchApplier()
