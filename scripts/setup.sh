#!/usr/bin/env bash
set -euo pipefail

echo "=== Eraya Setup ==="

# 1. Copy .env
if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created .env from .env.example — add your API keys."
fi

# 2. Backend
echo -e "\nSetting up Python virtualenv..."
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q

python manage.py migrate
python manage.py collectstatic --noinput 2>/dev/null || true
echo "Backend ready."
cd ..

# 3. Frontend
echo -e "\nInstalling frontend dependencies..."
cd frontend
npm install --silent
echo "Frontend ready."
cd ..

echo -e "\n=== Done ==="
echo "Start: docker-compose up"
echo "Or manually:"
echo "  backend: cd backend && daphne -b 0.0.0.0 -p 8000 eraya.asgi:application"
echo "  frontend: cd frontend && npm run dev"
