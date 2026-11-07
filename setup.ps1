# QuantaBench Setup Script (PowerShell)
# Automated setup for backend and frontend

$ErrorActionPreference = "Stop"

Write-Host "======================================" -ForegroundColor Cyan
Write-Host "  QuantaBench Setup" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

function Print-Step {
    param($Message)
    Write-Host "==> $Message" -ForegroundColor Blue
}

function Print-Success {
    param($Message)
    Write-Host "✓ $Message" -ForegroundColor Green
}

function Print-Warning {
    param($Message)
    Write-Host "⚠ $Message" -ForegroundColor Yellow
}

# Check if running from project root
if (-not (Test-Path "backend") -or -not (Test-Path "QuantaBench Frontend")) {
    Write-Host "Error: Please run this script from the project root directory" -ForegroundColor Red
    exit 1
}

# Check Python version
Print-Step "Checking Python version..."
try {
    $pythonVersion = & python --version 2>&1
    if ($pythonVersion -match "Python 3\.11") {
        Print-Success "Python 3.11 found"
    } else {
        Print-Warning "Python 3.11 not found. Please install Python 3.11+"
        exit 1
    }
} catch {
    Print-Warning "Python not found. Please install Python 3.11+"
    exit 1
}

# Check Node.js version
Print-Step "Checking Node.js version..."
try {
    $nodeVersion = & node -v
    $nodeMajor = [int]($nodeVersion -replace "v(\d+)\..*", '$1')
    if ($nodeMajor -ge 18) {
        Print-Success "Node.js found"
    } else {
        Print-Warning "Node.js version must be 18 or higher"
        exit 1
    }
} catch {
    Print-Warning "Node.js not found. Please install Node.js 18+"
    exit 1
}

# Check pnpm
Print-Step "Checking pnpm..."
try {
    $null = & pnpm -v
    Print-Success "pnpm found"
} catch {
    Print-Warning "pnpm not found. Installing pnpm..."
    npm install -g pnpm
}

Write-Host ""
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "  Backend Setup" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

Set-Location backend

# Create virtual environment
Print-Step "Creating Python virtual environment..."
python -m venv venv
Print-Success "Virtual environment created"

# Activate virtual environment
Print-Step "Activating virtual environment..."
& .\venv\Scripts\Activate.ps1
Print-Success "Virtual environment activated"

# Install dependencies
Print-Step "Installing Python dependencies..."
python -m pip install --upgrade pip
pip install -r requirements.txt
Print-Success "Python dependencies installed"

# Setup environment
if (-not (Test-Path ".env")) {
    Print-Step "Creating .env file..."
    Copy-Item .env.example .env
    Print-Warning "Please edit backend\.env with your API keys"
} else {
    Print-Success ".env file already exists"
}

# Create cache directory
Print-Step "Creating cache directory..."
New-Item -ItemType Directory -Force -Path cache | Out-Null
Print-Success "Cache directory created"

# Precompute demo cache (optional)
$response = Read-Host "Precompute demo cache? This will take 2-5 minutes (y/n)"
if ($response -eq 'y' -or $response -eq 'Y') {
    Print-Step "Precomputing demo cache..."
    python scripts\precompute_demo.py
    Print-Success "Demo cache precomputed"
} else {
    Print-Warning "Skipping demo cache precomputation"
}

# Run tests
$response = Read-Host "Run backend tests? (y/n)"
if ($response -eq 'y' -or $response -eq 'Y') {
    Print-Step "Running backend tests..."
    pytest
    Print-Success "Backend tests passed"
} else {
    Print-Warning "Skipping backend tests"
}

Set-Location ..

Write-Host ""
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "  Frontend Setup" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

Set-Location "QuantaBench Frontend\quanta-main"

# Install dependencies
Print-Step "Installing Node dependencies..."
pnpm install
Print-Success "Node dependencies installed"

# Setup environment
if (-not (Test-Path ".env.local")) {
    Print-Step "Creating .env.local file..."
    Copy-Item .env.local.example .env.local
    Print-Success ".env.local created"
} else {
    Print-Success ".env.local already exists"
}

Set-Location ..\..

Write-Host ""
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "  Setup Complete!" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "To start the application:" -ForegroundColor White
Write-Host ""
Write-Host "Option 1: Docker Compose (Recommended)" -ForegroundColor Yellow
Write-Host "  docker-compose up --build"
Write-Host ""
Write-Host "Option 2: Manual" -ForegroundColor Yellow
Write-Host "  Backend:"
Write-Host "    cd backend"
Write-Host "    .\venv\Scripts\Activate.ps1"
Write-Host "    uvicorn app.main:app --reload --port 8000"
Write-Host ""
Write-Host "  Frontend (in another terminal):"
Write-Host "    cd 'QuantaBench Frontend\quanta-main'"
Write-Host "    pnpm dev"
Write-Host ""
Write-Host "Access the application:" -ForegroundColor White
Write-Host "  Frontend: http://localhost:3000" -ForegroundColor Green
Write-Host "  Backend:  http://localhost:8000" -ForegroundColor Green
Write-Host "  API Docs: http://localhost:8000/docs" -ForegroundColor Green
Write-Host ""
Print-Warning "Don't forget to configure your API keys in backend\.env!"
Write-Host ""
