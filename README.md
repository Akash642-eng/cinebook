# CineBook

CineBook is a movie ticket booking application built as a DevOps learning project. This repository contains the application, container configuration, and local development setup.

## Technology stack

- Frontend: React and TypeScript
- Backend: FastAPI and Python
- Database: PostgreSQL
- Messaging: RabbitMQ
- Containers: Docker and Docker Compose
- Web server: NGINX
- Background processing: Worker service

## First-time setup

### Prerequisites

Install Docker Desktop and ensure its Docker engine is running. Git and Windows PowerShell are also recommended.

### 1. Open the project directory

```powershell
Set-Location "$HOME\Projects\cinebook"
```

### 2. Create your local environment file

```powershell
Copy-Item .env.example .env
notepad .env
```

Set strong, unique local values for `POSTGRES_PASSWORD`, `JWT_SECRET`, and `RABBITMQ_PASSWORD`. Keep the values private. Do not commit `.env` to Git.

If `.env` already exists, do not overwrite it with the example file.

### 3. Validate and start the application

```powershell
docker compose config --quiet
docker compose up --build -d
docker compose ps
```

Wait for the services to start and their health checks to pass.

## Local URLs

| Service | URL |
|---|---|
| CineBook frontend | http://localhost:5173/ |
| Backend health | http://localhost:8000/api/health |
| Backend readiness | http://localhost:8000/api/ready |
| API documentation | http://localhost:8000/docs |
| RabbitMQ management | http://localhost:15672/ |

Use the RabbitMQ credentials configured in your local environment and Compose configuration.

## Verification

Run these commands from the project directory:

```powershell
docker compose ps
Invoke-RestMethod http://localhost:8000/api/health
Invoke-RestMethod http://localhost:8000/api/ready
(Invoke-RestMethod http://localhost:8000/api/movies).Count
(Invoke-WebRequest http://localhost:5173/).StatusCode
```

Expected results for a correctly initialized environment:

- Health endpoint reports a healthy service.
- Readiness endpoint succeeds when its required dependencies are available.
- The movie endpoint returns the catalogue; the current development dataset contains four movies.
- The frontend returns HTTP status `200`.

If a check fails, inspect the service logs before making configuration changes.

## Logs and shutdown

View logs for all services:

```powershell
docker compose logs --tail 100
```

View logs for an individual service:

```powershell
docker compose logs --tail 100 backend
docker compose logs --tail 100 db
docker compose logs --tail 100 frontend
docker compose logs --tail 100 rabbitmq
docker compose logs --tail 100 worker
```

Stop the application without deleting persistent volumes:

```powershell
docker compose down
```

Start it again:

```powershell
docker compose up -d
```

**Important:** `docker compose down -v` removes Compose-managed volumes and can delete local database and message-broker data. Do not use it on your normal development environment unless you intentionally want to delete that data.

## Security

- Keep `.env` private and out of version control.
- Never put real passwords, API keys, tokens, or production secrets in source code.
- Use unique local development credentials.
- Do not expose database or management ports publicly.
- Local development settings are not a substitute for production security hardening.
