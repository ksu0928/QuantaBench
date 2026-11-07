#!/usr/bin/env python3
"""
Precompute cached results for common demo scenarios.

This script runs the optimization pipeline for typical demo configurations
and stores results in the cache, ensuring fast, deterministic demo behavior.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import get_settings
from app.problems.portfolio import PortfolioProblem
from app.services.pipeline import OptimizationPipeline
from app.services.cache import ResultCache
from app.services.runs import RunRegistry


async def precompute_scenario(
    pipeline: OptimizationPipeline,
    problem: PortfolioProblem,
    n_assets: int,
    budget: int,
    p: int,
    shots: int,
    seed: int,
    scenario_name: str,
) -> None:
    """Precompute and cache a single scenario."""
    print(f"\n{'='*60}")
    print(f"Scenario: {scenario_name}")
    print(f"  n_assets={n_assets}, budget={budget}, p={p}, shots={shots}, seed={seed}")
    print(f"{'='*60}")
    
    try:
        result = await pipeline.run_optimization(
            problem=problem,
            p=p,
            shots=shots,
            seed=seed,
            quantum_backend="aer_simulator",  # Use Aer for deterministic precompute
        )
        
        print(f"✓ Completed in {result.execution_time_seconds:.2f}s")
        print(f"  Run ID: {result.run_id}")
        print(f"  Quantum objective: {result.quantum_result.objective_value:.6f}")
        print(f"  Best classical objective: {result.best_classical_result.objective_value:.6f}")
        
        if result.quantum_result.is_feasible:
            print(f"  Quantum solution is feasible")
        else:
            print(f"  Quantum solution violated constraints")
            
        if result.metrics.approximation_ratio is not None:
            print(f"  Approximation ratio: {result.metrics.approximation_ratio:.4f}")
        
    except Exception as e:
        print(f"✗ Failed: {str(e)}")
        import traceback
        traceback.print_exc()


async def main():
    """Precompute common demo scenarios."""
    print("QuantaBench Demo Precompute Script")
    print("=" * 60)
    
    # Initialize services
    settings = get_settings()
    cache = ResultCache(settings)
    registry = RunRegistry(settings)
    pipeline = OptimizationPipeline(settings, cache, registry)
    
    # Load sample data
    data_path = Path(__file__).parent.parent / "app" / "data" / "returns_sample.csv"
    if not data_path.exists():
        print(f"ERROR: Sample data not found at {data_path}")
        return
    
    # Demo scenarios: (n_assets, budget, p, shots, seed, name)
    scenarios = [
        # Small problem - fast, good for quick demos
        (5, 2, 1, 1024, 42, "Small: 5 assets, p=1"),
        (5, 2, 2, 1024, 42, "Small: 5 assets, p=2"),
        
        # Medium problem - shows tradeoffs
        (8, 3, 1, 2048, 42, "Medium: 8 assets, p=1"),
        (8, 3, 2, 2048, 42, "Medium: 8 assets, p=2"),
        
        # Larger problem - demonstrates scaling
        (10, 4, 1, 2048, 42, "Large: 10 assets, p=1"),
        (10, 4, 2, 2048, 42, "Large: 10 assets, p=2"),
        
        # Different seeds for same problem
        (8, 3, 1, 2048, 123, "Medium: 8 assets, seed=123"),
        (8, 3, 1, 2048, 456, "Medium: 8 assets, seed=456"),
        
        # Higher p values
        (6, 2, 3, 1024, 42, "Small: 6 assets, p=3"),
        (6, 2, 4, 1024, 42, "Small: 6 assets, p=4"),
    ]
    
    total_scenarios = len(scenarios)
    print(f"\nPrecomputing {total_scenarios} scenarios...")
    
    for idx, (n_assets, budget, p, shots, seed, name) in enumerate(scenarios, 1):
        print(f"\n[{idx}/{total_scenarios}]", end=" ")
        
        # Create portfolio problem
        problem = PortfolioProblem(
            returns_file=str(data_path),
            n_assets=n_assets,
            budget=budget,
            risk_aversion=0.5,
        )
        
        await precompute_scenario(
            pipeline=pipeline,
            problem=problem,
            n_assets=n_assets,
            budget=budget,
            p=p,
            shots=shots,
            seed=seed,
            scenario_name=name,
        )
        
        # Small delay to avoid overwhelming the system
        await asyncio.sleep(0.5)
    
    # Print cache statistics
    print(f"\n{'='*60}")
    print("Precompute Complete!")
    print(f"{'='*60}")
    print(f"\nCache location: {settings.cache_dir}")
    
    # Count cache files
    cache_files = list(Path(settings.cache_dir).glob("*.json"))
    print(f"Total cache entries: {len(cache_files)}")
    
    # Estimate cache size
    total_size = sum(f.stat().st_size for f in cache_files)
    print(f"Total cache size: {total_size / 1024:.1f} KB")
    
    print("\nThese results are now cached and will be returned instantly")
    print("when the same parameters are requested via the API.")
    print("\nSuggested demo parameters:")
    print("  - Small: n_assets=5, budget=2, p=1-2")
    print("  - Medium: n_assets=8, budget=3, p=1-2")
    print("  - Large: n_assets=10, budget=4, p=1-2")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nPrecompute interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nFATAL ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
