# QuantaBench Backend

Track-agnostic quantum optimization workbench for the Intermountain Quantum Competition (BYU).

## Overview

QuantaBench solves portfolio optimization problems using QAOA, executed through **Classiq** (circuit synthesis) and **qBraid** (device access), with honest benchmarking against classical solvers.

### Key Features

1. **Deterministic Demo Pipeline** - Never fails live with cached results and automatic fallback
2. **Explicit Classiq Usage** - High-level QAOA modeling, constrained synthesis, execution reporting
3. **Explicit qBraid Usage** - Unified device access, automatic transpilation, multi-framework support
4. **Honest Benchmarking** - Classical baselines (brute force, annealing, greedy) included
5. **Plug-in Architecture** - Add new problems (Max-Cut, scheduling) in under 30 minutes

## Tech Stack

- **Python 3.11** - Fast API, Pydantic v2, pytest
- **Quantum SDKs**:
  - **Classiq** - Circuit modeling and synthesis
  - **qBraid** - Backend/provider access
  - **Qiskit + Aer** - Always-available fallback simulator
- **Scientific**: NumPy, SciPy (COBYLA), pandas
- **Configuration**: .env files, no hardcoded secrets

## Project Structure

```
backend/
├── app/
│   ├── main.py                 # FastAPI app
│   ├── config.py               # Settings & env loading
│   ├── schemas.py              # Pydantic models
│   ├── problems/
│   │   ├── base.py            # Abstract Problem interface
│   │   ├── portfolio.py       # Mean-variance portfolio
│   │   └── maxcut.py          # Max-Cut (stretch)
│   ├── quantum/
│   │   ├── hamiltonian.py     # QUBO ↔ Ising conversion
│   │   ├── backends.py        # Backend adapters
│   │   ├── qaoa_classiq.py    # Classiq QAOA builder
│   │   └── optimizer.py       # COBYLA w/ warm-start
│   ├── classical/
│   │   ├── brute_force.py     # Exact solver
│   │   ├── annealing.py       # Simulated annealing
│   │   └── greedy.py          # Greedy heuristic
│   ├── services/
│   │   ├── pipeline.py        # Orchestration
│   │   ├── cache.py           # Disk cache
│   │   └── runs.py            # Run registry
│   ├── metrics.py             # Benchmarking metrics
│   └── data/
│       └── returns_sample.csv # Sample stock returns
├── tests/
│   └── unit/                  # Unit tests
├── scripts/
│   └── precompute_demo.py     # Pre-generate cache
├── requirements.txt
├── .env.example
└── README.md
```

## Installation

### 1. Install Dependencies

```bash
# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install requirements
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

Edit `.env`:

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
```

### 3. Authenticate Classiq (Alternative: Interactive)

If not using M2M credentials:

```python
from classiq import authenticate
authenticate()  # Opens browser for confirmation
```

### 4. Verify Installation

```bash
pytest tests/unit/
```

## Usage

### Start API Server

```bash
# Development server (with auto-reload)
uvicorn app.main:app --reload --port 8000

# Production server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

API will be available at `http://localhost:8000`

Interactive docs: `http://localhost:8000/docs`

### Precompute Demo Cache

For deterministic demo behavior, precompute common scenarios:

```bash
python scripts/precompute_demo.py
```

This generates cached results for:
- Small (5 assets, p=1-2)
- Medium (8 assets, p=1-2)
- Large (10 assets, p=1-2)

### Run Optimization

**Via Python:**

```python
import requests

# Portfolio optimization request
response = requests.post("http://localhost:8000/api/optimize", json={
    "problem_type": "portfolio",
    "problem_params": {
        "returns_file": "sample",  # Uses built-in sample data
        "n_assets": 8,
        "budget": 3,
        "risk_aversion": 0.5
    },
    "qaoa_params": {
        "p": 2,
        "shots": 2048
    },
    "quantum_backend": "aer_simulator",  # or "classiq", "qbraid"
    "seed": 42
})

result = response.json()
print(f"Run ID: {result['run_id']}")
print(f"Quantum objective: {result['quantum_result']['objective_value']}")
print(f"Best classical: {result['best_classical_result']['objective_value']}")
print(f"Approximation ratio: {result['metrics']['approximation_ratio']}")
```

**Via cURL:**

```bash
curl -X POST "http://localhost:8000/api/optimize" \
  -H "Content-Type: application/json" \
  -d '{
    "problem_type": "portfolio",
    "problem_params": {
      "returns_file": "sample",
      "n_assets": 5,
      "budget": 2,
      "risk_aversion": 0.5
    },
    "qaoa_params": {
      "p": 1,
      "shots": 1024
    },
    "seed": 42
  }'
```

### Retrieve Run Results

```python
import requests

run_id = "abc123"  # From optimization response
response = requests.get(f"http://localhost:8000/api/runs/{run_id}")
result = response.json()
```

## Architecture

### Problem Interface

All problems implement:

```python
class Problem(ABC):
    @abstractmethod
    def build_qubo(self) -> Tuple[np.ndarray, float]:
        """Construct QUBO matrix Q and offset."""
        
    @abstractmethod
    def evaluate_objective(self, bitstring: str) -> float:
        """Evaluate objective for solution."""
        
    @abstractmethod
    def is_feasible(self, bitstring: str) -> bool:
        """Check constraint satisfaction."""
```

### Backend Adapters

Unified interface with automatic fallback:

```python
# Try Classiq, fall back to Aer on error
result, fell_back = backend_manager.execute_with_fallback(
    "classiq_simulator",
    circuit,
    shots=1024
)

# Backend automatically falls back on:
# - Authentication errors
# - Quota exceeded
# - Timeout
# - NotImplementedError (SDK not installed)
```

### QAOA Pipeline

```python
# 1. Build QUBO from problem
Q, offset = problem.build_qubo()

# 2. Convert to Ising Hamiltonian
h, J, ising_offset = qubo_to_ising(Q, offset)

# 3. Create Classiq QAOA circuit
qaoa = ClassiqQAOACircuit(h, J, ising_offset, 
                          max_circuit_width=20)

# 4. Optimize parameters with COBYLA
params = optimize_qaoa(qaoa, p=2, shots=1024, 
                       backend="classiq_simulator")

# 5. Extract best solution
best_bitstring = get_best_bitstring_from_counts(counts)
```

## Classiq Integration

### Explicit Usage Points

1. **QAOA Model Building** (`qaoa_classiq.py`)
   - High-level cost/mixer layer definitions
   - Qmod functional syntax

2. **Synthesis with Constraints** (`ClassiqQAOACircuit.synthesize()`)
   - `max_circuit_width`
   - `max_circuit_depth`
   - Returns synthesis report with gate counts

3. **Execution** (`ClassiqBackend.execute_circuit()`)
   - Direct execution on Classiq backends
   - Automatic fallback to Aer

### Fallback Behavior

If Classiq SDK is not installed:
- QAOA circuit is built in Qiskit format
- Executed on Aer simulator
- All other features work identically

## qBraid Integration

### Explicit Usage Points

1. **Automatic Transpilation** (`QBraidBackend.execute_circuit()`)
   - Accepts Qiskit, Cirq, Braket, OpenQASM
   - qBraid handles conversion automatically

2. **Unified Device Access** (`QbraidProvider`)
   - Single API key for all vendors
   - One call pattern for simulators and QPUs

3. **Error Handling**
   - Auth errors → helpful message
   - Quota exceeded → account link
   - Timeout → circuit size suggestion
   - All errors → automatic Aer fallback

### Device IDs

```python
# Simulators
"qbraid_qbraid_qiskit_simulator"
"qbraid_aws_sim_sv1"
"qbraid_ionq_simulator"

# Hardware (requires credits)
"qbraid_ionq_qpu_forte-1"
"qbraid_aws_rigetti_qpu_cepheus"
```

## Classical Baselines

For honest benchmarking:

- **Brute Force** - Exact solution (N ≤ 20)
- **Simulated Annealing** - Seeded, configurable temperature
- **Greedy** - Fast heuristic

All report runtime and solution quality.

## Metrics

```python
{
    "approximation_ratio": 0.95,  # vs optimal
    "prob_optimal": 0.42,         # P(measuring optimal)
    "feasibility_rate": 1.0,      # fraction feasible
    "sharpe_ratio": 1.82,         # portfolio metric
    "best_objective": -12.34,
    "optimal_objective": -12.98
}
```

## Caching

Results are cached by hash of `(problem_params, seed)`:

```python
# Cache key example
{
    "problem_type": "portfolio",
    "num_assets": 6,
    "target_size": 3,
    "risk_factor": 0.5,
    "seed": 42,
    "qaoa_p": 2
}
```

Cache TTL: 168 hours (1 week)

## Adding New Problems

1. **Inherit from `Problem`**

```python
class NewProblem(Problem):
    def build_qubo(self):
        # Construct Q matrix
        return Q, offset
    
    def evaluate_objective(self, bitstring):
        # Compute cost
        return cost
    
    def is_feasible(self, bitstring):
        # Check constraints
        return True
```

2. **Add to schema** (`schemas.py`)

```python
class ProblemType(str, Enum):
    NEW_PROBLEM = "new_problem"
```

3. **Register in router** (`main.py`)

4. **Test** (`tests/unit/test_new_problem.py`)

Total time: **< 30 minutes**

## Testing

```bash
# All tests
pytest

# Unit tests only
pytest tests/unit/

# Specific module
pytest tests/unit/test_hamiltonian.py

# With coverage
pytest --cov=app tests/
```

## API Endpoints

### `POST /api/optimize`

Run optimization problem.

**Request:**
```json
{
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
}
```

**Response:**
```json
{
    "run_id": "20231103_142530_abc123",
    "problem_type": "portfolio",
    "problem_params": {
        "returns_file": "sample",
        "n_assets": 8,
        "budget": 3,
        "risk_aversion": 0.5
    },
    "quantum_result": {
        "solution": "01010100",
        "objective_value": -15.234,
        "is_feasible": true,
        "constraint_violations": {},
        "backend_used": "aer_simulator",
        "execution_time_seconds": 3.45
    },
    "classical_results": [
        {
            "solver_name": "brute_force",
            "solution": "01001100",
            "objective_value": -16.123,
            "is_feasible": true,
            "execution_time_seconds": 0.12
        },
        {
            "solver_name": "simulated_annealing",
            "solution": "01001100",
            "objective_value": -16.123,
            "is_feasible": true,
            "execution_time_seconds": 0.08
        }
    ],
    "best_classical_result": {
        "solver_name": "brute_force",
        "solution": "01001100",
        "objective_value": -16.123,
        "is_feasible": true,
        "execution_time_seconds": 0.12
    },
    "metrics": {
        "approximation_ratio": 0.945,
        "probability_of_optimal": 0.234,
        "honest_assessment": "Classical (brute_force) found better solution: -16.123 vs -15.234",
        "optimal_objective": -16.123,
        "quantum_vs_optimal_gap": 0.889
    },
    "execution_time_seconds": 3.67,
    "cache_hit": false
}
```

### `GET /api/runs/{run_id}`

Retrieve results for a specific run.

**Response:** Same structure as `/api/optimize` response.

**Error Response (404):**
```json
{
    "detail": "Run not found: invalid_run_id"
}
```

### `GET /api/health`

Health check and system status.

**Response:**
```json
{
    "status": "healthy",
    "version": "1.0.0",
    "timestamp": "2023-11-03T14:25:30Z",
    "backends_available": {
        "aer_simulator": true,
        "classiq": false,
        "qbraid": false
    },
    "cache_enabled": true
}
```

### `GET /api/problems`

List available problem types and their parameters.

**Response:**
```json
{
    "problems": [
        {
            "id": "portfolio",
            "name": "Portfolio Optimization",
            "description": "Mean-variance portfolio selection with budget constraint",
            "parameters": {
                "returns_file": {
                    "type": "string",
                    "description": "Path to returns CSV or 'sample' for built-in data",
                    "required": true
                },
                "n_assets": {
                    "type": "integer",
                    "description": "Number of assets to select from",
                    "required": true,
                    "constraints": "n_assets >= 2"
                },
                "budget": {
                    "type": "integer",
                    "description": "Number of assets to include in portfolio",
                    "required": true,
                    "constraints": "1 <= budget < n_assets"
                },
                "risk_aversion": {
                    "type": "float",
                    "description": "Risk aversion parameter (higher = more conservative)",
                    "required": false,
                    "default": 0.5
                }
            }
        },
        {
            "id": "maxcut",
            "name": "Max-Cut",
            "description": "Maximum cut problem on weighted graph",
            "parameters": {
                "adjacency_matrix": {
                    "type": "array",
                    "description": "Weighted adjacency matrix",
                    "required": true
                }
            }
        }
    ]
}
```

## Troubleshooting

### Classiq Authentication Failed

```bash
# M2M flow
export CLASSIQ_CLIENT_ID="your_id"
export CLASSIQ_CLIENT_SECRET="your_secret"

# Interactive flow
python -c "from classiq import authenticate; authenticate()"
```

### qBraid API Key Not Found

```bash
export QBRAID_API_KEY="your_key"
```

Get key at: https://account.qbraid.com/account/api-keys

### Import Errors

```bash
pip install -r requirements.txt --upgrade
```

### Tests Failing

Check Python version:
```bash
python --version  # Should be 3.11+
```

## Development

### Pre-commit Hooks

```bash
pip install pre-commit
pre-commit install
```

### Code Style

```bash
# Format
black app/ tests/

# Lint
ruff check app/ tests/
```

## License

MIT License - see LICENSE file

## Competition Notes

### Best Use of Classiq

- Circuit synthesis with constraints (width, depth)
- High-level QAOA modeling in Qmod
- Synthesis report with gate counts
- Automatic optimization

### Best Use of qBraid

- Unified provider interface (QbraidProvider)
- Automatic transpilation from any framework
- Single API key for all devices
- Error handling with fallback

### Honest Benchmarking

- Classical baselines always run
- Metrics report even when classical wins
- Transparent approximation ratios
- No cherry-picking results
