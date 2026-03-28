# Scripts

## seed_db.py

Seeds the database with test users, services, subscriptions, and notifications.
Writes JWT tokens to a JSON file for use by load tests or manual API testing.

### Usage (Docker)

Runs automatically as part of the test compose stack:

```bash
docker compose -f docker-compose.yml -f docker-compose.test.yml run --rm seed
```

### Usage (standalone)

```bash
python scripts/seed_db.py \
  --db-url "sqlite:///./test.db" \
  --clear \
  --num-users 50 \
  --num-services 10 \
  --num-notifications 500 \
  --output-tokens scripts/test_tokens.json
```

### Options

| Flag                  | Default                       | Description                        |
|-----------------------|-------------------------------|------------------------------------|
| `--db-url`            | `SQLALCHEMY_DATABASE_URL` env | SQLAlchemy connection string       |
| `--clear`             | off                           | Drop existing data before seeding  |
| `--num-users`         | 50                            | Number of test users to create     |
| `--num-services`      | 10                            | Number of services to create       |
| `--num-notifications` | 500                           | Number of notifications to create  |
| `--output-tokens`     | `scripts/test_tokens.json`    | Path for the generated tokens file |

### Output

The generated tokens file contains:

- `admin_token` -- JWT for the admin user (`testuser_001`)
- `user_tokens` -- list of JWTs for all generated users
- `users` -- list of `{username, token}` objects
- `service_ids` -- list of UUID strings for created services

This file is gitignored and regenerated on each run.
