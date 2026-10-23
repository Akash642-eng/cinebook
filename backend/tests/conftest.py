import os

os.environ.setdefault(
    "DATABASE_URL",
    "sqlite:///./cinebook-ci-test.db",
)
os.environ.setdefault(
    "JWT_SECRET",
    "ci-only-test-secret-not-for-production",
)
os.environ.setdefault("RABBITMQ_PASSWORD", "ci-only-test-password")
os.environ.setdefault("RABBITMQ_USER", "cinebook")
os.environ.setdefault("RABBITMQ_HOST", "localhost")
