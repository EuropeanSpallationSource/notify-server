# ESS Notify Server

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)
[![sonarqube](https://sonarqube.esss.lu.se/api/project_badges/measure?project=ess-notify-server&metric=alert_status)](https://sonarqube.esss.lu.se/dashboard?id=ess-notify-server)
[![pipeline](https://gitlab.esss.lu.se/ics-software/ess-notify-server/badges/master/pipeline.svg)](https://gitlab.esss.lu.se/ics-software/ess-notify-server/pipelines)
[![coverage](https://gitlab.esss.lu.se/ics-software/ess-notify-server/badges/master/coverage.svg)](https://gitlab.esss.lu.se/ics-software/ess-notify-server/pipelines)

Python web server to send notifications.

ess-notify is built with [FastAPI].

## Configuration

All variables defined in `app/settings.py` can be overridden by exporting environment variables.
This can be achieved by setting the variables in a `.env` file:

```bash
$ cat .env
APNS_KEY_ID=my-key
TEAM_ID=my-team
ADMIN_USERS=username
FIREBASE_PROJECT_ID=my-project
GOOGLE_APPLICATION_CREDENTIALS=my-project.json
```

Note that as `APNS_AUTH_KEY` shall contain a private key (on multiple lines) it's not easy to define
it in the `.env` file.
The dummy default key can be overridden by creating a file and exporting its content:

```bash
export APNS_AUTH_KEY="$(cat .apns_auth_key)"
```

To be able to login, at least the following variables shall be overwritten:

- LDAP_HOST
- LDAP_USER_DN

### OpenID Connect with Automatic Realm Discovery for Mobile Apps

The implementation provides two OIDC-related endpoints used by mobile clients:

- GET /api/v1/realm-discovery/?type=<real|demo> — discover which realm and
  client to use for a given app "type".
- POST /api/v1/open_id_connect?realm=<realm> — exchange an OIDC authorization
  code (server performs token/userinfo calls, validates id_token and issues a
  local access token).

Exact environment variables used by the implementation

- `OIDC_ENABLED` (bool) — enable OIDC features
- `OIDC_BASE_URL` (string) — base Keycloak URL (e.g. https://keycloak.example.org/auth)
- `OIDC_DEFAULT_REALM` (string) — default realm used
- `OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET` — default client credentials
- `OIDC_SCOPE` — scope used when requesting userinfo
- `OIDC_DEMO_REALM`, `OIDC_DEMO_CLIENT_ID`, `OIDC_DEMO_CLIENT_SECRET` — demo realm/client values

Realm discovery (mobile client)

Request
```http
GET /api/v1/realm-discovery/?type=real
```

Response (implemented schema)
```json
{
  "realm": "company-realm",
  "authorization_endpoint": "https://keycloak.example.org/auth/realms/company-realm/protocol/openid-connect/auth",
  "token_endpoint": "https://keycloak.example.org/auth/realms/company-realm/protocol/openid-connect/token",
  "client_id": "notify",
  "type": "real"
}
```

Notes
- The endpoint expects the query parameter `type` (alias for the internal
  `RealmType` enum). The implementation maps types to realms using
  `deps.REALM_BY_TYPE` and exposes client IDs from `deps.CLIENT_BY_REALM`.
- The discovery response provides `authorization_endpoint` and `token_endpoint`
  (not a single discovery URI), and the `client_id` the mobile app should
  include in the initial authorization request.

OpenID Connect token exchange (mobile -> server)

After the mobile app completes the OIDC authorization code flow (using the
`client_id` provided and PKCE), the app should POST the authorization code to
the server which will perform the token/userinfo exchange and create a local
access token for the app.

Request
```http
POST /api/v1/open_id_connect?realm=company-realm
Content-Type: application/json

{
  "code": "authorization_code",
  "code_verifier": "pkce_verifier",
  "client_id": "notify",
  "redirect_uri": "app://callback"
}
```

Behavior
- The server posts the code to the realm's token endpoint and validates the
  returned id_token (using the realm's JWKS).
- Client secrets for token exchanges are looked up server-side from
  `deps.CLIENT_BY_REALM_TYPE`; mobile apps MUST NOT embed client secrets.


## Development

### Virtual environment

Python >= 3.11 is required.
Create a virtual environment and install the requirements:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e ".[tests]"
```

When using sqlite, it's not possible to run `alembic` for database migration
(sqlite doesn't support to drop a column in a table).
Create the database from scratch using:

```bash
notify-server create-db
```

This is for development only. In production, use postgres and alembic.

Run the application:

```bash
uvicorn --reload app.main:app
```

Go to <http://127.0.0.1:8000/api/v1/docs> and <http://127.0.0.1:8000/api/v2/docs> to browse the API depending on the version.

Using `uvicorn` with the `--reload` parameter will automatically restart the application when a file changes.
Note that the logging configuration assumes that the application is run with gunicorn.
To do so, run:

```bash
gunicorn -w 2 -k uvicorn.workers.UvicornWorker --log-level info app.main:app
```

This will run the application using [SQLite].
The application uses [PostgreSQL] in production. This can be done by updating the `SQLALCHEMY_DATABASE_URL` variable to point to a postgres database. Using [docker], as detailed below, is recommended.

### Docker

The provided `docker-compose.yml` file allows you to easily start the application with [PostgreSQL].

First time:

- Build the docker image: `docker-compose build`
- Start postgres: `docker-compose up -d postgres`
- Run alembic to create the database: `docker-compose run --rm web alembic upgrade head`
- Start the application: `docker-compose up web`

Those commands only need to be run the first time. The docker image shall be rebuilt only if requirements change.
After that, start the application by running:

```bash
docker-compose up -d postgres
docker-compose up web
```

### Testing

[pytest] is used for testing.
Create and activate a virtual environment as detailed above.

```bash
pytest -v tests
```

## Deployment

Deployment is performed with Ansible and Docker.
When pushing to the master branch, the application is automatically deployed to the test server <https://notify-test.esss.lu.se>.

To deploy to production, tag the branch (`git tag -a <version>`) and push that tag. At the end of the gitlab-ci pipeline, a manual job is created and shall be triggered manually.

### Maintenance

To remove old notifications, you can run the `notify-server delete-notifications` command.
You can run it inside the ess_notify_web container using the crontab:

```bash
/usr/bin/docker exec ess_notify_web notify-server delete-notifications
```

By default, only the last 30 days are kept. You can change that value with the `--days`option.

[fastapi]: https://fastapi.tiangolo.com
[pytest]: https://docs.pytest.org/en/stable/
[sqlite]: https://www.sqlite.org/index.html
[postgresql]: https://www.postgresql.org
[docker]: https://docs.docker.com
