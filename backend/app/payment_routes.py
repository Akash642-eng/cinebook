import hashlib
import logging
import secrets
import time
from threading import Lock
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

router = APIRouter(prefix="/api/payments", tags=["Payments"])
PAYMENT_TIMEOUT_MINUTES = 10


class SandboxPaymentRequest(BaseModel):
    booking_id: int = Field(gt=0)
    payment_method: str = Field(pattern="^(card|upi)$")
    instrument: str = Field(min_length=1, max_length=100)
    otp: str = Field(pattern=r"^\d{6}$")


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


def _owned_booking(db: Session, booking_id: int, user: User) -> Booking:
    booking = db.scalar(
        select(Booking).where(Booking.id == booking_id).with_for_update()
    )
    if booking is None or booking.user_id != user.id:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking


def _check_booking_payable(db: Session, booking: Booking) -> Showtime:
    now = datetime.now(timezone.utc)
    booked_at = booking.booked_at
    if booked_at.tzinfo is None:
        booked_at = booked_at.replace(tzinfo=timezone.utc)
    if booked_at <= now - timedelta(minutes=PAYMENT_TIMEOUT_MINUTES):
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
        raise HTTPException(
            status_code=400,
            detail="Showtime has started; pending booking was cancelled",
        )
    return showtime


def _publish_payment_event(payment: Payment) -> None:
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
        # The committed database transaction remains authoritative if RabbitMQ is unavailable.
        pass



# CINEBOOK_RANDOM_OTP_PATCH
# Local sandbox only: OTPs are logged to backend logs, never returned to the browser.
_otp_lock = Lock()
_otp_challenges = {}
_otp_ttl_seconds = 300
_otp_max_attempts = 5
_otp_logger = logging.getLogger(__name__)


class SandboxOtpRequest(BaseModel):
    booking_id: int = Field(gt=0)


def _otp_digest(user_id, booking_id, code):
    raw = f"{user_id}:{booking_id}:{code}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _issue_sandbox_otp(user_id, booking_id):
    code = f"{secrets.randbelow(1_000_000):06d}"
    now = time.monotonic()
    with _otp_lock:
        _otp_challenges[(str(user_id), int(booking_id))] = {
            "digest": _otp_digest(user_id, booking_id, code),
            "expires": now + _otp_ttl_seconds,
            "attempts": 0,
        }
    _otp_logger.warning(
        "CINEBOOK SANDBOX OTP | user=%s booking=%s code=%s | expires in 5 minutes",
        user_id, booking_id, code
    )


def _verify_sandbox_otp(user_id, booking_id, code):
    key = (str(user_id), int(booking_id))
    now = time.monotonic()
    with _otp_lock:
        challenge = _otp_challenges.get(key)
        if challenge is None or now >= challenge["expires"]:
            _otp_challenges.pop(key, None)
            return False
        if challenge["attempts"] >= _otp_max_attempts:
            _otp_challenges.pop(key, None)
            return False
        challenge["attempts"] += 1
        candidate = _otp_digest(user_id, booking_id, code)
        return secrets.compare_digest(candidate, challenge["digest"])


@router.post("/otp/request")
def request_sandbox_otp(
    request: SandboxOtpRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "customer":
        raise HTTPException(status_code=403, detail="Customer account required")

    booking = _owned_booking(db, request.booking_id, current_user)
    if booking.status != "pending_payment":
        raise HTTPException(status_code=409, detail="Booking is not awaiting payment")

    _issue_sandbox_otp(current_user.id, booking.id)
    return {"message": "A sandbox OTP was generated. Check the local backend logs."}


@router.post("/sandbox", response_model=PaymentResponse)
def simulate_payment(
    request: SandboxPaymentRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", max_length=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "customer":
        raise HTTPException(status_code=403, detail="Only customers can make payments")

    if not _verify_sandbox_otp(current_user.id, request.booking_id, request.otp):
        raise HTTPException(status_code=400, detail="Invalid or expired OTP. Request a new code and try again.")

    # Deterministic demo gateway rules; never contacts a bank or card network.
    instrument = request.instrument.strip().lower()
    if request.payment_method == "card":
        if not instrument.isdigit() or len(instrument) != 4:
            raise HTTPException(status_code=400, detail="Enter a valid demo card number")
        approved = instrument != "0000" and secrets.randbelow(100) < 80
    else:
        if "@" not in instrument:
            raise HTTPException(status_code=400, detail="Enter a valid demo UPI ID")
        approved = "fail" not in instrument and secrets.randbelow(100) < 80
    expected_status = "succeeded" if approved else "failed"
    effective_key = (idempotency_key or f"cinebook-booking-{request.booking_id}-{request.payment_method}-{instrument}").strip()
    if not effective_key or len(effective_key) > 100:
        raise HTTPException(status_code=400, detail="Invalid Idempotency-Key")

    existing = db.scalar(select(Payment).where(Payment.idempotency_key == effective_key))
    if existing is not None:
        existing_booking = db.get(Booking, existing.booking_id)
        if existing_booking is None or existing_booking.user_id != current_user.id:
            raise HTTPException(status_code=404, detail="Booking not found")
        if existing.booking_id != request.booking_id or existing.status != expected_status:
            raise HTTPException(status_code=409, detail="Idempotency key was already used differently")
        return _payment_response(existing)

    booking = _owned_booking(db, request.booking_id, current_user)
    existing = db.scalar(select(Payment).where(Payment.idempotency_key == effective_key))
    if existing is not None:
        if existing.booking_id != request.booking_id or existing.status != expected_status:
            raise HTTPException(status_code=409, detail="Idempotency key was already used differently")
        return _payment_response(existing)

    if booking.status != "pending_payment":
        raise HTTPException(status_code=409, detail="Booking is not awaiting payment")
    showtime = _check_booking_payable(db, booking)

    payment = Payment(
        booking_id=booking.id,
        amount_paise=showtime.ticket_price_paise,
        currency="INR",
        provider="sandbox",
        status=expected_status,
        reference=f"CB-SBX-{uuid4().hex}",
        idempotency_key=effective_key,
    )
    if approved:
        booking.status = "confirmed"
        if db.scalar(select(Ticket).where(Ticket.booking_id == booking.id)) is None:
            db.add(Ticket(booking_id=booking.id, token=token_urlsafe(32)))
    else:
        booking.status = "cancelled"

    db.add(payment)
    try:
        db.commit()
        db.refresh(payment)
    except IntegrityError:
        db.rollback()
        existing = db.scalar(select(Payment).where(Payment.idempotency_key == effective_key))
        if existing is not None and existing.booking_id == request.booking_id and existing.status == expected_status:
            return _payment_response(existing)
        raise HTTPException(status_code=409, detail="Payment could not be recorded; check booking status")

    _publish_payment_event(payment)
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
