#!/bin/bash
# Subscribe demo user to the demo service

set -e

BASE_URL="http://localhost:8000/api/v2"
SERVICE_ID="d3f4e5a6-b7c8-d9e0-f1a2-b3c4d5e6f7a8"

echo "🔐 Logging in..."
LOGIN_RESPONSE=$(curl -s -X POST $BASE_URL/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=demo&password=demo")

TOKEN=$(echo $LOGIN_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

echo "📝 Subscribing to Demo Service..."
curl -s -X PATCH $BASE_URL/users/user/services \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "[{\"id\": \"$SERVICE_ID\", \"is_subscribed\": true}]"

echo ""
echo "✅ Subscribed! Refresh http://localhost:8000/notifications to see notifications."
