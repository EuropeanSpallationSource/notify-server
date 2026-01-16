#!/bin/bash
# Test notification filtering functionality

set -e

BASE_URL="http://localhost:8000/api/v2"
SERVICE_ID="d3f4e5a6-b7c8-d9e0-f1a2-b3c4d5e6f7a8"

echo "🔐 Logging in..."
LOGIN_RESPONSE=$(curl -s -X POST $BASE_URL/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=demo&password=demo")

TOKEN=$(echo $LOGIN_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
echo "✅ Token received"

echo ""
echo "📱 Registering device token..."
curl -s -X POST $BASE_URL/users/user/device-token \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"device_token": "fake-ios-token-for-testing-1234567890abcdef"}' > /dev/null
echo "✅ Device registered"

echo ""
echo "🎯 Current filter settings:"
curl -s -X GET "$BASE_URL/users/user/services/$SERVICE_ID/filter" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

echo ""
echo "📨 Creating notifications (watch server logs)..."
echo ""

# This should be SENT (no "test" keyword)
echo "  1. Production Alert (WILL SEND) ✓"
curl -s -X POST "$BASE_URL/services/$SERVICE_ID/notifications" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title": "Production Alert", "subtitle": "Critical issue detected"}' > /dev/null

# This should be FILTERED (has "test" keyword)
echo "  2. Test Notification (WILL BE FILTERED) ✗"
curl -s -X POST "$BASE_URL/services/$SERVICE_ID/notifications" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title": "Test Notification", "subtitle": "Just testing the system"}' > /dev/null

# This should be FILTERED (has "debug" keyword)
echo "  3. Debug Mode Enabled (WILL BE FILTERED) ✗"
curl -s -X POST "$BASE_URL/services/$SERVICE_ID/notifications" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title": "Debug Mode Enabled", "subtitle": "Verbose logging active"}' > /dev/null

# This should be SENT (no excluded keywords)
echo "  4. Deployment Complete (WILL SEND) ✓"
curl -s -X POST "$BASE_URL/services/$SERVICE_ID/notifications" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title": "Deployment Complete", "subtitle": "Version 2.0 is live"}' > /dev/null

echo ""
echo "✅ Test notifications created!"
echo ""
echo "📊 Check your server logs to see:"
echo "   - Filtered notifications (excluded by keyword)"
echo "   - Sent notifications (attempted push delivery)"
echo ""
echo "💡 Modify filters with:"
echo "   curl -X PUT \"$BASE_URL/users/user/services/$SERVICE_ID/filter\" \\"
echo "     -H \"Authorization: Bearer \$TOKEN\" \\"
echo "     -H \"Content-Type: application/json\" \\"
echo "     -d '{\"include_keywords\": \"alert\", \"exclude_keywords\": \"\"}'"
