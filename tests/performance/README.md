# Load Tests

Locust-based load tests for the notify-server API. Three simulated user types:

| User Type             | Weight    | Behaviour                          |
|-----------------------|-----------|------------------------------------|
| NotificationReader    | 6         | Browses services and notifications |
| SubscriptionManager   | 1         | Toggles service subscriptions      |
| NotificationPublisher | 1         | Creates notifications              |

These tests are **not run in CI** and are intended for manual performance testing.

## Quick start (Docker)

From the repository root:

```bash
# Start postgres and web server
docker compose -f docker-compose.yml -f docker-compose.test.yml up --build -d postgres web

# Seed the database (runs migrations + creates test data)
docker compose -f docker-compose.yml -f docker-compose.test.yml run --rm seed

# Start Locust
docker compose -f docker-compose.yml -f docker-compose.test.yml up locust
```

Open http://localhost:8089 for the Locust web UI.

To stop everything:

```bash
docker compose -f docker-compose.yml -f docker-compose.test.yml down
# Add -v to also remove the database volume
```

## Configuration

- Enable SQL query logging: uncomment `SQLALCHEMY_DEBUG: "true"` in `docker-compose.test.yml` (do not use during load tests — it slows down workers significantly)
- Disable notification creation: set `fixed_count = 0` on `NotificationPublisher` in `locustfile.py`
- Adjust user weights: modify `weight` on each user class

## Files

- `locustfile.py` -- Locust user definitions and tasks
- `../../scripts/seed_db.py` -- Database seeder (generates test data and tokens)
- `../../docker-compose.test.yml` -:- Docker compose overlay for the test environment
