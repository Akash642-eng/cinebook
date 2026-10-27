from pathlib import Path
from datetime import datetime
import os
from io import BytesIO

import qrcode
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth_routes import get_current_user
from app.booking_models import Booking, Showtime, Ticket
from app.database import get_db
from app.models import Movie
from app.user_models import User

router = APIRouter(prefix="/api/tickets", tags=["Tickets"])


def _public_base_url() -> str:
    # For local Docker development, the browser-facing frontend is localhost:5173.
    # Set PUBLIC_APP_URL to your public HTTPS domain when deploying.
    return os.getenv("PUBLIC_APP_URL", "http://localhost:5173").rstrip("/")


def _ticket_pdf_url(token: str) -> str:
    return f"{_public_base_url()}/api/tickets/{token}/pdf"


def _ticket_row(token: str, db: Session):
    return db.execute(
        select(Ticket, Booking, Showtime, Movie)
        .join(Booking, Ticket.booking_id == Booking.id)
        .join(Showtime, Booking.showtime_id == Showtime.id)
        .join(Movie, Showtime.movie_id == Movie.id)
        .where(Ticket.token == token)
    ).first()


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

    # Relative URLs ensure images and links use the browser-facing frontend host,
    # not an internal Docker hostname such as "backend".
    return [
        {
            "id": ticket.id,
            "ticket_id": ticket.id,
            "booking_id": booking.id,
            "status": "valid" if booking.status == "confirmed" else "invalid",
            "movie_title": movie.title,
            "showtime_id": showtime.id,
            "starts_at": showtime.starts_at,
            "seat_number": booking.seat_number,
            "created_at": ticket.created_at,
            "verification_url": f"/api/tickets/verify/{ticket.token}",
            "qr_url": f"/api/tickets/{ticket.token}/qr",
            "pdf_url": f"/api/tickets/{ticket.token}/pdf",
        }
        for ticket, booking, showtime, movie in rows
    ]


@router.get("/verify/{token}")
def verify_ticket(token: str, db: Session = Depends(get_db)):
    row = _ticket_row(token, db)
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


@router.get("/{token}/pdf")
def download_ticket_pdf(token: str, db: Session = Depends(get_db)):
    row = _ticket_row(token, db)
    if row is None:
        raise HTTPException(status_code=404, detail="Ticket not found")

    ticket, booking, showtime, movie = row
    if booking.status != "confirmed":
        raise HTTPException(status_code=409, detail="Ticket is not valid")

    pdf_buffer = BytesIO()
    document = SimpleDocTemplate(
        pdf_buffer,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title=f"CineBook Ticket - Booking {booking.id}",
        author="CineBook",
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="CineBookTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=25,
        leading=30,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#f43f83"),
        spaceAfter=5 * mm,
    ))
    styles.add(ParagraphStyle(
        name="TicketSubtitle",
        parent=styles["Normal"],
        alignment=TA_CENTER,
        fontSize=10,
        textColor=colors.HexColor("#625568"),
        spaceAfter=8 * mm,
    ))
    styles.add(ParagraphStyle(
        name="TicketSection",
        parent=styles["Heading2"],
        fontSize=13,
        leading=17,
        textColor=colors.HexColor("#241724"),
        spaceBefore=4 * mm,
        spaceAfter=3 * mm,
    ))

    story = [
        Paragraph("CineBook", styles["CineBookTitle"]),
        Paragraph("MOVIE ADMISSION TICKET", styles["TicketSubtitle"]),
        Paragraph(str(movie.title), styles["Heading1"]),
        Spacer(1, 3 * mm),
    ]

    starts_at = showtime.starts_at
    if hasattr(starts_at, "strftime"):
        starts_at_text = starts_at.strftime("%d %b %Y, %I:%M %p")
    else:
        starts_at_text = str(starts_at)

    cinema = getattr(showtime, "cinema_name", "CineBook Cinema")
    screen = getattr(showtime, "screen_name", "As assigned")
    city = getattr(showtime, "city", "")
    amount_paise = getattr(showtime, "ticket_price_paise", 0)
    amount_text = f"INR {amount_paise / 100:.2f}"

    details = [
        ["BOOKING ID", f"#{booking.id}"],
        ["TICKET STATUS", "CONFIRMED"],
        ["MOVIE", str(movie.title)],
        ["CINEMA", str(cinema)],
        ["CITY", str(city)],
        ["SCREEN", str(screen)],
        ["DATE AND TIME", starts_at_text],
        ["SEAT NUMBER", str(booking.seat_number)],
        ["TICKET PRICE", amount_text],
        ["TICKET REFERENCE", str(ticket.token)],
    ]

    table = Table(details, colWidths=[48 * mm, 105 * mm], hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f3edf4")),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#59465b")),
        ("TEXTCOLOR", (1, 0), (1, -1), colors.HexColor("#211721")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("LEADING", (0, 0), (-1, -1), 13),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#dfd3e0")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 9),
        ("RIGHTPADDING", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))

    story.extend([
        table,
        Spacer(1, 8 * mm),
        Paragraph("Scan to download this ticket PDF", styles["TicketSubtitle"]),
    ])

    qr = qrcode.make(_ticket_pdf_url(ticket.token))
    qr_buffer = BytesIO()
    qr.save(qr_buffer, format="PNG")
    qr_buffer.seek(0)
    qr_image = Image(qr_buffer, width=42 * mm, height=42 * mm)
    qr_image.hAlign = "CENTER"
    story.extend([
        qr_image,
        Spacer(1, 5 * mm),
        Paragraph(
            "Keep this ticket for admission. The QR code opens the downloadable "
            "ticket PDF. The ticket can be used only while its booking remains confirmed.",
            styles["TicketSubtitle"],
        ),
    ])

    document.build(story)
    pdf_buffer.seek(0)

    return Response(
        content=pdf_buffer.getvalue(),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="CineBook-Ticket-{booking.id}.pdf"',
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/{token}/qr")
def ticket_qr(token: str, db: Session = Depends(get_db)):
    row = _ticket_row(token, db)
    if row is None:
        raise HTTPException(status_code=404, detail="Ticket not found")

    ticket, booking, showtime, movie = row
    if booking.status != "confirmed":
        raise HTTPException(status_code=409, detail="Ticket is not valid")

    image = qrcode.make(_ticket_pdf_url(ticket.token))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return Response(
        content=buffer.getvalue(),
        media_type="image/png",
        headers={"Cache-Control": "no-store"},
    )
