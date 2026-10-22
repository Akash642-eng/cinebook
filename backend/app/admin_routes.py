from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth_routes import get_current_user
from app.database import get_db
from app.models import Movie
from app.user_models import User

router = APIRouter(prefix="/api/admin", tags=["Administration"])


def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    from fastapi import HTTPException, status

    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access required",
        )

    return current_user


@router.get("/dashboard")
def admin_dashboard(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user_count = db.scalar(select(func.count()).select_from(User)) or 0
    movie_count = db.scalar(select(func.count()).select_from(Movie)) or 0

    return {
        "message": "Administrator access verified",
        "admin_email": admin.email,
        "statistics": {
            "total_users": user_count,
            "total_movies": movie_count,
        },
    }
