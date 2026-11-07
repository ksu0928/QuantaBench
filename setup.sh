#!/bin/bash

# QuantaBench Setup Script
# Automated setup for backend and frontend

set -e

echo "======================================"
echo "  QuantaBench Setup"
echo "======================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running from project root
if [ ! -d "backend" ] || [ ! -d "QuantaBench Frontend" ]; then
    echo "Error: Please run this script from the project root directory"
    exit 1
fi

# Function to print colored output
print_step() {
    echo -e "${BLUE}==>${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Check Python version
print_step "Checking Python version..."
if ! command -v python3.11 &> /dev/null; then
    print_warning "Python 3.11 not found. Please install Python 3.11+"
    exit 1
fi
print_success "Python 3.11 found"

# Check Node.js version
print_step "Checking Node.js version..."
if ! command -v node &> /dev/null; then
    print_warning "Node.js not found. Please install Node.js 18+"
    exit 1
fi
NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -lt 18 ]; then
    print_warning "Node.js version must be 18 or higher"
    exit 1
fi
print_success "Node.js found"

# Check pnpm
print_step "Checking pnpm..."
if ! command -v pnpm &> /dev/null; then
    print_warning "pnpm not found. Installing pnpm..."
    npm install -g pnpm
fi
print_success "pnpm found"

echo ""
echo "======================================"
echo "  Backend Setup"
echo "======================================"
echo ""

cd backend

# Create virtual environment
print_step "Creating Python virtual environment..."
python3.11 -m venv venv
print_success "Virtual environment created"

# Activate virtual environment
print_step "Activating virtual environment..."
source venv/bin/activate
print_success "Virtual environment activated"

# Install dependencies
print_step "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
print_success "Python dependencies installed"

# Setup environment
if [ ! -f ".env" ]; then
    print_step "Creating .env file..."
    cp .env.example .env
    print_warning "Please edit backend/.env with your API keys"
else
    print_success ".env file already exists"
fi

# Create cache directory
print_step "Creating cache directory..."
mkdir -p cache
print_success "Cache directory created"

# Precompute demo cache (optional)
read -p "Precompute demo cache? This will take 2-5 minutes (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_step "Precomputing demo cache..."
    python scripts/precompute_demo.py
    print_success "Demo cache precomputed"
else
    print_warning "Skipping demo cache precomputation"
fi

# Run tests
read -p "Run backend tests? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_step "Running backend tests..."
    pytest
    print_success "Backend tests passed"
else
    print_warning "Skipping backend tests"
fi

cd ..

echo ""
echo "======================================"
echo "  Frontend Setup"
echo "======================================"
echo ""

cd "QuantaBench Frontend/quanta-main"

# Install dependencies
print_step "Installing Node dependencies..."
pnpm install
print_success "Node dependencies installed"

# Setup environment
if [ ! -f ".env.local" ]; then
    print_step "Creating .env.local file..."
    cp .env.local.example .env.local
    print_success ".env.local created"
else
    print_success ".env.local already exists"
fi

cd ../..

echo ""
echo "======================================"
echo "  Setup Complete!"
echo "======================================"
echo ""
echo "To start the application:"
echo ""
echo "Option 1: Docker Compose (Recommended)"
echo "  docker-compose up --build"
echo ""
echo "Option 2: Manual"
echo "  Backend:"
echo "    cd backend"
echo "    source venv/bin/activate  # Windows: venv\\Scripts\\activate"
echo "    uvicorn app.main:app --reload --port 8000"
echo ""
echo "  Frontend (in another terminal):"
echo "    cd \"QuantaBench Frontend/quanta-main\""
echo "    pnpm dev"
echo ""
echo "Access the application:"
echo "  Frontend: http://localhost:3000"
echo "  Backend:  http://localhost:8000"
echo "  API Docs: http://localhost:8000/docs"
echo ""
print_warning "Don't forget to configure your API keys in backend/.env!"
echo ""
