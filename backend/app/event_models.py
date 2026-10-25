from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ProcessedEvent(Base):
    __tablename__ = "processed_events"

    # Unique event ID prevents the same event from being recorded twice.
    event_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
    )
    event_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="processed",
    )
    payload_json: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
