#!/bin/bash
# Set test filter for demo user

set -e

BASE_URL="http://localhost:8000/api/v2"
SERVICE_ID="d3f4e5a6-b7c8-d9e0-f1a2-b3c4d5e6f7a8"

echo "🔐 Logging in..."
LOGIN_RESPONSE=$(curl -s -X POST $BASE_URL/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=demo&password=demo")

TOKEN=$(echo $LOGIN_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

echo "🎯 Setting filter: exclude_keywords='test;debug'"
curl -X PUT "$BASE_URL/users/user/services/$SERVICE_ID/filter" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"include_keywords": "", "exclude_keywords": "test;debug"}'

echo ""
echo "✅ Filter set! Your app should now filter out notifications with 'test' or 'debug'"
