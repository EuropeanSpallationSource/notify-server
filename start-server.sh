#!/bin/bash
# Start the ESS Notify Server in development mode

cd "$(dirname "$0")"

# Activate virtual environment
source .venv/bin/activate

# Start server with auto-reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
