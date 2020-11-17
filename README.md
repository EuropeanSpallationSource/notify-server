# ESS Notify Server

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)
[![sonarqube](https://sonarqube.esss.lu.se/api/project_badges/measure?project=ess-notify-server&metric=alert_status)](https://sonarqube.esss.lu.se/dashboard?id=ess-notify-server)
[![pipeline](https://gitlab.esss.lu.se/ics-software/ess-notify-server/badges/master/pipeline.svg)](https://gitlab.esss.lu.se/ics-software/ess-notify-server/pipelines)
[![coverage](https://gitlab.esss.lu.se/ics-software/ess-notify-server/badges/master/coverage.svg)](https://gitlab.esss.lu.se/ics-software/ess-notify-server/pipelines)

Python web server to send notifications.

ess-notify is built with [FastAPI].

## Quick start

Create a virtual environment and install the requirements:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

Run the database migrations:

```bash
alembic upgrade head
```

Run the application:

```bash
uvicorn --reload app.main:app
```

Go to <http://127.0.0.1:8000/docs> to browse the API.

[fastapi]: https://fastapi.tiangolo.com
