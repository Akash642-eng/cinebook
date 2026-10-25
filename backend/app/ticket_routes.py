from io import BytesIO

import qrcode
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth_routes import get_current_user
from app.booking_models import Booking, Showtime, Ticket
from app.database import get_db
from app.models import Movie
from app.user_models import User

router = APIRouter(prefix="/api/tickets", tags=["Tickets"])


def _verification_url(request: Request, token: str) -> str:
    return f"{str(request.base_url).rstrip('/')}/api/tickets/verify/{token}"


@router.get("/me")
def list_my_tickets(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = db.execute(
        select(Ticket, Booking, Showtime, Movie)
        .join(Booking, Ticket.booking_id == Booking.id)
        .join(Showtime, Booking.showtime_id == Showtime.id)
        .join(Movie, Showtime.movie_id == Movie.id)
        .where(Booking.user_id == current_user.id)
        .order_by(Ticket.created_at.desc())
    ).all()
    base = str(request.base_url).rstrip("/")
    return [
        {
            "ticket_id": ticket.id,
            "booking_id": booking.id,
            "status": "valid" if booking.status == "confirmed" else "invalid",
            "movie_title": movie.title,
            "showtime_id": showtime.id,
            "starts_at": showtime.starts_at,
            "seat_number": booking.seat_number,
            "created_at": ticket.created_at,
            "verification_url": f"{base}/api/tickets/verify/{ticket.token}",
            "qr_url": f"{base}/api/tickets/{ticket.token}/qr",
        }
        for ticket, booking, showtime, movie in rows
    ]


@router.get("/verify/{token}")
def verify_ticket(token: str, db: Session = Depends(get_db)):
    row = db.execute(
        select(Ticket, Booking, Showtime, Movie)
        .join(Booking, Ticket.booking_id == Booking.id)
        .join(Showtime, Booking.showtime_id == Showtime.id)
        .join(Movie, Showtime.movie_id == Movie.id)
        .where(Ticket.token == token)
    ).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Ticket not found")

    ticket, booking, showtime, movie = row
    valid = booking.status == "confirmed"
    return {
        "verified": valid,
        "ticket_status": "valid" if valid else "invalid",
        "booking_id": booking.id,
        "movie_title": movie.title,
        "showtime_id": showtime.id,
        "starts_at": showtime.starts_at,
        "seat_number": booking.seat_number,
    }


@router.get("/{token}/qr")
def ticket_qr(token: str, request: Request, db: Session = Depends(get_db)):
    ticket = db.scalar(select(Ticket).where(Ticket.token == token))
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    booking = db.get(Booking, ticket.booking_id)
    if booking is None or booking.status != "confirmed":
        raise HTTPException(status_code=409, detail="Ticket is not valid")

    image = qrcode.make(_verification_url(request, ticket.token))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return Response(
        content=buffer.getvalue(),
        media_type="image/png",
        headers={"Cache-Control": "no-store"},
    )