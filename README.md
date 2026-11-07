# QuantaBench - Full Stack Quantum Optimization Workbench

**Honest quantum vs classical benchmarking for portfolio optimization**

QuantaBench is a full-stack application that solves portfolio optimization using QAOA (Quantum Approximate Optimization Algorithm) and compares results against classical baselines with complete transparency.

---

## 🎯 Key Features

- **QAOA Implementation** - Built with Classiq synthesis and qBraid execution
- **Honest Benchmarking** - Reports when classical methods win
- **Multiple Solvers** - Brute force, simulated annealing, greedy heuristics
- **Real-time UI** - Interactive dashboard with live results
- **Deterministic Demos** - Cached results ensure demos never fail
- **Production Ready** - Dockerized deployment, comprehensive tests

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│          Frontend (Next.js + React)                 │
│  ┌──────────────────────────────────────────────┐  │
│  │  Interactive UI · Real-time Results Display  │  │
│  │  React Query · TypeScript · Tailwind CSS     │  │
│  └──────────────────────────────────────────────┘  │
└───────────────────┬─────────────────────────────────┘
                    │ REST API (FastAPI)
                    │
┌───────────────────▼─────────────────────────────────┐
│          Backend (Python + FastAPI)                 │
│  ┌──────────────────────────────────────────────┐  │
│  │  QAOA Pipeline · Classical Solvers · Metrics │  │
│  │  Classiq · qBraid · Qiskit Aer               │  │
│  └──────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Option 1: Docker Compose (Recommended)

**1. Clone the repository**
```bash
git clone https://github.com/yourusername/quantabench.git
cd quantabench
```

**2. Create environment file**
```bash
# Copy example
cp backend/.env.example .env

# Edit with your credentials
nano .env
```

**3. Start services**
```bash
docker-compose up --build
```

**4. Access the application**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Option 2: Manual Setup

**Backend:**
```bash
cd backend

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# (Optional) Precompute demo cache
python scripts/precompute_demo.py

# Start server
uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd "QuantaBench Frontend/quanta-main"

# Install dependencies
pnpm install

# Configure environment
cp .env.local.example .env.local
# Edit .env.local (default API_URL is http://localhost:8000)

# Start development server
pnpm dev
```

---

## ⚙️ Configuration

### Backend Environment Variables

```env
# Classiq Authentication (M2M flow)
CLASSIQ_CLIENT_ID=your_client_id
CLASSIQ_CLIENT_SECRET=your_client_secret

# qBraid Authentication
QBRAID_API_KEY=your_qbraid_api_key

# Optional: IonQ (self-managed)
IONQ_API_KEY=your_ionq_key

# Feature Flags
ENABLE_CLASSIQ=true
ENABLE_QBRAID=true
ENABLE_HARDWARE=false  # Set true only for live QPU access
CACHE_ENABLED=true

# Cache Configuration
CACHE_DIR=./cache
CACHE_TTL_HOURS=168  # 1 week

# Logging
LOG_LEVEL=INFO
```

### Frontend Environment Variables

```env
# Backend API URL
NEXT_PUBLIC_API_URL=http://localhost:8000

# Optional: Debug logging
NEXT_PUBLIC_DEBUG=false
```

---

## 📖 Usage

### Running a Benchmark

**Via UI:**
1. Navigate to http://localhost:3000
2. Configure problem parameters:
   - Asset count (N): 5-15
   - Holdings (K): 2 to N-1
   - Risk aversion (λ): 0-1
   - QAOA depth (p): 1-4
   - Shots: 1024, 2048, or 4096
3. Click "Run Benchmark"
4. View real-time results with quantum vs classical comparison

**Via API:**
```bash
curl -X POST "http://localhost:8000/api/optimize" \
  -H "Content-Type: application/json" \
  -d '{
    "problem_type": "portfolio",
    "problem_params": {
      "returns_file": "sample",
      "n_assets": 8,
      "budget": 3,
      "risk_aversion": 0.5
    },
    "qaoa_params": {
      "p": 2,
      "shots": 2048
    },
    "quantum_backend": "aer_simulator",
    "seed": 42
  }'
```

### Retrieving Results

```bash
# Get specific run
curl http://localhost:8000/api/runs/{run_id}

# Check backend health
curl http://localhost:8000/api/health

# List available problems
curl http://localhost:8000/api/problems
```

---

## 🧪 Testing

### Backend Tests
```bash
cd backend

# Run all tests
pytest

# Run with coverage
pytest --cov=app tests/

# Run specific test file
pytest tests/unit/test_hamiltonian.py

# Run integration tests
pytest tests/integration/
```

### Frontend Tests
```bash
cd "QuantaBench Frontend/quanta-main"

# Type checking
pnpm tsc --noEmit

# Linting
pnpm eslint . --ext .ts,.tsx
```

---

## 📊 API Documentation

### Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/optimize` | POST | Run optimization problem |
| `/api/runs/{run_id}` | GET | Retrieve optimization results |
| `/api/health` | GET | Backend health check |
| `/api/problems` | GET | List available problems |

Full API documentation available at: http://localhost:8000/docs

---

## 🎨 Frontend Features

### Interactive Workbench
- Real-time parameter tuning
- Live backend connection status
- Configurable problem size and QAOA depth
- Deterministic mode with seed control

### Results Dashboard
- KPI cards (approximation ratio, probability of optimal, feasibility)
- Solver comparison table (quantum + classical baselines)
- Measurement histogram
- Execution time breakdown
- Selected portfolio visualization

### Honest Assessment
- Transparent reporting when classical methods outperform quantum
- Side-by-side metrics for all solvers
- No cherry-picking or selective reporting

---

## 🔧 Development

### Project Structure

```
quantabench/
├── backend/                    # FastAPI backend
│   ├── app/
│   │   ├── main.py            # FastAPI application
│   │   ├── config.py          # Settings
│   │   ├── schemas.py         # Pydantic models
│   │   ├── problems/          # Problem definitions
│   │   ├── quantum/           # QAOA implementation
│   │   ├── classical/         # Classical solvers
│   │   ├── services/          # Pipeline, cache, registry
│   │   ├── metrics.py         # Benchmarking metrics
│   │   └── data/              # Sample data
│   ├── tests/                 # Unit & integration tests
│   ├── scripts/               # Precompute & utilities
│   ├── requirements.txt       # Python dependencies
│   ├── Dockerfile            # Backend container
│   └── README.md             # Backend documentation
├── QuantaBench Frontend/
│   └── quanta-main/          # Next.js frontend
│       ├── app/              # Next.js app directory
│       │   ├── page.tsx      # Main page
│       │   ├── layout.tsx    # Root layout
│       │   └── globals.css   # Styles
│       ├── lib/              # Utilities & services
│       │   ├── api-client.ts # API client
│       │   ├── types.ts      # TypeScript types
│       │   ├── hooks/        # React Query hooks
│       │   ├── utils/        # Formatting utilities
│       │   └── providers/    # React providers
│       ├── components/       # React components
│       ├── package.json      # Node dependencies
│       ├── Dockerfile       # Frontend container
│       └── .env.local       # Environment config
├── docker-compose.yml        # Full stack deployment
└── README.md                # This file
```

### Adding New Features

**Backend:**
1. Define problem in `backend/app/problems/`
2. Add solver in `backend/app/classical/` or `backend/app/quantum/`
3. Update schemas in `backend/app/schemas.py`
4. Add tests in `backend/tests/`

**Frontend:**
1. Update types in `lib/types.ts`
2. Modify UI in `app/page.tsx`
3. Add utilities in `lib/utils/` if needed

---

## 🐳 Deployment

### Docker Compose (Production)

```bash
# Build and start
docker-compose up -d --build

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Clean up (remove volumes)
docker-compose down -v
```

### Individual Services

**Backend:**
```bash
cd backend
docker build -t quantabench-backend .
docker run -p 8000:8000 --env-file .env quantabench-backend
```

**Frontend:**
```bash
cd "QuantaBench Frontend/quanta-main"
docker build -t quantabench-frontend .
docker run -p 3000:3000 -e NEXT_PUBLIC_API_URL=http://localhost:8000 quantabench-frontend
```

### Cloud Deployment

**Backend (Render/Railway/Fly.io):**
- Set environment variables in dashboard
- Deploy from GitHub
- Configure health check endpoint: `/api/health`

**Frontend (Vercel/Netlify):**
- Set `NEXT_PUBLIC_API_URL` to your backend URL
- Deploy from GitHub
- Build command: `pnpm build`
- Output directory: `.next`

---

## 📈 Performance

### Caching
- Results cached by problem parameters + seed
- TTL: 168 hours (configurable)
- Cache hit provides instant response (<100ms)
- Cache miss: 3-15 seconds depending on problem size

### Scaling
- Small problems (n≤10): 2-5 seconds
- Medium problems (n=10-15): 5-15 seconds
- Brute force optimal: feasible up to n=20

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📝 License

MIT License - see LICENSE file for details

---

## 🏆 Competition Context

Built for the **Intermountain Quantum Competition (BYU)** with focus on:
- **Best Use of Classiq** - High-level QAOA modeling, constrained synthesis
- **Best Use of qBraid** - Unified provider interface, automatic transpilation
- **Honest Benchmarking** - Transparent reporting, never hiding classical wins

---

## 📞 Support

- **Documentation**: See backend/README.md and backend/COMPETITION_SUMMARY.md
- **API Docs**: http://localhost:8000/docs
- **Issues**: GitHub Issues
- **Email**: your.email@example.com

---

## 🙏 Acknowledgments

- **Classiq** - Circuit synthesis and optimization
- **qBraid** - Unified quantum device access
- **IBM Qiskit** - Quantum simulation framework
- **FastAPI** - High-performance Python web framework
- **Next.js** - React framework for production

---

**Built with ❤️ for transparent quantum computing**
