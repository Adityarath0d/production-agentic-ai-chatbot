from datetime import datetime, timezone

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base

def utcnow() -> datetime:
    return datetime.now(timezone.utc)

DEFAULT_TITLE = "New chat"

class Thread(Base):
    __tablename__ = "threads"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String, default=DEFAULT_TITLE)
    user_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default = utcnow, onupdate=utcnow)
    archived: Mapped[bool] = mapped_column(default=False, server_default="0")