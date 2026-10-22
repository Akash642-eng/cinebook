from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.booking_models import Cinema, Screen, Showtime
from app.booking_schemas import CinemaResponse, ShowtimeResponse
from app.database import get_db
from app.models import Movie

router = APIRouter(tags=["Cinemas and Showtimes"])


@router.get("/api/cinemas", response_model=list[CinemaResponse])
def list_cinemas(db: Session = Depends(get_db)):
    statement = select(Cinema).order_by(Cinema.city, Cinema.name)
    return list(db.scalars(statement).all())


@router.get("/api/showtimes", response_model=list[ShowtimeResponse])
def list_showtimes(
    movie_id: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db),
):
    now = datetime.now(timezone.utc)

    statement = (
        select(
            Showtime.id.label("id"),
            Showtime.movie_id.label("movie_id"),
            Movie.title.label("movie_title"),
            Cinema.id.label("cinema_id"),
            Cinema.name.label("cinema_name"),
            Cinema.city.label("city"),
            Screen.id.label("screen_id"),
            Screen.name.label("screen_name"),
            Screen.total_seats.label("total_seats"),
            Showtime.starts_at.label("starts_at"),
            Showtime.ticket_price_paise.label("ticket_price_paise"),
        )
        .join(Movie, Movie.id == Showtime.movie_id)
        .join(Screen, Screen.id == Showtime.screen_id)
        .join(Cinema, Cinema.id == Screen.cinema_id)
        .where(Showtime.starts_at > now, Movie.is_active.is_(True))
        .order_by(Showtime.starts_at)
    )

    if movie_id is not None:
        if db.get(Movie, movie_id) is None:
            raise HTTPException(status_code=404, detail="Movie not found")
        statement = statement.where(Showtime.movie_id == movie_id)

    rows = db.execute(statement).mappings().all()
    return [dict(row) for row in rows]
