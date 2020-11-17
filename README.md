# ESS Notify Server

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
