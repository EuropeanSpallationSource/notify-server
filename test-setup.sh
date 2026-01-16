#!/usr/bin/env bash
# Quick test script for ESS Notify Server with filter functionality

set -e

BASE_URL="http://localhost:8000"
API_BASE="${BASE_URL}/api/v2"

echo "🚀 ESS Notify Server - Development Test Script"
echo "================================================"
echo ""

# Step 1: Login with demo account
echo "📝 Step 1: Getting access token (demo/demo)..."
TOKEN_RESPONSE=$(curl -s -X POST "${API_BASE}/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=demo&password=demo")

TOKEN=$(echo $TOKEN_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null || echo "")

if [ -z "$TOKEN" ]; then
  echo "❌ Failed to get access token. Response:"
  echo "$TOKEN_RESPONSE"
  echo ""
  echo "Make sure the server is running and demo account is configured."
  exit 1
fi

echo "✅ Got access token: ${TOKEN:0:20}..."
echo ""

# Step 2: Get user profile
echo "📝 Step 2: Getting user profile..."
curl -s -X GET "${API_BASE}/users/user/profile" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
echo ""

# Step 3: Get available services
echo "📝 Step 3: Getting available services..."
SERVICES=$(curl -s -L -X GET "${API_BASE}/services/" \
  -H "Authorization: Bearer $TOKEN")
echo "$SERVICES" | python3 -m json.tool
echo ""

SERVICE_ID=$(echo "$SERVICES" | python3 -c "import sys, json; services=json.load(sys.stdin); print(services[0]['id'] if services else '')" 2>/dev/null || echo "")

if [ -z "$SERVICE_ID" ]; then
  echo "⚠️  No services found. Creating a test service..."
  # Note: Need admin token for this, using same demo token (which we made admin in .env)
  SERVICE_RESPONSE=$(curl -s -X POST "${API_BASE}/services" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"category":"demo","color":"FF5733","owner":"demo"}')
  echo "$SERVICE_RESPONSE" | python3 -m json.tool
  SERVICE_ID=$(echo "$SERVICE_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])" 2>/dev/null || echo "")
  echo ""
fi

echo "📌 Using Service ID: $SERVICE_ID"
echo ""

# Step 4: Subscribe to service
echo "📝 Step 4: Subscribing to service..."
curl -s -X PATCH "${API_BASE}/users/user/services" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "[{\"id\":\"$SERVICE_ID\",\"is_subscribed\":true}]"
echo "✅ Subscribed"
echo ""

# Step 5: Set up a filter (exclude notifications with "test")
echo "📝 Step 5: Setting up filter (exclude 'test' keyword)..."
FILTER_RESPONSE=$(curl -s -X PUT "${API_BASE}/users/user/services/${SERVICE_ID}/filter" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"exclude_keywords":"test;debug","include_keywords":""}')
echo "$FILTER_RESPONSE" | python3 -m json.tool
echo ""

# Step 6: Get filter to verify
echo "📝 Step 6: Verifying filter settings..."
curl -s -X GET "${API_BASE}/users/user/services/${SERVICE_ID}/filter" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
echo ""

echo "✅ Setup complete!"
echo ""
echo "📱 To test notifications, you can:"
echo "   1. Add a device token:"
echo "      curl -X POST '${API_BASE}/users/user/device-token' \\"
echo "        -H 'Authorization: Bearer $TOKEN' \\"
echo "        -H 'Content-Type: application/json' \\"
echo "        -d '{\"device_token\":\"YOUR_64_CHAR_IOS_TOKEN_OR_LONGER_ANDROID_TOKEN\"}'"
echo ""
echo "   2. Send a test notification (will be filtered if contains 'test'):"
echo "      curl -X POST '${API_BASE}/services/${SERVICE_ID}/notifications' \\"
echo "        -H 'Content-Type: application/json' \\"
echo "        -d '{\"title\":\"Important Alert\",\"subtitle\":\"Production issue detected\",\"url\":\"https://example.com\"}'"
echo ""
echo "   3. Send a notification that gets filtered:"
echo "      curl -X POST '${API_BASE}/services/${SERVICE_ID}/notifications' \\"
echo "        -H 'Content-Type: application/json' \\"
echo "        -d '{\"title\":\"Test Message\",\"subtitle\":\"This is just a test\",\"url\":\"\"}'"
echo ""
echo "🌐 API Documentation: ${BASE_URL}/api/v2/docs"
echo "🏠 Web UI: ${BASE_URL}/"
