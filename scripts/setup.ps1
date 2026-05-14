# Eraya — Windows setup script
# Run from the project root: .\scripts\setup.ps1

Write-Host "=== Eraya Setup ===" -ForegroundColor Cyan

# 1. Copy .env
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env from .env.example — fill in your API keys." -ForegroundColor Yellow
} else {
    Write-Host ".env already exists." -ForegroundColor Green
}

# 2. Backend Python venv
Write-Host "`nSetting up Python virtual environment..." -ForegroundColor Cyan
Set-Location backend
python -m venv .venv
& .\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt

# 3. Django migrations
python manage.py migrate
python manage.py collectstatic --noinput

Write-Host "`nBackend ready. Run: daphne -b 0.0.0.0 -p 8000 eraya.asgi:application" -ForegroundColor Green
Set-Location ..

# 4. Frontend
Write-Host "`nInstalling frontend dependencies..." -ForegroundColor Cyan
Set-Location frontend
npm install
Write-Host "Frontend ready. Run: npm run dev" -ForegroundColor Green
Set-Location ..

Write-Host "`n=== Setup complete ===" -ForegroundColor Cyan
Write-Host "Quick start:"
Write-Host "  docker-compose up           # full stack with Docker"
Write-Host "  OR"
Write-Host "  backend: daphne -b 0.0.0.0 -p 8000 eraya.asgi:application"
Write-Host "  frontend: cd frontend && npm run dev"
