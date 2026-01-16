# ESS Notify Server - AI Coding Agent Instructions

## Architecture Overview

This is a **FastAPI-based notification server** that sends push notifications to iOS (via APNs) and Android (via Firebase) devices. The app serves both:
- **Web UI** (HTML with HTMX) for notification management at root `/`
- **Versioned REST APIs** mounted at `/api/v1` and `/api/v2` using custom vendored `fastapi_versioning`

### Key Components
- **Authentication**: Dual mode - LDAP/URL for API (backward compatible) + OIDC for web login
- **Database**: SQLAlchemy ORM with SQLite (dev) / PostgreSQL (prod), Alembic for migrations
- **Push delivery**: Async HTTP/2 to APNs & Firebase, with configurable concurrency (`NB_PARALLEL_PUSH`)
- **Multi-tenancy**: Services organize notifications; users subscribe to services

## Critical Patterns

### Application Structure (main.py)
Two separate FastAPI apps are created:
1. `app` - Main app for HTML views with session middleware
2. `original_api` - API-only app that gets versioned, then mounted at `/api`

The `VersionedFastAPI` wrapper from `app/_vendor/fastapi_versioning/` creates `/v1`, `/v2` prefixes automatically. **Never modify vendored code** - see `LICENSE.fastapi_versioning` for attribution.

### Database Session Management
Use dependency injection pattern throughout:
```python
from app import deps
db: Session = Depends(deps.get_db)
```
Sessions are auto-closed in `finally` block. For background tasks in `utils.py`, manually create `SessionLocal()` and close explicitly.

### Authentication Layers
- **API routes**: `Depends(deps.get_current_user)` validates JWT bearer tokens
- **Web routes**: `Depends(deps.get_current_user_from_session)` checks session cookies
- **Admin-only**: Use `Depends(deps.get_current_admin_user)` for service management
- **Special case**: Swagger UI injects `token="swagger-ui"` to reuse web session for API testing

### Custom SQLAlchemy Types
Two critical type decorators in `models.py`:
- `TZDateTime`: Stores timezone-aware datetimes as UTC, handles naive/aware conversions
- `GUID`: Cross-database UUID support (native PostgreSQL UUID, CHAR(32) for SQLite)

### Notification Flow
1. Create notification via API/web → stores in DB
2. Background task calls `utils.send_notification(notification_id)`
3. Async gathering sends to all subscribed users' device tokens
4. Separate `ios.send_push()` and `firebase.send_push()` handle platform-specific payloads
5. Failed tokens trigger automatic cleanup via `crud.remove_user_device_token()`

## Development Workflow

### Local Setup
```bash
# Dev with SQLite (no alembic support)
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && pip install -e .[tests]
notify-server create-db  # Creates fresh SQLite DB

# Dev with Docker + PostgreSQL (production-like)
docker-compose build
docker-compose up -d postgres
docker-compose run --rm web alembic upgrade head
docker-compose up web
```

**Important**: SQLite cannot drop columns, so alembic migrations fail. Use `notify-server create-db` to recreate schema in dev.

### Running the App
- **Uvicorn (auto-reload)**: `uvicorn --reload app.main:app` - logging config assumes gunicorn, output may differ
- **Gunicorn (production-like)**: `gunicorn -w 2 -k uvicorn.workers.UvicornWorker --log-level info app.main:app`

### Testing
```bash
pytest -v tests
```
- Test fixtures in `tests/conftest.py` override settings via `environ` before imports
- Factories use `pytest-factoryboy` with SQLAlchemy persistence (see `tests/factories.py`)
- `respx` mocks HTTP calls to APNs/Firebase
- Always check `conftest.py` env overrides when adding settings

### Configuration
All settings in `app/settings.py` read from environment or `.env` file. Key variables:
- `AUTHENTICATION_METHOD`: `"ldap"` or `"url"` (API auth, coexists with OIDC)
- `OIDC_ENABLED`: `True` enables web login via OpenID Connect
- `SQLALCHEMY_DATABASE_URL`: Switch between SQLite/PostgreSQL
- `ADMIN_USERS`: Comma-separated usernames for admin privileges

**Multi-line secrets**: Export from file: `export APNS_AUTH_KEY="$(cat .apns_auth_key)"`

### Database Migrations
Production uses PostgreSQL + Alembic:
```bash
# Create migration after model changes
alembic revision --autogenerate -m "description"
# Apply in Docker
docker-compose run --rm web alembic upgrade head
```

### CLI Commands
The `notify-server` CLI (Typer-based) in `app/command.py`:
- `create-db`: Bootstrap SQLite schema (dev only)
- `delete-notifications --days 30`: Prune old notifications (run via cron)
- `delete-user <username>`: Remove user and tokens

## Project Conventions

### Code Style
- **Formatter**: Black (enforced via pre-commit)
- **Import order**: Standard library → third-party → local (. imports)
- **Logging**: Use `from fastapi.logger import logger`, assumes gunicorn setup

### Model-Schema Separation
- `models.py`: SQLAlchemy ORM classes (`Base` subclasses)
- `schemas.py`: Pydantic models for API validation/serialization
- `crud.py`: All DB operations isolated here, never raw queries in routes

### API Versioning Strategy
- New endpoints get `@version(major=2)` decorator from vendored `fastapi_versioning`
- Default version is `(1, 0)`, routes without decorator inherit it
- Both `/api/v1/docs` and `/api/v2/docs` auto-generate OpenAPI specs

### Error Handling
- Routes raise `HTTPException` with appropriate status codes
- Views use custom exception handlers in `views/exceptions.py` for HTML error pages
- External API failures (APNs/Firebase) log warnings but don't interrupt flow

## Deployment Notes

- **Docker**: Multi-stage build compiles dependencies (psycopg2), final image runs as non-root `csi:csi` user
- **Production**: Ansible-based deployment to `notify-test.esss.lu.se` (master) and production (tagged releases)
- **Monitoring**: Sentry integration via `SENTRY_DSN` setting wraps app with `SentryAsgiMiddleware`
- **Session security**: `https_only=True` on SessionMiddleware, requires HTTPS in production

## Common Tasks

**Adding a new notification field:**
1. Update `models.Notification` with SQLAlchemy column
2. Add field to `schemas.Notification` Pydantic model
3. Generate alembic migration: `alembic revision --autogenerate -m "add field"`
4. Update `to_apn_payload()` / `to_android_payload()` methods if needed

**Adding admin-only endpoints:**
```python
current_user: models.User = Depends(deps.get_current_admin_user)
```

**Testing authentication:**
Override `ADMIN_USERS` in `conftest.py` environ setup, use factories to create test users

**Debugging push failures:**
Check logs for "Send notification to..." entries. Token cleanup happens automatically when APNs/Firebase return unregistered errors (see `ios.py:60-69`, `firebase.py:60-70`)
