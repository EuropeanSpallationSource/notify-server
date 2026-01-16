# 🚀 Quick Development Setup Guide

## Prerequisites
- Python 3.11+
- SQLite (for local dev) or PostgreSQL (for production-like setup)

## Setup Steps

### 1. Create Virtual Environment & Install Dependencies
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e '.[tests]'
```

### 2. Create `.env` File
The `.env` file in the root directory configures the server for local development:

```bash
# Authentication - uses demo account (username: demo, password: demo)
DEMO_ACCOUNT_PASSWORD=demo
DEMO_ACCOUNT_SERVICE=demo
ADMIN_USERS=demo

# Bypass LDAP for development
AUTHENTICATION_METHOD=url
AUTHENTICATION_URL=http://localhost:9999/fake-auth

# Database
SQLALCHEMY_DATABASE_URL=sqlite:///./sql_app.db

# Disable OIDC
OIDC_ENABLED=false

# Push notification settings (test values)
FIREBASE_PROJECT_ID=my-project
GOOGLE_APPLICATION_CREDENTIALS=test-key.json
APNS_KEY_ID=UB40ZXKCDZ
TEAM_ID=6F44JJ9SDF
NB_PARALLEL_PUSH=2
```

### 3. Initialize Database
```bash
.venv/bin/notify-server create-db
```

### 4. Start Development Server
```bash
.venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The server will be available at:
- **API v2 Docs**: http://localhost:8000/api/v2/docs
- **API v1 Docs**: http://localhost:8000/api/v1/docs
- **Web UI**: http://localhost:8000/

## Testing the API

### Login (Get Access Token)
```bash
curl -X POST 'http://localhost:8000/api/v2/login' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=demo&password=demo'
```

Save the `access_token` from the response.

### Create a Service (Admin Only)
```bash
TOKEN="your_access_token_here"

curl -X POST 'http://localhost:8000/api/v2/services' \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"category":"test-service","color":"FF5733","owner":"demo"}'
```

### Set Up Notification Filters
```bash
SERVICE_ID="service_id_from_previous_step"

# Exclude notifications containing "test" or "debug"
curl -X PUT "http://localhost:8000/api/v2/users/user/services/${SERVICE_ID}/filter" \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"exclude_keywords":"test;debug","include_keywords":""}'
```

### Add Device Token
```bash
# For iOS (64 character hex string)
curl -X POST 'http://localhost:8000/api/v2/users/user/device-token' \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"device_token":"1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"}'

# For Android (longer token from Firebase)
curl -X POST 'http://localhost:8000/api/v2/users/user/device-token' \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"device_token":"your_firebase_token_here_which_is_much_longer_than_64_characters"}'
```

### Send a Notification
```bash
# This will trigger filter matching and push delivery
curl -X POST "http://localhost:8000/api/v2/services/${SERVICE_ID}/notifications" \
  -H 'Content-Type: application/json' \
  -d '{
    "title":"Production Alert",
    "subtitle":"Database connection pool exhausted",
    "url":"https://monitoring.example.com/alert/123"
  }'
```

## Notification Filtering

The filter system allows users to control which notifications they receive:

### How It Works
1. **Exclude keywords** (checked first): If notification text matches any exclude keyword, it's blocked
2. **Include keywords** (if set): Notification must match at least one include keyword
3. **No filter**: All notifications are sent (backward compatible)

### Filter Examples

**Block test notifications:**
```json
{"exclude_keywords": "test;debug;staging", "include_keywords": ""}
```

**Only receive critical alerts:**
```json
{"exclude_keywords": "", "include_keywords": "critical;urgent;emergency"}
```

**Exclude tests but only show errors:**
```json
{"exclude_keywords": "test;debug", "include_keywords": "error;failure;critical"}
```

Keywords are:
- **Semicolon-separated**: `"keyword1;keyword2;keyword3"`
- **Case-insensitive**: "ERROR" matches "error"
- **Substring matching**: "test" matches "testing" or "latest"

## Automated Test Script

Run the included test script to set up a complete demo environment:

```bash
./test-setup.sh
```

This script will:
1. Login with the demo account
2. Create a test service
3. Subscribe to the service
4. Set up example filters
5. Show you how to send notifications

## Troubleshooting

### LDAP Errors
If you see `ldap3.core.exceptions.LDAPSocketOpenError`, make sure your `.env` file has:
```
AUTHENTICATION_METHOD=url
```

### Session/Cookie Issues
The web UI requires HTTPS in production but uses `https_only=False` implicitly in dev due to localhost.

### Push Notification Testing
- APNs requires valid certificates (use dummy values for now)
- Firebase requires a valid service account JSON file
- Notifications are logged even if push delivery fails

## Running Tests
```bash
pytest -v tests
```

Tests use in-memory SQLite and mock external services (APNs/Firebase).
