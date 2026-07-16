from uuid import uuid4

from sqlalchemy import String, Text

from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database.database import Base


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    agent_id: Mapped[str] = mapped_column(String)

    instruction: Mapped[str] = mapped_column(Text)

    status: Mapped[str] = mapped_column(
        String,
        default="queued",
    )

    result: Mapped[str] = mapped_column(
        Text,
        default="",
    )
