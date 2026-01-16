#!/bin/bash
# Restart the ESS Notify Server

cd "$(dirname "$0")"

echo "🔄 Restarting server..."

# Stop existing server
./stop-server.sh

# Wait a moment
sleep 1

# Start server in background
./start-server.sh &

echo "✅ Server restarting..."
echo "   Check logs with: tail -f nohup.out"
