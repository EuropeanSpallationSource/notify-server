#!/bin/bash
# Clean up notifications older than 7 days
# Run this script daily via cron

cd "$(dirname "$0")"
source .venv/bin/activate

echo "🧹 Cleaning up notifications older than 7 days..."
notify-server delete-notifications --days 7

echo "✅ Cleanup complete"
