# CineBook

CineBook is an independent movie ticket booking application being built as a full-stack and DevOps portfolio project.

## Day 1 foundation

- Frontend: React, TypeScript, and Vite
- Backend: FastAPI and SQLAlchemy
- Database: PostgreSQL
- Local environment: Docker Compose

## Run locally

1. Install Docker Desktop and make sure its engine is running.
2. Keep the generated `.env` file private.
3. From the project root, run:

   ```powershell
   docker compose config
   docker compose up --build -d
   docker compose ps
   ```

4. Open the links below.

## Local URLs

- Frontend: http://localhost:5173
- API documentation: http://localhost:8000/docs
- Health endpoint: http://localhost:8000/api/health
- Readiness endpoint: http://localhost:8000/api/ready
- Movie catalogue: http://localhost:8000/api/movies

## Useful commands

```powershell
docker compose ps
docker compose logs --tail 100 db backend frontend
docker compose down
```

`docker compose down` stops and removes the containers but preserves the named PostgreSQL data volume. Do not use `docker compose down -v` unless you intentionally want to delete that volume.

## Security notes

- Never commit `.env` or real credentials.
- Payment integration will use sandbox/test mode only.
- This development starter is not yet production-ready.
