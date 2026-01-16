#!/usr/bin/env bash
# Complete setup script for ESS Notify Server development

set -e

echo "🔧 ESS Notify Server - Complete Development Setup"
echo "=================================================="
echo ""

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file..."
    cat > .env << 'EOF'
# Development Environment Configuration
DEMO_ACCOUNT_PASSWORD=demo
DEMO_ACCOUNT_SERVICE=demo
ADMIN_USERS=demo

AUTHENTICATION_METHOD=url
AUTHENTICATION_URL=http://localhost:9999/fake-auth

SQLALCHEMY_DATABASE_URL=sqlite:///./sql_app.db
OIDC_ENABLED=false

FIREBASE_PROJECT_ID=my-project
GOOGLE_APPLICATION_CREDENTIALS=test-key.json
APNS_KEY_ID=UB40ZXKCDZ
TEAM_ID=6F44JJ9SDF
NB_PARALLEL_PUSH=2
SQLALCHEMY_DEBUG=false
EOF
    echo "✅ Created .env file"
else
    echo "ℹ️  .env file already exists"
fi
echo ""

# Check if venv exists
if [ ! -d ".venv" ]; then
    echo "🐍 Creating virtual environment..."
    python3 -m venv .venv
    echo "✅ Virtual environment created"
else
    echo "ℹ️  Virtual environment already exists"
fi
echo ""

# Activate and install dependencies
echo "📦 Installing dependencies..."
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -r requirements.txt
.venv/bin/pip install -q -e '.[tests]'
echo "✅ Dependencies installed"
echo ""

# Create database
echo "🗄️  Creating database..."
.venv/bin/notify-server create-db
echo "✅ Database created"
echo ""

# Create initial service
echo "🎯 Creating initial demo service..."
sqlite3 sql_app.db << 'EOF'
INSERT OR IGNORE INTO services (id, category, color, owner) 
VALUES ('d3f4e5a6b7c8d9e0f1a2b3c4d5e6f7a8', 'demo', 'FF5733', 'demo');
EOF
echo "✅ Demo service created"
echo ""

echo "✨ Setup complete!"
echo ""
echo "📚 Next steps:"
echo "   1. Start the server:"
echo "      .venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
echo ""
echo "   2. Test the setup:"
echo "      ./test-setup.sh"
echo ""
echo "   3. View API docs:"
echo "      http://localhost:8000/api/v2/docs"
echo ""
echo "   4. Read development guide:"
echo "      cat DEV_SETUP.md"
echo ""
