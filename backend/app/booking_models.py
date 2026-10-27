
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Cinema(Base):
    __tablename__ = "cinemas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    address: Mapped[str] = mapped_column(String(300), nullable=False)


class Screen(Base):
    __tablename__ = "screens"
    __table_args__ = (
        UniqueConstraint("cinema_id", "name", name="uq_screen_cinema_name"),
        CheckConstraint(
            "total_seats > 0",
            name="ck_screen_total_seats_positive",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cinema_id: Mapped[int] = mapped_column(
        ForeignKey("cinemas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    total_seats: Mapped[int] = mapped_column(Integer, nullable=False, default=40)


class Showtime(Base):
    __tablename__ = "showtimes"
    __table_args__ = (
        CheckConstraint(
            "ticket_price_paise > 0",
            name="ck_showtime_price_positive",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    movie_id: Mapped[int] = mapped_column(
        ForeignKey("movies.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    screen_id: Mapped[int] = mapped_column(
        ForeignKey("screens.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    starts_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    ticket_price_paise: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class Booking(Base):
    __tablename__ = "bookings"
    __table_args__ = (
        Index(
            "uq_booking_showtime_seat_active",
            "showtime_id",
            "seat_number",
            unique=True,
            postgresql_where=text("status IN ('pending_payment', 'confirmed')"),
        ),
        CheckConstraint("seat_number > 0", name="ck_booking_seat_positive"),
        CheckConstraint(
            "status IN ('pending_payment', 'confirmed', 'cancelled')",
            name="ck_booking_status_valid",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    showtime_id: Mapped[int] = mapped_column(
        ForeignKey("showtimes.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    seat_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending_payment",
        server_default="pending_payment",
    )
    booked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint("amount_paise > 0", name="ck_payment_amount_positive"),
        CheckConstraint(
            "status IN ('pending', 'succeeded', 'failed')",
            name="ck_payment_status_valid",
        ),
        CheckConstraint(
            "provider = 'sandbox'",
            name="ck_payment_provider_valid",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    booking_id: Mapped[int] = mapped_column(
        ForeignKey("bookings.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    amount_paise: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="INR",
        server_default="INR",
    )
    provider: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="sandbox",
        server_default="sandbox",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        server_default="pending",
    )
    reference: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
    )
    idempotency_key: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    booking_id: Mapped[int] = mapped_column(
        ForeignKey("bookings.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
        index=True,
    )
    token: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
