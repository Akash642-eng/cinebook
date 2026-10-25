from datetime import datetime, timedelta, timezone
from secrets import token_urlsafe
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth_routes import get_current_user
from app.booking_models import Booking, Payment, Showtime, Ticket
from app.database import get_db
from app.event_publisher import publish_event
from app.user_models import User

router = APIRouter(prefix="/api/payments", tags=["Sandbox Payments"])
PAYMENT_TIMEOUT_MINUTES = 10


class SandboxPaymentRequest(BaseModel):
    booking_id: int = Field(gt=0)
    outcome: str = Field(pattern="^(success|failure)$")


class PaymentResponse(BaseModel):
    id: int
    booking_id: int
    amount_rupees: str
    currency: str
    provider: str
    status: str
    reference: str
    created_at: datetime


def _payment_response(payment: Payment) -> dict:
    return {
        "id": payment.id,
        "booking_id": payment.booking_id,
        "amount_rupees": f"{payment.amount_paise / 100:.2f}",
        "currency": payment.currency,
        "provider": payment.provider,
        "status": payment.status,
        "reference": payment.reference,
        "created_at": payment.created_at,
    }


def _return_existing_payment(
    payment: Payment,
    booking_id: int,
    expected_status: str,
    current_user: User,
    db: Session,
) -> dict:
    existing_booking = db.get(Booking, payment.booking_id)
    if existing_booking is None or existing_booking.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Booking not found")
    if payment.booking_id != booking_id or payment.status != expected_status:
        raise HTTPException(
            status_code=409,
            detail="Idempotency key was already used for a different booking or outcome",
        )
    return _payment_response(payment)


@router.post("/sandbox", response_model=PaymentResponse)
def simulate_payment(
    request: SandboxPaymentRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", max_length=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "customer":
        raise HTTPException(status_code=403, detail="Only customers can make payments")

    expected_status = "succeeded" if request.outcome == "success" else "failed"
    # Deterministic fallback keeps existing frontend clients replay-safe; new clients may send the header.
    effective_key = (idempotency_key or f"cinebook-booking-{request.booking_id}-{request.outcome}").strip()
    if not effective_key or len(effective_key) > 100:
        raise HTTPException(status_code=400, detail="Invalid Idempotency-Key")

    existing = db.scalar(select(Payment).where(Payment.idempotency_key == effective_key))
    if existing is not None:
        return _return_existing_payment(existing, request.booking_id, expected_status, current_user, db)

    booking = db.scalar(
        select(Booking).where(Booking.id == request.booking_id).with_for_update()
    )
    if booking is None or booking.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Booking not found")

    # A concurrent request may have committed this key while we waited for the booking lock.
    existing = db.scalar(select(Payment).where(Payment.idempotency_key == effective_key))
    if existing is not None:
        return _return_existing_payment(existing, request.booking_id, expected_status, current_user, db)

    if booking.status != "pending_payment":
        raise HTTPException(status_code=409, detail="Booking is not awaiting payment")

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(minutes=PAYMENT_TIMEOUT_MINUTES)
    booked_at = booking.booked_at
    if booked_at.tzinfo is None:
        booked_at = booked_at.replace(tzinfo=timezone.utc)
    if booked_at <= cutoff:
        booking.status = "cancelled"
        db.commit()
        raise HTTPException(
            status_code=409,
            detail="Payment window expired; booking was cancelled. Please select the seat again.",
        )

    showtime = db.get(Showtime, booking.showtime_id)
    if showtime is None:
        raise HTTPException(status_code=404, detail="Showtime not found")
    starts_at = showtime.starts_at
    if starts_at.tzinfo is None:
        starts_at = starts_at.replace(tzinfo=timezone.utc)
    if starts_at <= now:
        booking.status = "cancelled"
        db.commit()
        raise HTTPException(status_code=400, detail="Showtime has started; pending booking was cancelled")

    payment = Payment(
        booking_id=booking.id,
        amount_paise=showtime.ticket_price_paise,
        currency="INR",
        provider="sandbox",
        status=expected_status,
        reference=f"CB-SBX-{uuid4().hex}",
        idempotency_key=effective_key,
    )
    if request.outcome == "success":
        booking.status = "confirmed"
        db.add(Ticket(booking_id=booking.id, token=token_urlsafe(32)))
    else:
        booking.status = "cancelled"

    db.add(payment)
    try:
        db.commit()
        db.refresh(payment)
    except IntegrityError:
        db.rollback()
        # A simultaneous request using the same key may have won the unique-index race.
        existing = db.scalar(select(Payment).where(Payment.idempotency_key == effective_key))
        if existing is not None:
            return _return_existing_payment(existing, request.booking_id, expected_status, current_user, db)
        raise HTTPException(status_code=409, detail="Payment could not be recorded; check booking status")

    # Publish only after the transaction committed; replayed requests do not publish duplicates.
    try:
        publish_event(
            "payment.succeeded" if payment.status == "succeeded" else "payment.failed",
            {
                "payment_id": payment.id,
                "booking_id": payment.booking_id,
                "status": payment.status,
                "amount_rupees": f"{payment.amount_paise / 100:.2f}",
                "currency": payment.currency,
            },
        )
    except Exception:
        # The committed payment/ticket remain authoritative even if the optional event broker is unavailable.
        pass

    return _payment_response(payment)


@router.get("/me", response_model=list[PaymentResponse])
def list_my_payments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    statement = (
        select(Payment)
        .join(Booking, Payment.booking_id == Booking.id)
        .where(Booking.user_id == current_user.id)
        .order_by(Payment.created_at.desc())
    )
    return [_payment_response(payment) for payment in db.scalars(statement).all()]