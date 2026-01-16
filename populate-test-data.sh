#!/usr/bin/env bash
# Populate database with test data for client testing

set -e

echo "🎲 Populating database with test data..."
echo ""

# Get auth token
echo "🔐 Logging in as demo user..."
TOKEN=$(curl -s -X POST 'http://localhost:8000/api/v2/login' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=demo&password=demo' | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null)

if [ -z "$TOKEN" ]; then
  echo "❌ Failed to login. Make sure the server is running."
  exit 1
fi

echo "✅ Logged in"
echo ""

# Get service ID
SERVICE_ID=$(curl -s -L "http://localhost:8000/api/v2/services/" \
  -H "Authorization: Bearer $TOKEN" | python3 -c "import sys, json; print(json.load(sys.stdin)[0]['id'])" 2>/dev/null)

echo "📌 Using service: $SERVICE_ID"
echo ""

# Subscribe to service
echo "📝 Subscribing to service..."
curl -s -X PATCH "http://localhost:8000/api/v2/users/user/services" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "[{\"id\":\"$SERVICE_ID\",\"is_subscribed\":true}]" > /dev/null
echo "✅ Subscribed"
echo ""

# Create sample notifications
echo "📨 Creating sample notifications..."

# Notification 1: Important production alert
curl -s -X POST "http://localhost:8000/api/v2/services/$SERVICE_ID/notifications" \
  -H "Content-Type: application/json" \
  -d '{
    "title":"Production Alert",
    "subtitle":"High CPU usage detected on server prod-web-01",
    "url":"https://monitoring.example.com/alerts/1234"
  }' > /dev/null
echo "  ✓ Created: Production Alert"

# Notification 2: Deployment notification
curl -s -X POST "http://localhost:8000/api/v2/services/$SERVICE_ID/notifications" \
  -H "Content-Type: application/json" \
  -d '{
    "title":"Deployment Complete",
    "subtitle":"Version 2.3.1 successfully deployed to production",
    "url":"https://ci.example.com/deploy/5678"
  }' > /dev/null
echo "  ✓ Created: Deployment Complete"

# Notification 3: Database backup success
curl -s -X POST "http://localhost:8000/api/v2/services/$SERVICE_ID/notifications" \
  -H "Content-Type: application/json" \
  -d '{
    "title":"Backup Successful",
    "subtitle":"Daily database backup completed - 2.4 GB",
    "url":"https://backup.example.com/jobs/9012"
  }' > /dev/null
echo "  ✓ Created: Backup Successful"

# Notification 4: Critical error
curl -s -X POST "http://localhost:8000/api/v2/services/$SERVICE_ID/notifications" \
  -H "Content-Type: application/json" \
  -d '{
    "title":"Critical Error",
    "subtitle":"Payment gateway connection failed - immediate action required",
    "url":"https://status.example.com/incident/3456"
  }' > /dev/null
echo "  ✓ Created: Critical Error"

# Notification 5: Security alert
curl -s -X POST "http://localhost:8000/api/v2/services/$SERVICE_ID/notifications" \
  -H "Content-Type: application/json" \
  -d '{
    "title":"Security Alert",
    "subtitle":"Multiple failed login attempts detected from IP 192.168.1.100",
    "url":"https://security.example.com/events/7890"
  }' > /dev/null
echo "  ✓ Created: Security Alert"

# Notification 6: Scheduled maintenance
curl -s -X POST "http://localhost:8000/api/v2/services/$SERVICE_ID/notifications" \
  -H "Content-Type: application/json" \
  -d '{
    "title":"Maintenance Scheduled",
    "subtitle":"Database maintenance window: Dec 15, 2025 02:00-04:00 UTC",
    "url":"https://calendar.example.com/event/maint-2025-12"
  }' > /dev/null
echo "  ✓ Created: Maintenance Scheduled"

# Notification 7: Test notification (will be filtered if exclude_keywords contains "test")
curl -s -X POST "http://localhost:8000/api/v2/services/$SERVICE_ID/notifications" \
  -H "Content-Type: application/json" \
  -d '{
    "title":"Test Notification",
    "subtitle":"This is just a test - please ignore",
    "url":""
  }' > /dev/null
echo "  ✓ Created: Test Notification (filtered by default)"

# Notification 8: Performance warning
curl -s -X POST "http://localhost:8000/api/v2/services/$SERVICE_ID/notifications" \
  -H "Content-Type: application/json" \
  -d '{
    "title":"Performance Warning",
    "subtitle":"API response time increased to 2.5s (threshold: 1.0s)",
    "url":"https://metrics.example.com/dashboard/api"
  }' > /dev/null
echo "  ✓ Created: Performance Warning"

# Notification 9: New user signup
curl -s -X POST "http://localhost:8000/api/v2/services/$SERVICE_ID/notifications" \
  -H "Content-Type: application/json" \
  -d '{
    "title":"New User Signup",
    "subtitle":"Premium account created: user@example.com",
    "url":"https://admin.example.com/users/12345"
  }' > /dev/null
echo "  ✓ Created: New User Signup"

# Notification 10: Storage capacity warning
curl -s -X POST "http://localhost:8000/api/v2/services/$SERVICE_ID/notifications" \
  -H "Content-Type: application/json" \
  -d '{
    "title":"Storage Warning",
    "subtitle":"Disk usage at 85% on /data partition",
    "url":"https://monitoring.example.com/storage"
  }' > /dev/null
echo "  ✓ Created: Storage Warning"

echo ""
echo "✅ Created 10 sample notifications!"
echo ""

# Show notification count
NOTIFICATION_COUNT=$(curl -s -L "http://localhost:8000/api/v2/users/user/notifications?limit=100" \
  -H "Authorization: Bearer $TOKEN" | python3 -c "import sys, json; print(len(json.load(sys.stdin)))" 2>/dev/null)

echo "📊 Summary:"
echo "   • Total notifications: $NOTIFICATION_COUNT"
echo "   • Service: demo"
echo "   • Filter active: excludes 'test' and 'debug'"
echo ""
echo "🎯 Next steps:"
echo "   1. View in web UI: http://localhost:8000/"
echo "   2. Test with your mobile client"
echo "   3. Add a device token to receive push notifications"
echo ""
echo "💡 To add your device token:"
echo "   curl -X POST 'http://localhost:8000/api/v2/users/user/device-token' \\"
echo "     -H 'Authorization: Bearer $TOKEN' \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"device_token\":\"YOUR_DEVICE_TOKEN_HERE\"}'"
echo ""
