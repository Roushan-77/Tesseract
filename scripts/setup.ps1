$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

if (-not (Test-Path ".env")) {
  Copy-Item ".env.example" ".env"
  Write-Host "Created .env from .env.example. Review DEMO_PASSWORD and JWT_SECRET before sharing the project."
}

docker compose -f infrastructure/docker-compose.yml up -d
if ($LASTEXITCODE -ne 0) {
  throw "PostgreSQL could not start. Open Docker Desktop, wait for its engine, then run this script again."
}

Write-Host "Waiting for PostgreSQL..."
for ($attempt = 1; $attempt -le 30; $attempt++) {
  docker compose -f infrastructure/docker-compose.yml exec -T postgres pg_isready -U tesseract -d tesseract | Out-Null
  if ($LASTEXITCODE -eq 0) { break }
  Start-Sleep -Seconds 2
}
if ($LASTEXITCODE -ne 0) { throw "PostgreSQL did not become ready within 60 seconds." }

Push-Location apps/api
try {
  python -m alembic upgrade head
  python -m app.seed
} finally {
  Pop-Location
}

Write-Host "Tesseract database is ready. Start the API and web commands in README.md."
