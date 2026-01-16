#!/bin/bash
# Modify notification filters

BASE_URL="http://localhost:8000/api/v2"
SERVICE_ID="d3f4e5a6-b7c8-d9e0-f1a2-b3c4d5e6f7a8"

echo "🔐 Logging in..."
TOKEN=$(curl -s -X POST $BASE_URL/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=demo&password=demo" | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

echo ""
echo "📊 Current active filter:"
CURRENT=$(curl -s "$BASE_URL/users/user/services/$SERVICE_ID/filter" \
  -H "Authorization: Bearer $TOKEN")
CURRENT_INCLUDE=$(echo $CURRENT | python3 -c "import sys, json; print(json.load(sys.stdin).get('include_keywords', ''))")
CURRENT_EXCLUDE=$(echo $CURRENT | python3 -c "import sys, json; print(json.load(sys.stdin).get('exclude_keywords', ''))")
echo "   Include: '$CURRENT_INCLUDE'"
echo "   Exclude: '$CURRENT_EXCLUDE'"

echo ""
echo "Available preset options:"
echo "  1) Clear all filters (show everything)"
echo "  2) Exclude: test;debug"
echo "  3) Exclude: test;debug;maintenance;deploy"
echo "  4) Include only: alert;critical;error"
echo "  5) Custom"
echo ""
read -p "Choose option (1-5): " choice

case $choice in
  1)
    INCLUDE=""
    EXCLUDE=""
    ;;
  2)
    INCLUDE=""
    EXCLUDE="test;debug"
    ;;
  3)
    INCLUDE=""
    EXCLUDE="test;debug;maintenance;deploy"
    ;;
  4)
    INCLUDE="alert;critical;error"
    EXCLUDE=""
    ;;
  5)
    read -p "Include keywords (semicolon-separated, or empty): " INCLUDE
    read -p "Exclude keywords (semicolon-separated, or empty): " EXCLUDE
    ;;
  *)
    echo "Invalid option"
    exit 1
    ;;
esac

echo ""
echo "🎯 Setting filter..."
curl -s -X PUT "$BASE_URL/users/user/services/$SERVICE_ID/filter" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"include_keywords\": \"$INCLUDE\", \"exclude_keywords\": \"$EXCLUDE\"}" | python3 -m json.tool

echo ""
echo "✅ Filter updated!"
echo "   Include: '$INCLUDE'"
echo "   Exclude: '$EXCLUDE'"
echo ""
echo "Refresh http://localhost:8000/notifications to see changes"
