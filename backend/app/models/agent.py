from uuid import uuid4

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database.database import Base


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    name: Mapped[str] = mapped_column(String)

    description: Mapped[str] = mapped_column(String)

    type: Mapped[str] = mapped_column(String, default="general")

    status: Mapped[str] = mapped_column(String, default="idle")
