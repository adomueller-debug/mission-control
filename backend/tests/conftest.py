from __future__ import annotations

import os
import tempfile
from pathlib import Path


TEST_DATABASE = Path(tempfile.gettempdir()) / f"mission_control_test_{os.getpid()}.db"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DATABASE}"
os.environ["MISSION_CONTROL_TESTING"] = "1"
