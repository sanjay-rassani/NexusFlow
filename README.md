# NexusFlow

A production-grade, real-time food delivery platform. Customers order food, vendors prepare it, riders deliver it — and everyone gets live updates through WebSockets without ever refreshing the page.

Built to show how real-world distributed systems work: event-driven architecture, real-time messaging, background jobs, caching, and a React frontend — all wired together.

---

## What it does

| Who | Can do |
|-----|--------|
| **Customer** | Browse vendors, place orders, track delivery live, chat with vendor/rider, receive notifications |
| **Vendor** | Manage menu & products, accept/reject orders, update order status, chat with customers |
| **Rider** | View assigned deliveries, update live GPS location, chat with customers |
| **Admin** | Manage all users, activate vendors, assign riders, monitor the system |

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend API | Django 4.2 + Django REST Framework |
| Real-time | Django Channels 4 + Daphne (ASGI/WebSocket) |
| Database | PostgreSQL 15 |
| Cache + Pub/Sub | Redis 7 |
| Background Jobs | Celery 5 + Celery Beat |
| Frontend | React 18 + TypeScript + Vite + Tailwind CSS |
| Containerization | Docker + Docker Compose |
| Reverse Proxy | Nginx |

---

## Architecture

```
Browser (React)
   │
   ├── HTTP (REST)  ──────────────────► Django REST API
   │                                        │
   └── WebSocket ──► Django Channels ◄── Redis Pub/Sub
                                            │
                              ┌─────────────┴──────────────┐
                         PostgreSQL                   Celery Workers
                       (persistent data)          (emails, background tasks)
```

**How a live order update works:**
1. Vendor taps "Accept Order" → Django saves status change to PostgreSQL
2. On transaction commit → Redis pub/sub is notified
3. Django Channels broadcasts to all connected WebSocket clients
4. Customer's browser updates the status badge **instantly** — no polling

---

## Key Features

**Authentication**
- JWT login with access + refresh tokens
- Refresh token rotation and blacklisting on logout
- Email verification and password reset

**Order lifecycle (8 states)**
```
CREATED → ACCEPTED → PREPARING → READY_FOR_PICKUP → PICKED_UP → ON_THE_WAY → DELIVERED
                   ↘ CANCELLED (from CREATED or ACCEPTED)
```
Strict state machine — invalid transitions are rejected. Orders stuck in `CREATED` for 30 min are auto-cancelled by a Celery beat task.

**Real-time (WebSocket)**
- Live order status tracking
- Live rider GPS location
- Per-user notification stream
- In-room chat between customer, vendor, and rider

**Caching (Redis)**
- Vendor list and product list responses cached (5–10 min TTL)
- Cache invalidated automatically on any write
- Rate limiting on login (10/min) and register (5/min) per IP

**Chat**
- One chat room per order (customer + vendor + rider)
- Typing indicators and read receipts over WebSocket
- Full message history via REST

**Notifications**
- Persisted to database (retrievable later)
- Pushed live via WebSocket
- Email notifications sent async via Celery

---

## Project Structure

```
NexusFlow/
├── backend/
│   ├── config/
│   │   ├── settings/
│   │   │   ├── base.py          # All shared settings
│   │   │   ├── development.py   # Dev overrides
│   │   │   └── production.py    # Prod overrides
│   │   ├── asgi.py              # ASGI entry point + WebSocket routing
│   │   ├── urls.py              # REST API routes (/api/v1/)
│   │   ├── routing.py           # WebSocket routes (/ws/)
│   │   └── celery.py            # Celery app
│   ├── apps/
│   │   ├── users/               # Auth, JWT, RBAC, email verification
│   │   ├── vendors/             # Vendor profiles, products, categories
│   │   ├── orders/              # Order lifecycle, state machine
│   │   ├── delivery/            # Rider profiles, GPS location tracking
│   │   ├── chat/                # Real-time messaging, read receipts
│   │   └── notifications/       # In-app + WebSocket + email notifications
│   ├── core/                    # Shared: permissions, pagination, exceptions, cache, rate limiter
│   └── requirements/
│       ├── base.txt
│       ├── development.txt
│       └── production.txt
├── frontend/
│   └── src/
│       ├── api/                 # Axios instance + typed API calls
│       ├── store/               # Zustand (auth + notification state)
│       ├── hooks/               # useNotificationSocket
│       ├── router/              # React Router + ProtectedRoute
│       ├── features/
│       │   ├── auth/            # Login, Register pages
│       │   ├── vendors/         # Vendor list + detail pages
│       │   └── orders/          # Order list + live order detail
│       └── components/          # Layout, NotificationBell
├── docker/
│   ├── backend/Dockerfile
│   ├── celery/Dockerfile
│   └── nginx/nginx.conf
├── docker-compose.yml           # Full production stack
├── docker-compose.dev.yml       # Dev infra only (Postgres + Redis)
└── .env.example                 # Environment variable template
```

---

## Local Setup

### Requirements

- Python 3.12+
- Node.js 20+
- PostgreSQL 15
- Redis 7
- Docker (optional, for infra)

---

### 1. Clone the repo

```bash
git clone <repo-url>
cd NexusFlow
```

---

### 2. Configure environment

```bash
cp .env.example .env
```

Open `.env` and set at minimum:

```env
SECRET_KEY=any-long-random-string
DATABASE_URL=postgres://nexusflow:nexusflow@localhost:5432/nexusflow
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/2
```

For email to actually send (optional in dev):
```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST_USER=your@gmail.com
EMAIL_HOST_PASSWORD=your-gmail-app-password
```
> Leave `EMAIL_BACKEND` as the default `console.EmailBackend` during development — emails will print to the terminal instead.

---

### 3. Start infrastructure

If you have Docker:
```bash
docker-compose -f docker-compose.dev.yml up -d
```

Or start PostgreSQL and Redis manually on their default ports (5432, 6379).

---

### 4. Set up the backend

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements/development.txt

python manage.py migrate
python manage.py create_admin   # Creates an admin user non-interactively
```

---

### 5. Start the backend server

For development (HTTP only):
```bash
python manage.py runserver
```

For WebSocket support (required for real-time features):
```bash
daphne -b 0.0.0.0 -p 8000 config.asgi:application
```

---

### 6. Start the Celery worker (separate terminal)

Required for emails and the auto-cancel periodic task:
```bash
cd backend
source venv/bin/activate
celery -A config worker --loglevel=info
```

To also run scheduled tasks (e.g. auto-cancel expired orders):
```bash
celery -A config beat --loglevel=info
```

---

### 7. Set up the frontend

```bash
cd frontend
npm install
npm run dev         # Starts at http://localhost:3000
```

The frontend auto-proxies `/api` and `/ws` to `http://localhost:8000` — no extra config needed.

---

### 8. Access the app

| What | URL |
|------|-----|
| Frontend | http://localhost:3000 |
| REST API | http://localhost:8000/api/v1/ |
| Django Admin | http://localhost:8000/admin/ |

---

## REST API Reference

### Auth — `/api/v1/auth/`

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `register/` | Create account |
| POST | `login/` | Get JWT tokens |
| POST | `token/refresh/` | Refresh access token |
| POST | `logout/` | Blacklist refresh token |
| GET / PATCH | `me/` | View / update profile |
| POST | `change-password/` | Change password |
| POST | `password-reset/` | Request password reset email |
| POST | `password-reset/confirm/` | Confirm reset with token |
| POST | `email/verify/send/` | Re-send verification email |
| POST | `email/verify/confirm/` | Confirm email with token |

### Vendors — `/api/v1/vendors/`

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `vendors/` | List all active vendors (cached) |
| GET | `vendors/{id}/` | Vendor detail + categories (cached) |
| GET | `vendors/{id}/products/` | Vendor menu (cached) |
| GET | `products/{id}/` | Single product detail |
| POST | `vendors/onboard/` | Vendor self-onboarding |
| GET / PATCH | `vendors/me/` | Vendor manages own profile |
| POST | `vendors/me/toggle-open/` | Open / close kitchen |

### Orders — `/api/v1/orders/`

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET / POST | `customer/` | List or place orders |
| GET | `customer/{id}/` | Order detail |
| POST | `customer/{id}/cancel/` | Cancel order |
| GET | `vendor/` | Vendor's incoming orders |
| POST | `vendor/{id}/accept/` | Accept order |
| POST | `vendor/{id}/reject/` | Reject order |
| POST | `vendor/{id}/prepare/` | Mark as preparing |
| POST | `vendor/{id}/ready/` | Mark as ready for pickup |
| GET | `rider/` | Rider's assigned orders |
| POST | `rider/{id}/pickup/` | Mark as picked up |
| POST | `rider/{id}/on-the-way/` | Mark as on the way |
| POST | `rider/{id}/deliver/` | Mark as delivered |
| POST | `admin/{id}/assign-rider/` | Admin assigns a rider |

### Chat — `/api/v1/chat/`

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `rooms/` | My chat rooms |
| GET | `rooms/{id}/` | Room detail + 50 recent messages |
| GET | `rooms/{id}/messages/` | Paginated message history |
| POST | `rooms/{id}/messages/send/` | Send a message (REST fallback) |
| POST | `rooms/{id}/read/` | Mark all messages as read |
| POST | `orders/{order_id}/room/` | Get or create room for an order |

### Notifications — `/api/v1/notifications/`

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | My notifications (`?is_read=true/false`) |
| GET | `unread-count/` | `{"count": N}` |
| POST | `{id}/read/` | Mark one as read |
| POST | `read-all/` | Mark all as read |

### Delivery — `/api/v1/delivery/`

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `location/update/` | Rider updates GPS (REST fallback) |

---

## WebSocket Reference

All WebSocket connections require a JWT token as a query parameter:
```
ws://localhost:8000/ws/<path>/?token=<access_token>
```

| URL | Who connects | What it does |
|-----|-------------|--------------|
| `ws/orders/{order_id}/` | Customer, Vendor, Rider | Live order status updates |
| `ws/notifications/` | Any authenticated user | Personal notification stream |
| `ws/chat/{room_id}/` | Order participants | Real-time chat |
| `ws/rider/{rider_id}/location/` | Rider (sends), Customer (receives) | Live GPS tracking |

### WebSocket message types (server → client)

```json
// Order status changed
{ "type": "ORDER_STATUS_UPDATED", "order_id": "...", "status": "ON_THE_WAY" }

// New notification
{ "type": "NOTIFICATION_PUSH", "notification": { "title": "...", "message": "..." } }

// Chat message
{ "type": "CHAT_MESSAGE", "room_id": "...", "message": { "content": "...", "sender_email": "..." } }

// Rider location
{ "type": "RIDER_LOCATION_UPDATED", "rider_id": "...", "lat": 24.86, "lng": 67.01 }
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | — | Django secret key (required) |
| `DEBUG` | `True` | Set `False` in production |
| `DATABASE_URL` | postgres://... | PostgreSQL connection string |
| `REDIS_URL` | redis://localhost:6379/0 | Redis for cache |
| `CELERY_BROKER_URL` | redis://localhost:6379/2 | Redis for Celery |
| `EMAIL_BACKEND` | console (prints to terminal) | Set to smtp for real emails |
| `EMAIL_HOST_USER` | — | SMTP username |
| `EMAIL_HOST_PASSWORD` | — | SMTP password / App password |
| `CORS_ALLOWED_ORIGINS` | http://localhost:3000 | Allowed frontend origins |
| `ORDER_EXPIRY_MINUTES` | `30` | Auto-cancel window for unaccepted orders |

---

## How roles work

Every user has one role, set at registration. The role controls what they can see and do:

- **CUSTOMER** — can only access their own orders and browse vendors
- **VENDOR** — can only manage their own profile, products, and incoming orders
- **RIDER** — can only see assigned deliveries and update location
- **ADMIN** — full access; created via `python manage.py create_admin`

JWT tokens embed the user's role. The backend checks permissions on every request.
