"""QAOA parameter optimization using COBYLA with warm-start and restarts.

This module implements a robust optimization strategy for QAOA:
1. Warm-start: Initialize p-layer params from optimized (p-1)-layer params
2. Multiple restarts: Try several initial points to avoid local minima
3. Progress tracking: Monitor convergence and best results
"""

import time
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np
from scipy.optimize import minimize

from .qaoa_classiq import (
    ClassiqQAOACircuit,
    QAOAParameters,
    evaluate_qaoa_energy,
    get_best_bitstring_from_counts,
)
from .backends import BackendManager


@dataclass
class OptimizationResult:
    """Result from QAOA parameter optimization."""

    best_params: QAOAParameters
    best_energy: float
    num_iterations: int
    num_function_evals: int
    optimization_time_s: float
    convergence_history: List[float]
    restart_energies: List[float]
    success: bool


class QAOAOptimizer:
    """QAOA parameter optimizer with COBYLA, warm-start, and restarts."""

    def __init__(
        self,
        qaoa_circuit: ClassiqQAOACircuit,
        backend_manager: BackendManager,
        backend_name: str = "aer_simulator",
        shots: int = 1024,
        max_restarts: int = 3,
        seed: Optional[int] = None,
    ):
        """Initialize QAOA optimizer.
        
        Args:
            qaoa_circuit: ClassiqQAOACircuit instance
            backend_manager: Backend manager for circuit execution
            backend_name: Name of backend to use
            shots: Number of measurement shots per evaluation
            max_restarts: Maximum number of random restarts
            seed: Random seed for reproducibility
        """
        self.qaoa_circuit = qaoa_circuit
        self.backend_manager = backend_manager
        self.backend_name = backend_name
        self.shots = shots
        self.max_restarts = max_restarts
        self.rng = np.random.default_rng(seed)
        self.seed = seed

        # Optimization history
        self._iteration_count = 0
        self._function_eval_count = 0
        self._convergence_history: List[float] = []
        self._best_energy = float("inf")
        self._best_params: Optional[QAOAParameters] = None

    def optimize(
        self,
        p: int,
        warm_start_params: Optional[QAOAParameters] = None,
        maxiter: int = 200,
    ) -> OptimizationResult:
        """Optimize QAOA parameters for p layers.
        
        Strategy:
        1. If warm_start_params provided (from p-1), use as initial point
        2. Otherwise, try multiple random initializations
        3. Use COBYLA (derivative-free, handles noise well)
        4. Return best result across all restarts
        
        Args:
            p: Number of QAOA layers
            warm_start_params: Optional parameters from p-1 optimization
            maxiter: Maximum iterations per restart
            
        Returns:
            OptimizationResult with best parameters found
        """
        start_time = time.time()

        restart_energies = []
        best_result = None
        best_energy_overall = float("inf")

        # Determine number of restarts
        if warm_start_params is not None:
            # Warm start: one optimization from transferred params
            num_restarts = 1
            initial_points = [self._warm_start_initialization(warm_start_params, p)]
        else:
            # Cold start: multiple random initializations
            num_restarts = self.max_restarts
            initial_points = [
                QAOAParameters.random_init(p, seed=self.seed + i if self.seed else None)
                for i in range(num_restarts)
            ]

        # Run optimizations
        for restart_idx, init_params in enumerate(initial_points):
            print(f"Optimization restart {restart_idx + 1}/{num_restarts}")

            # Reset counters for this restart
            self._iteration_count = 0
            self._function_eval_count = 0
            self._convergence_history = []

            # Run COBYLA
            result = self._run_cobyla(init_params, maxiter)

            restart_energies.append(result["best_energy"])

            # Track best across restarts
            if result["best_energy"] < best_energy_overall:
                best_energy_overall = result["best_energy"]
                best_result = result

        optimization_time = time.time() - start_time

        return OptimizationResult(
            best_params=best_result["best_params"],
            best_energy=best_result["best_energy"],
            num_iterations=best_result["num_iterations"],
            num_function_evals=best_result["num_function_evals"],
            optimization_time_s=optimization_time,
            convergence_history=best_result["convergence_history"],
            restart_energies=restart_energies,
            success=best_result["success"],
        )

    def _warm_start_initialization(
        self,
        prev_params: QAOAParameters,
        new_p: int,
    ) -> QAOAParameters:
        """Initialize p-layer params from optimized (p-1)-layer params.
        
        Strategy: Interleave previous parameters and add new layer with small random values.
        
        Example: p=2 → p=3
        Old: [γ₀, β₀, γ₁, β₁]
        New: [γ₀, β₀, γ₁, β₁, γ₂, β₂]  where γ₂, β₂ are small random
        
        Args:
            prev_params: Optimized parameters from p-1 layers
            new_p: Target number of layers
            
        Returns:
            Initialized parameters for new_p layers
        """
        old_p = prev_params.p

        if new_p <= old_p:
            # Just truncate if needed (shouldn't happen in normal usage)
            return QAOAParameters(
                p=new_p,
                gamma=prev_params.gamma[:new_p],
                beta=prev_params.beta[:new_p],
            )

        # Start with old parameters
        new_gamma = np.zeros(new_p)
        new_beta = np.zeros(new_p)

        new_gamma[:old_p] = prev_params.gamma
        new_beta[:old_p] = prev_params.beta

        # Initialize new layers with small random perturbations
        for i in range(old_p, new_p):
            new_gamma[i] = self.rng.uniform(0, 0.5)  # Small gamma
            new_beta[i] = self.rng.uniform(0, 0.5)   # Small beta

        return QAOAParameters(p=new_p, gamma=new_gamma, beta=new_beta)

    def _run_cobyla(
        self,
        init_params: QAOAParameters,
        maxiter: int,
    ) -> Dict:
        """Run COBYLA optimization from initial parameters.
        
        Args:
            init_params: Initial QAOA parameters
            maxiter: Maximum iterations
            
        Returns:
            Dict with optimization results
        """
        # Convert to flat array for scipy
        x0 = init_params.to_flat_array()

        # Define objective function
        def objective(x_flat):
            params = QAOAParameters.from_flat_array(x_flat, p=init_params.p)
            energy = self._evaluate_energy(params)
            return energy

        # Run COBYLA
        try:
            result = minimize(
                objective,
                x0,
                method="COBYLA",
                options={
                    "maxiter": maxiter,
                    "rhobeg": 0.5,  # Initial step size
                    "tol": 1e-6,    # Tolerance
                },
            )

            best_params = QAOAParameters.from_flat_array(result.x, p=init_params.p)
            best_energy = result.fun
            success = result.success

        except Exception as e:
            print(f"Warning: Optimization failed: {e}")
            # Return initial parameters as fallback
            best_params = init_params
            best_energy = self._evaluate_energy(init_params)
            success = False

        return {
            "best_params": best_params,
            "best_energy": best_energy,
            "num_iterations": self._iteration_count,
            "num_function_evals": self._function_eval_count,
            "convergence_history": self._convergence_history.copy(),
            "success": success,
        }

    def _evaluate_energy(self, params: QAOAParameters) -> float:
        """Evaluate expected energy for given parameters.
        
        This is the objective function for optimization.
        
        Args:
            params: QAOA parameters
            
        Returns:
            Expected energy ⟨H⟩
        """
        self._iteration_count += 1
        self._function_eval_count += 1

        try:
            # Convert QAOA circuit to Qiskit (fallback if Classiq not available)
            qiskit_circuit = self.qaoa_circuit.to_qiskit(params)

            # Execute circuit
            result, _ = self.backend_manager.execute_with_fallback(
                self.backend_name,
                qiskit_circuit,
                shots=self.shots,
                seed=self.seed,
            )

            # Evaluate energy from counts
            energy = evaluate_qaoa_energy(
                result.counts,
                self.qaoa_circuit.h,
                self.qaoa_circuit.J,
                self.qaoa_circuit.offset,
            )

            # Track convergence
            self._convergence_history.append(energy)

            # Track best
            if energy < self._best_energy:
                self._best_energy = energy
                self._best_params = params

            if self._iteration_count % 10 == 0:
                print(f"  Iteration {self._iteration_count}: energy = {energy:.4f}")

            return energy

        except Exception as e:
            print(f"Warning: Energy evaluation failed: {e}")
            # Return large penalty to guide optimizer away
            return 1e6


def optimize_qaoa_progressive(
    qaoa_circuit: ClassiqQAOACircuit,
    backend_manager: BackendManager,
    max_p: int,
    backend_name: str = "aer_simulator",
    shots: int = 1024,
    max_restarts: int = 3,
    maxiter_per_p: int = 200,
    seed: Optional[int] = None,
) -> Dict[int, OptimizationResult]:
    """Optimize QAOA progressively from p=1 to p=max_p with warm-start.
    
    This implements the warm-start strategy:
    - Optimize p=1 with random restarts
    - Use p=1 params to initialize p=2
    - Use p=2 params to initialize p=3
    - etc.
    
    Args:
        qaoa_circuit: ClassiqQAOACircuit instance
        backend_manager: Backend manager
        max_p: Maximum number of layers
        backend_name: Backend to use
        shots: Shots per evaluation
        max_restarts: Restarts for p=1 (subsequent p use warm-start)
        maxiter_per_p: Max iterations per p value
        seed: Random seed
        
    Returns:
        Dict mapping p → OptimizationResult
    """
    results = {}
    prev_params = None

    for p in range(1, max_p + 1):
        print(f"\n{'='*60}")
        print(f"Optimizing QAOA with p={p} layers")
        print(f"{'='*60}")

        optimizer = QAOAOptimizer(
            qaoa_circuit=qaoa_circuit,
            backend_manager=backend_manager,
            backend_name=backend_name,
            shots=shots,
            max_restarts=max_restarts,
            seed=seed,
        )

        result = optimizer.optimize(
            p=p,
            warm_start_params=prev_params,
            maxiter=maxiter_per_p,
        )

        results[p] = result

        print(f"\nResult for p={p}:")
        print(f"  Best energy: {result.best_energy:.6f}")
        print(f"  Function evals: {result.num_function_evals}")
        print(f"  Time: {result.optimization_time_s:.2f}s")

        # Use this result for warm-starting p+1
        prev_params = result.best_params

    return results


def optimize_qaoa_single(
    qaoa_circuit: ClassiqQAOACircuit,
    backend_manager: BackendManager,
    p: int,
    backend_name: str = "aer_simulator",
    shots: int = 1024,
    max_restarts: int = 3,
    maxiter: int = 200,
    seed: Optional[int] = None,
) -> OptimizationResult:
    """Optimize QAOA for a single p value (no warm-start).
    
    Args:
        qaoa_circuit: ClassiqQAOACircuit instance
        backend_manager: Backend manager
        p: Number of QAOA layers
        backend_name: Backend to use
        shots: Shots per evaluation
        max_restarts: Number of random restarts
        maxiter: Maximum iterations
        seed: Random seed
        
    Returns:
        OptimizationResult
    """
    optimizer = QAOAOptimizer(
        qaoa_circuit=qaoa_circuit,
        backend_manager=backend_manager,
        backend_name=backend_name,
        shots=shots,
        max_restarts=max_restarts,
        seed=seed,
    )

    return optimizer.optimize(
        p=p,
        warm_start_params=None,
        maxiter=maxiter,
    )
