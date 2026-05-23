# NexusFlow

A production-grade, real-time event-driven platform demonstrating scalable distributed systems design.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Django 4.2 + Django REST Framework |
| Real-time | Django Channels 4 + Daphne (WebSockets) |
| Database | PostgreSQL 15 |
| Cache / Pub-Sub | Redis 7 |
| Background Jobs | Celery 5 + django-celery-beat |
| Frontend | React (Phase 10) |
| Reverse Proxy | Nginx |
| Containerization | Docker + Docker Compose |

## Architecture

```
React Frontend  ←──────────────────────────────────────────────┐
     │  HTTP (REST)     │  WebSocket                           │
     ▼                  ▼                                       │
  Nginx ──────── Django (Daphne ASGI)                         │
                    │         │                                 │
           REST API │    Channels Layer ←── Redis Pub/Sub ─────┘
                    │         │
              PostgreSQL   Celery Workers
```

## Project Structure

```
NexusFlow/
├── backend/
│   ├── config/              # Django project settings + routing
│   │   ├── settings/
│   │   │   ├── base.py      # Shared settings
│   │   │   ├── development.py
│   │   │   └── production.py
│   │   ├── asgi.py          # ASGI + WebSocket routing
│   │   ├── urls.py          # Root URL config (/api/v1/)
│   │   ├── routing.py       # WebSocket URL patterns
│   │   └── celery.py        # Celery app
│   ├── apps/
│   │   ├── users/           # Auth, user model, RBAC
│   │   ├── vendors/         # Vendor + product management
│   │   ├── orders/          # Order lifecycle (8 states)
│   │   ├── delivery/        # Rider management + GPS tracking
│   │   ├── chat/            # Real-time messaging
│   │   └── notifications/   # In-app + WebSocket notifications
│   ├── core/                # Shared: pagination, permissions, exceptions
│   └── requirements/
│       ├── base.txt
│       ├── development.txt
│       └── production.txt
├── docker/
│   ├── backend/Dockerfile
│   ├── celery/Dockerfile
│   └── nginx/nginx.conf
├── docker-compose.yml       # Production
├── docker-compose.dev.yml   # Dev (infra only)
└── .env.example
```

## Quick Start (Development)

### 1. Clone & configure environment

```bash
git clone <repo>
cd NexusFlow
cp .env.example .env
# Edit .env with your values
```

### 2. Start infrastructure (PostgreSQL + Redis)

```bash
docker-compose -f docker-compose.dev.yml up -d
```

### 3. Install Python dependencies

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements/development.txt
```

### 4. Run migrations & start server

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

### 5. Start Celery worker (separate terminal)

```bash
celery -A config worker --loglevel=info
```

### 6. Access

- API: http://localhost:8000/api/v1/
- Admin: http://localhost:8000/admin/
- Redis GUI: http://localhost:8081/

## API Endpoints (Phase 1)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/register/` | User registration |
| POST | `/api/v1/auth/login/` | Login → JWT tokens |
| POST | `/api/v1/auth/token/refresh/` | Refresh access token |
| GET/PATCH | `/api/v1/auth/me/` | Current user profile |
| POST | `/api/v1/auth/change-password/` | Change password |

## Development Phases

- [x] **Phase 1** — Project Foundation (current)
- [x] **Phase 2** — Authentication (JWT, RBAC, email verification)
- [x] **Phase 3** — Vendor & Product Management
- [x] **Phase 4** — Order Management System
- [x] **Phase 5** — WebSocket Integration (Django Channels)
- [x] **Phase 6** — Redis Caching Layer
- [x] **Phase 7** — Celery Background Jobs
- [x] **Phase 8** — Chat System
- [ ] **Phase 9** — Notification System
- [ ] **Phase 10** — React Frontend
- [ ] **Phase 11** — Docker + Nginx Production Deploy
- [ ] **Phase 12** — Monitoring & Analytics
