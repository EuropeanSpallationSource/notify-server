#!/bin/bash
# Stop the ESS Notify Server

echo "🛑 Stopping server..."

# Find and kill uvicorn processes
pkill -f "uvicorn app.main:app" || echo "No server process found"

echo "✅ Server stopped"
