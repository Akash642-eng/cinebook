from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth_routes import get_current_user
from app.booking_models import Booking, Payment, Showtime
from app.database import get_db
from app.user_models import User

router = APIRouter(prefix="/api/payments", tags=["Sandbox Payments"])


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


@router.post("/sandbox", response_model=PaymentResponse)
def simulate_payment(
    request: SandboxPaymentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "customer":
        raise HTTPException(status_code=403, detail="Only customers can make payments")

    booking = db.scalar(
        select(Booking)
        .where(Booking.id == request.booking_id)
        .with_for_update()
    )

    if booking is None or booking.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Booking not found")

    if booking.status != "pending_payment":
        raise HTTPException(
            status_code=409,
            detail="Booking is not awaiting payment",
        )

    showtime = db.get(Showtime, booking.showtime_id)
    if showtime is None:
        raise HTTPException(status_code=404, detail="Showtime not found")

    if showtime.starts_at <= datetime.now(timezone.utc):
        booking.status = "cancelled"
        db.commit()
        raise HTTPException(
            status_code=400,
            detail="Showtime has started; pending booking was cancelled",
        )

    payment = Payment(
        booking_id=booking.id,
        amount_paise=showtime.ticket_price_paise,
        currency="INR",
        provider="sandbox",
        status="succeeded" if request.outcome == "success" else "failed",
        reference=f"CB-SBX-{uuid4().hex}",
    )

    if request.outcome == "success":
        booking.status = "confirmed"
    else:
        booking.status = "cancelled"

    db.add(payment)

    try:
        db.commit()
        db.refresh(payment)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Payment could not be recorded; please check booking status",
        )

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
    payments = list(db.scalars(statement).all())
    return [
        {
            "id": payment.id,
            "booking_id": payment.booking_id,
            "amount_rupees": f"{payment.amount_paise / 100:.2f}",
            "currency": payment.currency,
            "provider": payment.provider,
            "status": payment.status,
            "reference": payment.reference,
            "created_at": payment.created_at,
        }
        for payment in payments
    ]
