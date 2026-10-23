from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth_routes import get_current_user
from app.booking_models import Booking, Screen, Showtime
from app.booking_schemas import (
    BookingCreate,
    BookingResponse,
    SeatAvailabilityResponse,
    SeatResponse,
)
from app.database import get_db
from app.event_publisher import publish_event
from app.user_models import User

router = APIRouter(tags=["Seat Booking"])

PAYMENT_TIMEOUT_MINUTES = 10


def expire_pending_bookings(db: Session, showtime_id: int | None = None) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(
        minutes=PAYMENT_TIMEOUT_MINUTES
    )
    statement = select(Booking).where(
        Booking.status == "pending_payment",
        Booking.booked_at <= cutoff,
    )
    if showtime_id is not None:
        statement = statement.where(Booking.showtime_id == showtime_id)

    expired = list(db.scalars(statement.with_for_update()).all())
    for booking in expired:
        booking.status = "cancelled"

    if expired:
        db.commit()

    return len(expired)


def require_customer(current_user: User) -> None:
    if current_user.role != "customer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only customer accounts can book tickets",
        )


def get_future_showtime(db: Session, showtime_id: int) -> Showtime:
    showtime = db.get(Showtime, showtime_id)

    if showtime is None:
        raise HTTPException(status_code=404, detail="Showtime not found")

    if showtime.starts_at <= datetime.now(timezone.utc):
        raise HTTPException(
            status_code=400,
            detail="This showtime has already started",
        )

    return showtime


@router.get(
    "/api/showtimes/{showtime_id}/seats",
    response_model=SeatAvailabilityResponse,
)
def get_seat_availability(
    showtime_id: int,
    db: Session = Depends(get_db),
):
    showtime = db.get(Showtime, showtime_id)

    if showtime is None:
        raise HTTPException(status_code=404, detail="Showtime not found")

    expire_pending_bookings(db, showtime_id)

    screen = db.get(Screen, showtime.screen_id)
    if screen is None:
        raise HTTPException(status_code=500, detail="Screen configuration missing")

    unavailable_numbers = set(
        db.scalars(
            select(Booking.seat_number).where(
                Booking.showtime_id == showtime_id,
                Booking.status.in_(["pending_payment", "confirmed"]),
            )
        ).all()
    )

    seats = [
        SeatResponse(
            seat_number=number,
            status="booked" if number in unavailable_numbers else "available",
        )
        for number in range(1, screen.total_seats + 1)
    ]

    return SeatAvailabilityResponse(
        showtime_id=showtime_id,
        total_seats=screen.total_seats,
        available_seats=screen.total_seats - len(unavailable_numbers),
        booked_seats=len(unavailable_numbers),
        seats=seats,
    )


@router.post(
    "/api/bookings",
    response_model=BookingResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_booking(
    request: BookingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_customer(current_user)
    showtime = get_future_showtime(db, request.showtime_id)
    expire_pending_bookings(db, request.showtime_id)

    screen = db.get(Screen, showtime.screen_id)
    if screen is None:
        raise HTTPException(status_code=500, detail="Screen configuration missing")

    if request.seat_number > screen.total_seats:
        raise HTTPException(
            status_code=422,
            detail=f"Seat number must be between 1 and {screen.total_seats}",
        )

    existing = db.scalar(
        select(Booking)
        .where(
            Booking.showtime_id == request.showtime_id,
            Booking.seat_number == request.seat_number,
        )
        .with_for_update()
    )

    if existing is not None and existing.status in ("pending_payment", "confirmed"):
        raise HTTPException(
            status_code=409,
            detail="This seat is already booked or awaiting payment",
        )

    if existing is not None:
        existing.user_id = current_user.id
        existing.status = "pending_payment"
        existing.booked_at = datetime.now(timezone.utc)
        booking = existing
    else:
        booking = Booking(
            user_id=current_user.id,
            showtime_id=request.showtime_id,
            seat_number=request.seat_number,
            status="pending_payment",
        )
        db.add(booking)

    try:
        db.commit()
        db.refresh(booking)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="This seat was just reserved by another customer. Please choose another seat.",
        )

    publish_event(
        "booking.created",
        {
            "booking_id": booking.id,
            "showtime_id": booking.showtime_id,
            "seat_number": booking.seat_number,
            "status": booking.status,
        },
    )

    return booking


@router.get("/api/bookings/me", response_model=list[BookingResponse])
def list_my_bookings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    statement = (
        select(Booking)
        .where(Booking.user_id == current_user.id)
        .order_by(Booking.booked_at.desc())
    )
    return list(db.scalars(statement).all())


@router.post(
    "/api/bookings/{booking_id}/cancel",
    response_model=BookingResponse,
)
def cancel_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_customer(current_user)

    booking = db.scalar(
        select(Booking)
        .where(Booking.id == booking_id)
        .with_for_update()
    )

    if booking is None or booking.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Booking not found")

    if booking.status == "cancelled":
        raise HTTPException(status_code=409, detail="Booking is already cancelled")

    showtime = db.get(Showtime, booking.showtime_id)
    if showtime is None:
        raise HTTPException(status_code=404, detail="Showtime not found")

    if showtime.starts_at <= datetime.now(timezone.utc):
        raise HTTPException(
            status_code=400,
            detail="A booking cannot be cancelled after the show has started",
        )

    booking.status = "cancelled"
    db.commit()
    db.refresh(booking)

    return booking
