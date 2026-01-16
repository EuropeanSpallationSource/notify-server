#!/bin/bash
echo "=== Checking notify-test.esss.lu.se deployment status ==="
echo ""

echo "1. Testing /health endpoint:"
curl -s http://notify-test.esss.lu.se/health || echo "FAILED"
echo ""

echo "2. Checking API v2 endpoints for new filter routes:"
curl -s http://notify-test.esss.lu.se/api/v2/openapi.json | python3 -m json.tool | grep -A 2 "filter" | head -20
echo ""

echo "3. Testing if settings page has filter UI (requires login):"
echo "   Visit: http://notify-test.esss.lu.se/settings"
echo "   Look for 'Notification Filters' section under subscribed services"
echo ""

echo "4. Check GitLab CI pipeline:"
echo "   Visit your GitLab repo -> CI/CD -> Pipelines"
echo "   Look for commit: 653b96c"
