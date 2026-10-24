from time import perf_counter

from fastapi import FastAPI, Request
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Histogram,
    generate_latest,
)
from starlette.responses import Response


HTTP_REQUESTS = Counter(
    "cinebook_http_requests_total",
    "Total HTTP requests handled by CineBook.",
    ("method", "route", "status_code"),
)

HTTP_REQUEST_DURATION = Histogram(
    "cinebook_http_request_duration_seconds",
    "HTTP request duration in seconds.",
    ("method", "route"),
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)


def install_metrics(app: FastAPI) -> None:
    @app.middleware("http")
    async def collect_http_metrics(request: Request, call_next):
        if request.url.path == "/metrics":
            return await call_next(request)

        started_at = perf_counter()
        status_code = 500

        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            route = request.scope.get("route")
            route_path = getattr(route, "path", "unmatched")

            HTTP_REQUESTS.labels(
                method=request.method,
                route=route_path,
                status_code=str(status_code),
            ).inc()

            HTTP_REQUEST_DURATION.labels(
                method=request.method,
                route=route_path,
            ).observe(perf_counter() - started_at)

    @app.get("/metrics", include_in_schema=False)
    def expose_metrics() -> Response:
        return Response(
            content=generate_latest(),
            media_type=CONTENT_TYPE_LATEST,
        )
