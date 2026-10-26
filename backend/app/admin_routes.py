from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth_routes import get_current_user
from app.database import get_db
from app.models import Movie
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