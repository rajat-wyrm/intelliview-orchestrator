$ErrorActionPreference = "Stop"

Write-Host "========================================"
Write-Host " IntelliView Orchestrator Setup"
Write-Host "========================================"
Write-Host ""

Write-Host "Checking prerequisites..."

# Check Docker
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Error "Docker is not installed or not available in PATH."
    exit 1
}

Write-Host "Docker: OK"

# Check Docker Compose
try {
    docker compose version | Out-Null
    Write-Host "Docker Compose: OK"
}
catch {
    Write-Error "Docker Compose is not available."
    exit 1
}

# Check Node.js
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    Write-Error "Node.js is not installed or not available in PATH."
    exit 1
}

Write-Host "Node.js: OK"

# Check npm
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    Write-Error "npm is not installed or not available in PATH."
    exit 1
}

Write-Host "npm: OK"
Write-Host ""
Write-Host "Checking environment file..."

if (-not (Test-Path ".env")) {
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env"
        Write-Host ".env created from .env.example"
    }
    else {
        Write-Error ".env.example not found."
        exit 1
    }
}
else {
    Write-Host ".env already exists. Keeping existing configuration."
}

Write-Host ""
Write-Host "Setting up Python environment..."
Write-Host ""

if (-not (Test-Path ".venv")) {
    python -m venv .venv

    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to create Python virtual environment."
        exit 1
    }

    Write-Host "Python virtual environment created."
}
else {
    Write-Host "Python virtual environment already exists."
}

Write-Host "Installing Python dependencies..."

& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt

if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to install Python dependencies."
    exit 1
}

Write-Host "Python dependencies installed successfully."
Write-Host ""
Write-Host "Starting Docker services..."
Write-Host ""

docker compose up -d --build

if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to start Docker services."
    exit 1
}

Write-Host ""
Write-Host "Docker services started successfully."
Write-Host ""
Write-Host "Waiting for required Docker services to become healthy..."

$requiredServices = @("redis", "postgres")
$timeoutSeconds = 120
$pollIntervalSeconds = 2
$elapsedSeconds = 0
$servicesReady = $false

while ($elapsedSeconds -lt $timeoutSeconds) {
    $services = docker compose ps --format "{{.Service}}|{{.Health}}|{{.State}}"

    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to check Docker service health."
        exit 1
    }

    $health = @{}

    foreach ($line in $services) {
        if (-not [string]::IsNullOrWhiteSpace($line)) {
            $parts = $line -split '\|', 3

            if ($parts.Count -eq 3) {
                $health[$parts[0]] = $parts[1]
            }
        }
    }

    $servicesReady = $true

    foreach ($service in $requiredServices) {
        if (-not $health.ContainsKey($service) -or $health[$service] -ne "healthy") {
            $servicesReady = $false
            break
        }
    }

    if ($servicesReady) {
        break
    }

    Start-Sleep -Seconds $pollIntervalSeconds
    $elapsedSeconds += $pollIntervalSeconds
}

if (-not $servicesReady) {
    Write-Error "Timed out waiting for required Docker services to become healthy: $($requiredServices -join ', ')."
    docker compose ps
    exit 1
}

Write-Host "Required Docker services are healthy."
Write-Host ""
Write-Host "Seeding demo data..."
Write-Host ""

& ".\.venv\Scripts\python.exe" scripts/seed.py

if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to seed demo data."
    exit 1
}

Write-Host ""
Write-Host "Demo data seeded successfully."
Write-Host ""
Write-Host "Installing frontend dependencies..."
Write-Host ""

Push-Location "frontend"

npm.cmd install

if ($LASTEXITCODE -ne 0) {
    Pop-Location
    Write-Error "Failed to install frontend dependencies."
    exit 1
}

Pop-Location

Write-Host ""
Write-Host "Frontend dependencies installed successfully."
Write-Host ""
Write-Host "========================================"
Write-Host " Setup completed successfully!"
Write-Host "========================================"
Write-Host ""
Write-Host "Start the frontend with:"
Write-Host "  cd frontend"
Write-Host "  npm run dev"
Write-Host ""
Write-Host "Then open:"
Write-Host "  http://localhost:3000"