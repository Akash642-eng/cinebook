from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.database import Base, SessionLocal, engine
from app.models import Movie
from app.user_models import User
from app.booking_models import Booking, Cinema, Screen, Showtime

# Ensure all model classes are registered before creating missing tables.
Base.metadata.create_all(bind=engine)

with SessionLocal() as db:
    cinema = db.scalar(
        select(Cinema).where(Cinema.name == "CineBook Central")
    )

    if cinema is None:
        cinema = Cinema(
            name="CineBook Central",
            city="Mysuru",
            address="Demo Address, Mysuru, Karnataka",
        )
        db.add(cinema)
        db.flush()

    screens = list(
        db.scalars(
            select(Screen).where(Screen.cinema_id == cinema.id)
        ).all()
    )

    if not screens:
        screens = [
            Screen(cinema_id=cinema.id, name="Screen 1", total_seats=40),
            Screen(cinema_id=cinema.id, name="Screen 2", total_seats=40),
        ]
        db.add_all(screens)
        db.flush()

    movies = list(
        db.scalars(
            select(Movie).where(Movie.is_active.is_(True)).order_by(Movie.id)
        ).all()
    )

    if not movies:
        raise SystemExit("No active movies found. Check /api/movies first.")

    existing_showtime = db.scalar(select(Showtime.id).limit(1))

    if existing_showtime is None:
        now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
        slots = [
            now + timedelta(days=1, hours=10),
            now + timedelta(days=1, hours=14),
        ]

        new_showtimes = []
        for index, movie in enumerate(movies):
            screen = screens[index % len(screens)]
            for start in slots:
                new_showtimes.append(
                    Showtime(
                        movie_id=movie.id,
                        screen_id=screen.id,
                        starts_at=start,
                        ticket_price_paise=25000,
                    )
                )

        db.add_all(new_showtimes)
        db.commit()
        print(f"Created {len(new_showtimes)} demo showtimes.")
    else:
        print("Showtimes already exist; no duplicate seed data created.")

    print(f"Cinema: {cinema.name}, {cinema.city}")
    print(f"Screens: {len(screens)}")
