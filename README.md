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

Refer to the default values defined in the [Ansible role](https://gitlab.esss.lu.se/ics-ansible-galaxy/ics-ans-role-ess-notify-server/-/blob/master/defaults/main.yml)
and in the [ess_notify_servers](https://csentry.esss.lu.se/network/groups/view/ess_notify_servers) group in CSEntry.

## Development

### Virtual environment

Python >= 3.6 is required.
Create a virtual environment and install the requirements:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .[tests]
```

Run the database migrations:

```bash
alembic upgrade head
```

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

[fastapi]: https://fastapi.tiangolo.com
[pytest]: https://docs.pytest.org/en/stable/
[sqlite]: https://www.sqlite.org/index.html
[postgresql]: https://www.postgresql.org
[docker]: https://docs.docker.com
