"""Pydantic schemas for API requests and responses."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator


# Enums
class ProblemType(str, Enum):
    """Supported optimization problem types."""

    PORTFOLIO = "portfolio"
    MAXCUT = "maxcut"


class SolverType(str, Enum):
    """Available solver types."""

    QUANTUM_QAOA = "quantum_qaoa"
    BRUTE_FORCE = "brute_force"
    SIMULATED_ANNEALING = "simulated_annealing"
    GREEDY = "greedy"


class BackendType(str, Enum):
    """Quantum backend types."""

    CLASSIQ_SIMULATOR = "classiq_simulator"
    QBRAID_SIMULATOR = "qbraid_simulator"
    QBRAID_HARDWARE = "qbraid_hardware"
    AER_FALLBACK = "aer_fallback"


class RunStatus(str, Enum):
    """Optimization run status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CACHED = "cached"


# Problem Parameters
class PortfolioParams(BaseModel):
    """Portfolio optimization parameters."""

    num_assets: int = Field(
        ..., ge=2, le=20, description="Number of assets to consider"
    )
    target_size: int = Field(..., ge=1, description="Target portfolio size (K)")
    risk_factor: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Risk aversion factor (q)"
    )
    lambda_penalty: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Cardinality constraint penalty (auto-tuned if None)",
    )
    seed: Optional[int] = Field(
        default=None, description="Random seed for reproducibility"
    )

    @field_validator("target_size")
    @classmethod
    def validate_target_size(cls, v: int, info) -> int:
        """Ensure target_size <= num_assets."""
        if "num_assets" in info.data and v > info.data["num_assets"]:
            raise ValueError("target_size must be <= num_assets")
        return v


class MaxCutParams(BaseModel):
    """Max-Cut problem parameters (stretch goal)."""

    num_nodes: int = Field(..., ge=3, le=20, description="Number of graph nodes")
    edge_probability: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Random graph edge probability"
    )
    seed: Optional[int] = Field(
        default=None, description="Random seed for graph generation"
    )


ProblemParams = Union[PortfolioParams, MaxCutParams]


# Quantum Execution Parameters
class QAOAParams(BaseModel):
    """QAOA execution parameters."""

    p: int = Field(default=2, ge=1, le=3, description="Number of QAOA layers")
    shots: int = Field(default=1024, ge=100, le=10000, description="Number of shots")
    backend: BackendType = Field(
        default=BackendType.CLASSIQ_SIMULATOR, description="Quantum backend to use"
    )
    optimizer_restarts: int = Field(
        default=3, ge=1, le=5, description="Number of optimizer restarts"
    )
    max_circuit_width: Optional[int] = Field(
        default=None, description="Max circuit width constraint (Classiq)"
    )
    max_circuit_depth: Optional[int] = Field(
        default=None, description="Max circuit depth constraint (Classiq)"
    )
    warm_start: bool = Field(
        default=True, description="Use warm-start from p-1 parameters"
    )


# Optimization Request
class OptimizationRequest(BaseModel):
    """Request to run optimization."""

    problem_type: ProblemType = Field(..., description="Type of optimization problem")
    problem_params: Dict[str, Any] = Field(
        ..., description="Problem-specific parameters"
    )
    solvers: List[SolverType] = Field(
        ..., min_length=1, description="Solvers to run"
    )
    qaoa_params: Optional[QAOAParams] = Field(
        default=None, description="QAOA parameters (required if using quantum solver)"
    )
    use_cache: bool = Field(
        default=True, description="Use cached results if available"
    )

    @field_validator("qaoa_params")
    @classmethod
    def validate_qaoa_params(cls, v: Optional[QAOAParams], info) -> Optional[QAOAParams]:
        """Ensure QAOA params provided if quantum solver requested."""
        if "solvers" in info.data:
            if SolverType.QUANTUM_QAOA in info.data["solvers"] and v is None:
                raise ValueError(
                    "qaoa_params required when using quantum_qaoa solver"
                )
        return v


# Results
class Solution(BaseModel):
    """Optimization solution."""

    bitstring: str = Field(..., description="Binary solution string")
    selected_indices: List[int] = Field(
        ..., description="Selected asset/node indices"
    )
    objective_value: float = Field(..., description="Objective function value")
    is_feasible: bool = Field(..., description="Whether solution satisfies constraints")
    probability: Optional[float] = Field(
        default=None, description="Measurement probability (quantum)"
    )


class SynthesisReport(BaseModel):
    """Circuit synthesis report (Classiq)."""

    num_qubits: int = Field(..., description="Number of qubits")
    circuit_depth: int = Field(..., description="Circuit depth")
    gate_counts: Dict[str, int] = Field(..., description="Gate type counts")
    synthesis_time_s: float = Field(..., description="Synthesis time in seconds")


class SolverResult(BaseModel):
    """Result from a single solver."""

    solver: SolverType = Field(..., description="Solver type")
    best_solution: Solution = Field(..., description="Best solution found")
    all_solutions: List[Solution] = Field(
        default_factory=list, description="All unique solutions explored"
    )
    runtime_s: float = Field(..., description="Solver runtime in seconds")
    backend_used: Optional[str] = Field(
        default=None, description="Backend used (for quantum)"
    )
    synthesis_report: Optional[SynthesisReport] = Field(
        default=None, description="Circuit synthesis details"
    )
    optimizer_iterations: Optional[int] = Field(
        default=None, description="Number of optimizer iterations"
    )
    final_parameters: Optional[List[float]] = Field(
        default=None, description="Final QAOA parameters"
    )


class Metrics(BaseModel):
    """Benchmarking metrics."""

    approximation_ratio: Optional[float] = Field(
        default=None, description="Approximation ratio vs optimal"
    )
    prob_optimal: Optional[float] = Field(
        default=None, description="Probability of measuring optimal (quantum)"
    )
    feasibility_rate: float = Field(
        ..., description="Fraction of feasible solutions"
    )
    sharpe_ratio: Optional[float] = Field(
        default=None, description="Sharpe ratio (portfolio only)"
    )
    best_objective: float = Field(..., description="Best objective value found")
    optimal_objective: Optional[float] = Field(
        default=None, description="Known optimal objective"
    )


class OptimizationResponse(BaseModel):
    """Response from optimization run."""

    run_id: str = Field(..., description="Unique run identifier")
    status: RunStatus = Field(..., description="Run status")
    problem_type: ProblemType = Field(..., description="Problem type")
    problem_params: Dict[str, Any] = Field(..., description="Problem parameters")
    results: Dict[SolverType, SolverResult] = Field(
        default_factory=dict, description="Results by solver"
    )
    metrics: Optional[Metrics] = Field(default=None, description="Benchmarking metrics")
    created_at: datetime = Field(..., description="Creation timestamp")
    completed_at: Optional[datetime] = Field(
        default=None, description="Completion timestamp"
    )
    error: Optional[str] = Field(default=None, description="Error message if failed")
    cache_hit: bool = Field(default=False, description="Whether result was cached")


# Health Check
class HealthResponse(BaseModel):
    """API health status."""

    status: str = Field(..., description="Overall status")
    version: str = Field(..., description="API version")
    backends_available: Dict[str, bool] = Field(
        ..., description="Backend availability"
    )
    features: Dict[str, bool] = Field(..., description="Feature flags")


# Problem Info
class ProblemInfo(BaseModel):
    """Information about a problem type."""

    type: ProblemType = Field(..., description="Problem type")
    description: str = Field(..., description="Problem description")
    parameters: Dict[str, Any] = Field(..., description="Parameter schema")
    constraints: List[str] = Field(..., description="Problem constraints")


class ListProblemsResponse(BaseModel):
    """List of available problems."""

    problems: List[ProblemInfo] = Field(..., description="Available problem types")
