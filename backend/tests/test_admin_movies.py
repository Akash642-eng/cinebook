import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth_routes import get_current_user
from app.database import Base, get_db
from app.main import app
from app.models import Movie
from app.user_models import User


@pytest.fixture
def test_environment():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestSession = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
    )
    Base.metadata.create_all(bind=engine)

    with TestSession() as db:
        admin = User(
            full_name="Test Administrator",
            email="admin-test@example.invalid",
            phone="1234567890",
            hashed_password="test-only-not-a-real-password",
            role="admin",
            is_active=True,
        )
        customer = User(
            full_name="Test Customer",
            email="customer-test@example.invalid",
            phone="1234567891",
            hashed_password="test-only-not-a-real-password",
            role="customer",
            is_active=True,
        )
        db.add_all([admin, customer])
        db.commit()
        db.refresh(admin)
        db.refresh(customer)
        admin_id = admin.id
        customer_id = customer.id

    def override_get_db():
        with TestSession() as db:
            yield db

    def override_admin_user():
        with TestSession() as db:
            user = db.get(User, admin_id)
            assert user is not None
            yield user

    def override_customer_user():
        with TestSession() as db:
            user = db.get(User, customer_id)
            assert user is not None
            yield user

    original_overrides = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_admin_user

    try:
        with TestClient(app) as client:
            yield client, TestSession, override_customer_user
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(original_overrides)
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def movie_payload(title="Test Movie"):
    return {
        "title": title,
        "genre": "Drama",
        "language": "English",
        "duration_minutes": 110,
        "description": "A test-only movie for catalogue management.",
        "poster_url": "https://example.invalid/test-poster.jpg",
        "is_active": True,
    }


def test_admin_movie_list_requires_authentication(test_environment):
    client, _, _ = test_environment
    original_override = app.dependency_overrides.pop(
        get_current_user, None
    )

    try:
        response = client.get("/api/admin/movies")
    finally:
        if original_override is not None:
            app.dependency_overrides[get_current_user] = original_override

    assert response.status_code == 401


def test_customer_cannot_access_admin_movies(test_environment):
    client, _, override_customer_user = test_environment
    app.dependency_overrides[get_current_user] = override_customer_user

    response = client.get("/api/admin/movies")

    assert response.status_code == 403


def test_admin_can_list_movies(test_environment):
    client, TestSession, _ = test_environment

    with TestSession() as db:
        db.add(Movie(**movie_payload("Existing Test Movie")))
        db.commit()

    response = client.get("/api/admin/movies")

    assert response.status_code == 200
    assert any(
        movie["title"] == "Existing Test Movie"
        for movie in response.json()
    )


def test_admin_can_create_movie(test_environment):
    client, _, _ = test_environment

    response = client.post(
        "/api/admin/movies",
        json=movie_payload("Created Test Movie"),
    )

    assert response.status_code == 201
    assert response.json()["title"] == "Created Test Movie"
    assert response.json()["is_active"] is True


def test_admin_can_update_movie_and_deactivate_it(test_environment):
    client, TestSession, _ = test_environment

    with TestSession() as db:
        movie = Movie(**movie_payload("Before Update"))
        db.add(movie)
        db.commit()
        db.refresh(movie)
        movie_id = movie.id

    update_response = client.patch(
        f"/api/admin/movies/{movie_id}",
        json={"title": "After Update"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["title"] == "After Update"

    status_response = client.patch(
        f"/api/admin/movies/{movie_id}/status",
        json={"is_active": False},
    )
    assert status_response.status_code == 200
    assert status_response.json()["is_active"] is False

    public_response = client.get("/api/movies")
    assert public_response.status_code == 200
    assert all(
        movie["id"] != movie_id
        for movie in public_response.json()
    )


def test_admin_movie_create_rejects_invalid_input(test_environment):
    client, _, _ = test_environment

    response = client.post(
        "/api/admin/movies",
        json={
            **movie_payload(),
            "duration_minutes": 0,
        },
    )

    assert response.status_code == 422


def test_admin_movie_update_returns_404_for_unknown_id(test_environment):
    client, _, _ = test_environment

    response = client.patch(
        "/api/admin/movies/999999",
        json={"title": "Missing Movie"},
    )

    assert response.status_code == 404
