from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth_routes import get_current_user
from app.database import get_db
from app.models import Movie
from datetime import datetime, timedelta, timezone

from app.booking_models import Booking, Cinema, Payment, Screen, Showtime, Ticket
from app.user_models import User

router = APIRouter(prefix="/api/admin", tags=["Administration"])


def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access required",
        )
    return current_user


class AdminMovieCreate(BaseModel):
    title: str = Field(min_length=1, max_length=150)
    genre: str = Field(min_length=1, max_length=100)
    language: str = Field(min_length=1, max_length=50)
    duration_minutes: int = Field(gt=0, le=600)
    description: str = Field(min_length=1, max_length=10000)
    poster_url: str = Field(min_length=1, max_length=500)
    is_active: bool = True


class AdminMovieUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=150)
    genre: str | None = Field(default=None, min_length=1, max_length=100)
    language: str | None = Field(default=None, min_length=1, max_length=50)
    duration_minutes: int | None = Field(default=None, gt=0, le=600)
    description: str | None = Field(default=None, min_length=1, max_length=10000)
    poster_url: str | None = Field(default=None, min_length=1, max_length=500)


class AdminMovieStatus(BaseModel):
    is_active: bool


class AdminMovieResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    genre: str
    language: str
    duration_minutes: int
    description: str
    poster_url: str
    is_active: bool


@router.get("/dashboard")
def admin_dashboard(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user_count = db.scalar(select(func.count()).select_from(User)) or 0
    movie_count = db.scalar(
        select(func.count()).select_from(Movie).where(Movie.is_active.is_(True))
    ) or 0

    return {
        "message": "Administrator access verified",
        "admin_email": admin.email,
        "statistics": {
            "total_users": user_count,
            "total_movies": movie_count,
        },
    }


@router.get("/movies", response_model=list[AdminMovieResponse])
def list_admin_movies(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    statement = select(Movie).order_by(Movie.id)
    return list(db.scalars(statement).all())


@router.post(
    "/movies",
    response_model=AdminMovieResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_admin_movie(
    request: AdminMovieCreate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    values = request.model_dump()
    for key in ("title", "genre", "language", "description", "poster_url"):
        values[key] = values[key].strip()
        if not values[key]:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"{key} cannot be blank",
            )

    movie = Movie(**values)
    db.add(movie)
    try:
        db.commit()
        db.refresh(movie)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Movie could not be created because of a data conflict",
        ) from exc

    return movie


@router.patch("/movies/{movie_id}", response_model=AdminMovieResponse)
def update_admin_movie(
    movie_id: int,
    request: AdminMovieUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    movie = db.get(Movie, movie_id)
    if movie is None:
        raise HTTPException(status_code=404, detail="Movie not found")

    changes = request.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Provide at least one field to update",
        )

    for key, value in changes.items():
        if isinstance(value, str):
            value = value.strip()
            if not value:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"{key} cannot be blank",
                )
        setattr(movie, key, value)

    try:
        db.commit()
        db.refresh(movie)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Movie could not be updated because of a data conflict",
        ) from exc

    return movie


@router.patch(
    "/movies/{movie_id}/status",
    response_model=AdminMovieResponse,
)
def set_admin_movie_status(
    movie_id: int,
    request: AdminMovieStatus,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    movie = db.get(Movie, movie_id)
    if movie is None:
        raise HTTPException(status_code=404, detail="Movie not found")

    movie.is_active = request.is_active
    db.commit()
    db.refresh(movie)
    return movie

@router.get("/analytics")
def admin_analytics(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Read-only operational analytics for the admin Command Center."""
    now = datetime.now(timezone.utc)
    start_day = (now - timedelta(days=6)).date()

    users_total = db.scalar(
        select(func.count()).select_from(User)
    ) or 0
    movies_total = db.scalar(
        select(func.count()).select_from(Movie)
    ) or 0
    movies_active = db.scalar(
        select(func.count()).select_from(Movie).where(Movie.is_active.is_(True))
    ) or 0
    cinemas_total = db.scalar(
        select(func.count()).select_from(Cinema)
    ) or 0
    screens_total = db.scalar(
        select(func.count()).select_from(Screen)
    ) or 0
    showtimes_upcoming = db.scalar(
        select(func.count()).select_from(Showtime).where(Showtime.starts_at >= now)
    ) or 0
    bookings_total = db.scalar(
        select(func.count()).select_from(Booking)
    ) or 0
    bookings_confirmed = db.scalar(
        select(func.count()).select_from(Booking).where(Booking.status == "confirmed")
    ) or 0
    bookings_pending = db.scalar(
        select(func.count()).select_from(Booking).where(Booking.status == "pending_payment")
    ) or 0
    bookings_cancelled = db.scalar(
        select(func.count()).select_from(Booking).where(Booking.status == "cancelled")
    ) or 0

    # Revenue means successful recorded payments only; amounts are stored in paise.
    revenue_paise = db.scalar(
        select(func.coalesce(func.sum(Payment.amount_paise), 0)).where(
            Payment.status == "succeeded"
        )
    ) or 0
    payments_succeeded = db.scalar(
        select(func.count()).select_from(Payment).where(Payment.status == "succeeded")
    ) or 0
    payments_pending = db.scalar(
        select(func.count()).select_from(Payment).where(Payment.status == "pending")
    ) or 0
    payments_failed = db.scalar(
        select(func.count()).select_from(Payment).where(Payment.status == "failed")
    ) or 0

    payment_rows = db.execute(
        select(Payment.created_at, Payment.amount_paise).where(
            Payment.status == "succeeded",
            Payment.created_at >= datetime.combine(
                start_day, datetime.min.time(), tzinfo=timezone.utc
            ),
        )
    ).all()

    revenue_by_day = {}
    for offset in range(7):
        day = start_day + timedelta(days=offset)
        revenue_by_day[day.isoformat()] = 0

    for created_at, amount_paise in payment_rows:
        day_key = created_at.date().isoformat()
        if day_key in revenue_by_day:
            revenue_by_day[day_key] += int(amount_paise)

    booking_rows = db.execute(
        select(Booking.booked_at).where(
            Booking.booked_at >= datetime.combine(
                start_day, datetime.min.time(), tzinfo=timezone.utc
            )
        )
    ).scalars().all()

    bookings_by_day = {day: 0 for day in revenue_by_day}
    for booked_at in booking_rows:
        day_key = booked_at.date().isoformat()
        if day_key in bookings_by_day:
            bookings_by_day[day_key] += 1

    top_movie_rows = db.execute(
        select(
            Movie.id,
            Movie.title,
            func.count(Booking.id).label("booking_count"),
        )
        .join(Showtime, Showtime.movie_id == Movie.id)
        .join(Booking, Booking.showtime_id == Showtime.id)
        .where(Booking.status == "confirmed")
        .group_by(Movie.id, Movie.title)
        .order_by(func.count(Booking.id).desc(), Movie.title)
        .limit(5)
    ).all()

    recent_rows = db.execute(
        select(
            Booking.id,
            Booking.status,
            Booking.seat_number,
            Booking.booked_at,
            User.full_name,
            User.email,
            Movie.title.label("movie_title"),
            Cinema.name.label("cinema_name"),
            Showtime.starts_at,
            Payment.amount_paise,
            Payment.status.label("payment_status"),
        )
        .join(User, User.id == Booking.user_id)
        .join(Showtime, Showtime.id == Booking.showtime_id)
        .join(Movie, Movie.id == Showtime.movie_id)
        .join(Screen, Screen.id == Showtime.screen_id)
        .join(Cinema, Cinema.id == Screen.cinema_id)
        .outerjoin(Payment, Payment.booking_id == Booking.id)
        .order_by(Booking.booked_at.desc(), Booking.id.desc())
        .limit(10)
    ).all()

    upcoming_rows = db.execute(
        select(
            Showtime.id,
            Movie.title,
            Cinema.name.label("cinema_name"),
            Cinema.city,
            Screen.name.label("screen_name"),
            Showtime.starts_at,
            Showtime.ticket_price_paise,
            Screen.total_seats,
        )
        .join(Movie, Movie.id == Showtime.movie_id)
        .join(Screen, Screen.id == Showtime.screen_id)
        .join(Cinema, Cinema.id == Screen.cinema_id)
        .where(Showtime.starts_at >= now)
        .order_by(Showtime.starts_at)
        .limit(8)
    ).all()

    return {
        "generated_at": now.isoformat(),
        "admin_email": admin.email,
        "kpis": {
            "total_users": int(users_total),
            "total_movies": int(movies_total),
            "active_movies": int(movies_active),
            "total_cinemas": int(cinemas_total),
            "total_screens": int(screens_total),
            "upcoming_showtimes": int(showtimes_upcoming),
            "total_bookings": int(bookings_total),
            "confirmed_bookings": int(bookings_confirmed),
            "pending_bookings": int(bookings_pending),
            "cancelled_bookings": int(bookings_cancelled),
            "successful_payments": int(payments_succeeded),
            "pending_payments": int(payments_pending),
            "failed_payments": int(payments_failed),
            "successful_payment_revenue_paise": int(revenue_paise),
        },
        "revenue_trend": [
            {"date": day, "revenue_paise": amount}
            for day, amount in revenue_by_day.items()
        ],
        "booking_trend": [
            {"date": day, "bookings": count}
            for day, count in bookings_by_day.items()
        ],
        "top_movies": [
            {
                "movie_id": row.id,
                "title": row.title,
                "confirmed_bookings": int(row.booking_count),
            }
            for row in top_movie_rows
        ],
        "recent_bookings": [
            {
                "booking_id": row.id,
                "status": row.status,
                "seat_number": row.seat_number,
                "booked_at": row.booked_at.isoformat(),
                "customer_name": row.full_name,
                "customer_email": row.email,
                "movie_title": row.movie_title,
                "cinema_name": row.cinema_name,
                "showtime": row.starts_at.isoformat(),
                "payment_amount_paise": (
                    int(row.amount_paise) if row.amount_paise is not None else None
                ),
                "payment_status": row.payment_status,
            }
            for row in recent_rows
        ],
        "upcoming_shows": [
            {
                "showtime_id": row.id,
                "movie_title": row.title,
                "cinema_name": row.cinema_name,
                "city": row.city,
                "screen_name": row.screen_name,
                "starts_at": row.starts_at.isoformat(),
                "ticket_price_paise": int(row.ticket_price_paise),
                "total_seats": int(row.total_seats),
            }
            for row in upcoming_rows
        ],
    }
