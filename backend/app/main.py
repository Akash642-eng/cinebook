from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from app.metrics import install_metrics
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.auth_routes import router as auth_router
from app.admin_routes import router as admin_router
from app.booking_routes import router as booking_router
from app.booking_customer_routes import router as booking_customer_router
from app.payment_routes import router as payment_router
from app.database import Base, engine, get_db
from app.models import Movie
from app.booking_models import Booking, Cinema, Screen, Showtime
from app.user_models import User
from app.schemas import MovieResponse


STARTER_MOVIES = [
    {
        "title": "The Last Horizon",
        "genre": "Science Fiction",
        "language": "English",
        "duration_minutes": 142,
        "description": "An astronaut discovers a signal that could change humanity's future.",
        "poster_url": "https://placehold.co/600x900/172554/FFFFFF?text=The+Last+Horizon",
    },
    {
        "title": "Midnight Express",
        "genre": "Thriller",
        "language": "English",
        "duration_minutes": 128,
        "description": "A late-night train journey becomes a race against time.",
        "poster_url": "https://placehold.co/600x900/312E81/FFFFFF?text=Midnight+Express",
    },
    {
        "title": "Monsoon Dreams",
        "genre": "Drama",
        "language": "Kannada",
        "duration_minutes": 135,
        "description": "A family returns to its hometown to rediscover what matters most.",
        "poster_url": "https://placehold.co/600x900/134E4A/FFFFFF?text=Monsoon+Dreams",
    },
    {
        "title": "The Final Lap",
        "genre": "Sports",
        "language": "Hindi",
        "duration_minutes": 119,
        "description": "A determined young racer fights for one final chance.",
        "poster_url": "https://placehold.co/600x900/7C2D12/FFFFFF?text=The+Final+Lap",
    },
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Temporary Day 1 bootstrap. Database migrations will be added later.
    Base.metadata.create_all(bind=engine)

    with Session(engine) as db:
        existing_movie = db.scalar(select(Movie.id).limit(1))
        if existing_movie is None:
            db.add_all([Movie(**movie) for movie in STARTER_MOVIES])
            db.commit()

    yield


app = FastAPI(
    title="CineBook API",
    description="Movie ticket booking platform API",
    version="0.1.0",
    lifespan=lifespan,
)

install_metrics(app)

app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(booking_router)
app.include_router(booking_customer_router)
app.include_router(payment_router)


@app.get("/api/health")
def health():
    return {"status": "healthy", "service": "cinebook-api"}


@app.get("/api/ready")
def readiness(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ready", "database": "connected"}
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="Database unavailable",
        ) from exc


@app.get("/api/version")
def version():
    return {"application": "cinebook", "version": "0.1.0"}


@app.get("/api/movies", response_model=list[MovieResponse])
def list_movies(db: Session = Depends(get_db)):
    statement = (
        select(Movie)
        .where(Movie.is_active.is_(True))
        .order_by(Movie.id)
    )
    return list(db.scalars(statement).all())


@app.get("/api/movies/{movie_id}", response_model=MovieResponse)
def get_movie(movie_id: int, db: Session = Depends(get_db)):
    movie = db.get(Movie, movie_id)
    if movie is None or not movie.is_active:
        raise HTTPException(status_code=404, detail="Movie not found")
    return movie
