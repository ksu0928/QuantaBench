"""FastAPI application for QuantaBench backend.

This module provides REST API endpoints for quantum optimization,
exposing the complete pipeline to the React frontend.
"""

from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, List

import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import __version__
from .config import get_settings
from .problems.portfolio import PortfolioOptimization
from .schemas import (
    BackendType,
    HealthResponse,
    ListProblemsResponse,
    OptimizationRequest,
    OptimizationResponse,
    ProblemInfo,
    ProblemType,
    RunStatus,
    SolverType,
)
from .services.cache import build_cache_params, get_cache
from .services.pipeline import OptimizationPipeline
from .services.runs import get_registry


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager.
    
    Handles startup and shutdown tasks.
    """
    # Startup
    settings = get_settings()
    print(f"Starting QuantaBench Backend v{__version__}")
    print(f"Environment: {settings.env}")
    print(f"Cache enabled: {settings.cache_enabled}")
    print(f"Classiq enabled: {settings.enable_classiq}")
    print(f"qBraid enabled: {settings.enable_qbraid}")
    
    # Load sample data
    app.state.sample_returns = _load_sample_returns()
    
    yield
    
    # Shutdown
    print("Shutting down QuantaBench Backend")


app = FastAPI(
    title="QuantaBench API",
    description="Track-agnostic quantum optimization workbench",
    version=__version__,
    lifespan=lifespan,
)

# Configure CORS
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _load_sample_returns() -> np.ndarray:
    """Load sample stock returns data.
    
    Returns:
        Returns array (T x N) for N assets over T days
    """
    # TODO: Load from backend/app/data/returns_sample.csv when available
    # For now, generate synthetic data
    np.random.seed(42)
    T, N = 252, 20  # 1 year of daily data, 20 assets
    returns = np.random.randn(T, N) * 0.015  # 1.5% daily volatility
    # Add some drift
    returns += np.random.randn(N) * 0.0005  # Small positive drift
    return returns


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint."""
    return {
        "name": "QuantaBench API",
        "version": __version__,
        "status": "online",
        "docs": "/docs",
    }


@app.get("/api/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Health check endpoint with backend availability.
    
    Returns backend status for Classiq, qBraid, and Aer.
    """
    settings = get_settings()
    
    # Check backend availability
    backends_available = {
        "aer": True,  # Always available
        "classiq": settings.enable_classiq and settings.is_classiq_configured(),
        "qbraid": settings.enable_qbraid and settings.is_qbraid_configured(),
    }
    
    features = {
        "cache": settings.cache_enabled,
        "hardware": settings.enable_hardware,
        "classiq_synthesis": settings.enable_classiq,
        "qbraid_execution": settings.enable_qbraid,
    }
    
    return HealthResponse(
        status="healthy",
        version=__version__,
        backends_available=backends_available,
        features=features,
    )


@app.get("/api/problems", response_model=ListProblemsResponse, tags=["Problems"])
async def list_problems():
    """List available optimization problems.
    
    Returns information about supported problem types.
    """
    problems = [
        ProblemInfo(
            type=ProblemType.PORTFOLIO,
            description="Mean-variance portfolio optimization with cardinality constraints",
            parameters={
                "num_assets": "int (2-20): Number of assets",
                "target_size": "int (1-num_assets): Target portfolio size",
                "risk_factor": "float (0-1): Risk aversion (0=max return, 1=min risk)",
                "seed": "int (optional): Random seed for reproducibility",
            },
            constraints=["Exactly K assets must be selected"],
        ),
        ProblemInfo(
            type=ProblemType.MAXCUT,
            description="Graph Max-Cut problem (stretch goal)",
            parameters={
                "num_nodes": "int (3-20): Number of graph nodes",
                "edge_probability": "float (0-1): Edge probability for random graph",
                "seed": "int (optional): Random seed",
            },
            constraints=["None (all solutions feasible)"],
        ),
    ]
    
    return ListProblemsResponse(problems=problems)


@app.post("/api/optimize", response_model=OptimizationResponse, tags=["Optimization"])
async def optimize(request: OptimizationRequest):
    """Run optimization with requested solvers.
    
    This is the main endpoint that:
    1. Checks cache for existing results
    2. Creates the problem instance
    3. Runs all requested solvers
    4. Calculates metrics
    5. Caches results
    6. Returns comprehensive response
    """
    registry = get_registry()
    cache = get_cache()
    
    # Create run in registry
    run_id = registry.create_run(
        problem_type=request.problem_type.value,
        problem_params=request.problem_params,
        solvers=[s.value for s in request.solvers],
    )
    
    try:
        # Build cache parameters
        cache_params = build_cache_params(
            problem_type=request.problem_type.value,
            problem_params=request.problem_params,
            solvers=[s.value for s in request.solvers],
            qaoa_params=request.qaoa_params.dict() if request.qaoa_params else None,
        )
        
        # Check cache if enabled
        if request.use_cache:
            cached = cache.get(cache_params)
            if cached is not None:
                print(f"Cache hit for run {run_id}")
                
                # Restore cached results
                registry.update_results(
                    run_id,
                    cached.get("results", {}),
                    cached.get("metrics"),
                )
                registry.set_cached(run_id)
                
                run = registry.get_run(run_id)
                return run
        
        # Create problem
        registry.update_status(run_id, RunStatus.RUNNING)
        problem = _create_problem(request.problem_type, request.problem_params)
        
        # Run optimization pipeline
        pipeline = OptimizationPipeline(problem)
        results = pipeline.run_solvers(request.solvers, request.qaoa_params)
        metrics = pipeline.calculate_metrics()
        
        # Update registry
        registry.update_results(run_id, results, metrics)
        registry.update_status(run_id, RunStatus.COMPLETED)
        
        # Cache results
        if request.use_cache:
            cache_data = {
                "results": results,
                "metrics": metrics,
                "run_id": run_id,
            }
            cache.set(cache_params, cache_data)
        
        # Return response
        run = registry.get_run(run_id)
        return run
        
    except Exception as e:
        # Mark as failed
        error_msg = str(e)
        registry.set_error(run_id, error_msg)
        
        raise HTTPException(
            status_code=500,
            detail=f"Optimization failed: {error_msg}",
        )


@app.get("/api/runs/{run_id}", response_model=OptimizationResponse, tags=["Runs"])
async def get_run(run_id: str):
    """Get optimization run by ID.
    
    Allows retrieving results from previous runs.
    """
    registry = get_registry()
    run = registry.get_run(run_id)
    
    if run is None:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    
    return run


@app.get("/api/runs", response_model=List[OptimizationResponse], tags=["Runs"])
async def list_runs(
    limit: int = 10,
    status: RunStatus = None,
):
    """List recent optimization runs.
    
    Args:
        limit: Maximum number of runs to return (default 10)
        status: Filter by status (optional)
    """
    registry = get_registry()
    runs = registry.list_runs(limit=limit, status_filter=status)
    return runs


@app.delete("/api/runs/{run_id}", tags=["Runs"])
async def delete_run(run_id: str):
    """Delete an optimization run."""
    registry = get_registry()
    deleted = registry.delete_run(run_id)
    
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    
    return {"status": "deleted", "run_id": run_id}


@app.post("/api/cache/clear", tags=["Cache"])
async def clear_cache():
    """Clear all cached results.
    
    Useful for testing or when problem definitions change.
    """
    cache = get_cache()
    count = cache.clear_all()
    
    return {
        "status": "cleared",
        "entries_deleted": count,
    }


@app.get("/api/cache/stats", tags=["Cache"])
async def cache_stats():
    """Get cache statistics."""
    cache = get_cache()
    stats = cache.get_stats()
    return stats


@app.get("/api/registry/stats", tags=["Registry"])
async def registry_stats():
    """Get run registry statistics."""
    registry = get_registry()
    stats = registry.get_stats()
    return stats


@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    """Handle ValueError exceptions."""
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc)},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions."""
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"},
    )


def _create_problem(problem_type: ProblemType, params: Dict):
    """Create problem instance from request parameters.
    
    Args:
        problem_type: Type of problem
        params: Problem parameters
        
    Returns:
        Problem instance
        
    Raises:
        ValueError: If parameters are invalid
    """
    if problem_type == ProblemType.PORTFOLIO:
        # Get sample returns
        returns = app.state.sample_returns
        
        return PortfolioOptimization(
            returns=returns,
            num_assets=params["num_assets"],
            target_size=params["target_size"],
            risk_factor=params.get("risk_factor", 0.5),
            lambda_penalty=params.get("lambda_penalty"),
            seed=params.get("seed"),
        )
    
    elif problem_type == ProblemType.MAXCUT:
        from .problems.maxcut import MaxCutOptimization
        
        return MaxCutOptimization(
            num_nodes=params["num_nodes"],
            edge_probability=params.get("edge_probability", 0.5),
            seed=params.get("seed"),
        )
    
    else:
        raise ValueError(f"Unknown problem type: {problem_type}")


if __name__ == "__main__":
    import uvicorn
    
    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
    )
