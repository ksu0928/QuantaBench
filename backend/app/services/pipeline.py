"""Pipeline orchestration for running optimization problems through multiple solvers.

This module coordinates the execution of quantum and classical solvers, collects
results, calculates metrics, and produces comprehensive benchmarking reports.
"""

import time
from typing import Dict, List, Optional

import numpy as np

from ..classical.annealing import solve_simulated_annealing
from ..classical.brute_force import solve_brute_force
from ..classical.greedy import solve_greedy
from ..config import get_settings
from ..metrics import generate_benchmarking_report
from ..problems.base import Problem
from ..quantum.backends import BackendManager, get_backend_manager
from ..quantum.hamiltonian import qubo_to_ising
from ..quantum.optimizer import optimize_qaoa_single
from ..quantum.qaoa_classiq import ClassiqQAOACircuit, get_best_bitstring_from_counts
from ..schemas import (
    Metrics,
    QAOAParams,
    RunStatus,
    Solution,
    SolverResult,
    SolverType,
    SynthesisReport,
)


class OptimizationPipeline:
    """Orchestrates optimization across quantum and classical solvers."""

    def __init__(
        self,
        problem: Problem,
        backend_manager: Optional[BackendManager] = None,
    ):
        """Initialize optimization pipeline.
        
        Args:
            problem: Problem instance to solve
            backend_manager: Backend manager (uses global if None)
        """
        self.problem = problem
        self.backend_manager = backend_manager or get_backend_manager()
        self.settings = get_settings()

        # Results storage
        self.results: Dict[SolverType, SolverResult] = {}
        self.optimal_bitstring: Optional[str] = None
        self.optimal_objective: Optional[float] = None

    def run_quantum_qaoa(
        self,
        qaoa_params: QAOAParams,
    ) -> SolverResult:
        """Run QAOA quantum optimization.
        
        Args:
            qaoa_params: QAOA parameters
            
        Returns:
            SolverResult with QAOA solution
        """
        print(f"\n{'='*60}")
        print("Running Quantum QAOA Solver")
        print(f"{'='*60}")

        start_time = time.time()

        try:
            # Build Ising Hamiltonian
            Q, qubo_offset = self.problem.get_qubo_matrix()
            h, J, ising_offset = qubo_to_ising(Q, qubo_offset)

            # Create QAOA circuit
            qaoa_circuit = ClassiqQAOACircuit(
                h, J, ising_offset,
                max_circuit_width=qaoa_params.max_circuit_width,
                max_circuit_depth=qaoa_params.max_circuit_depth,
            )

            # Optimize parameters
            optimization_result = optimize_qaoa_single(
                qaoa_circuit=qaoa_circuit,
                backend_manager=self.backend_manager,
                p=qaoa_params.p,
                backend_name=qaoa_params.backend.value,
                shots=qaoa_params.shots,
                max_restarts=qaoa_params.optimizer_restarts,
                maxiter=200,
                seed=None,  # Use problem seed if available
            )

            # Get best solution from optimization
            # Execute final circuit to get counts
            qiskit_circuit = qaoa_circuit.to_qiskit(optimization_result.best_params)
            final_result, fell_back = self.backend_manager.execute_with_fallback(
                qaoa_params.backend.value,
                qiskit_circuit,
                shots=qaoa_params.shots,
            )

            # Get best bitstring from counts
            best_bitstring = get_best_bitstring_from_counts(final_result.counts)
            decoded = self.problem.decode_solution(best_bitstring)

            # Create solution
            best_solution = Solution(
                bitstring=best_bitstring,
                selected_indices=decoded.get("selected_indices", []),
                objective_value=self.problem.evaluate_objective(best_bitstring),
                is_feasible=self.problem.is_feasible(best_bitstring),
                probability=final_result.counts.get(best_bitstring, 0) / qaoa_params.shots,
            )

            # Collect all solutions from counts
            all_solutions = []
            for bitstring, count in sorted(
                final_result.counts.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]:  # Top 10
                all_solutions.append(Solution(
                    bitstring=bitstring,
                    selected_indices=self.problem.decode_solution(bitstring).get(
                        "selected_indices", []
                    ),
                    objective_value=self.problem.evaluate_objective(bitstring),
                    is_feasible=self.problem.is_feasible(bitstring),
                    probability=count / qaoa_params.shots,
                ))

            runtime = time.time() - start_time

            # Synthesis report (if available)
            synthesis_report = None
            circuit_info = qaoa_circuit.get_circuit_info()
            if circuit_info:
                # Create synthesis report from Qiskit circuit as fallback
                qc = qaoa_circuit.to_qiskit(optimization_result.best_params)
                synthesis_report = SynthesisReport(
                    num_qubits=qc.num_qubits,
                    circuit_depth=qc.depth(),
                    gate_counts=dict(qc.count_ops()),
                    synthesis_time_s=0.0,  # Not available for Qiskit fallback
                )

            return SolverResult(
                solver=SolverType.QUANTUM_QAOA,
                best_solution=best_solution,
                all_solutions=all_solutions,
                runtime_s=runtime,
                backend_used=final_result.backend_name,
                synthesis_report=synthesis_report,
                optimizer_iterations=optimization_result.num_iterations,
                final_parameters=optimization_result.best_params.to_flat_array().tolist(),
            )

        except Exception as e:
            print(f"Error in QAOA: {e}")
            raise

    def run_brute_force(self) -> SolverResult:
        """Run brute force exact solver.
        
        Returns:
            SolverResult with exact solution
        """
        print(f"\n{'='*60}")
        print("Running Brute Force Exact Solver")
        print(f"{'='*60}")

        solution = solve_brute_force(self.problem)

        # Store optimal for comparison
        self.optimal_bitstring = solution.best_bitstring
        self.optimal_objective = solution.best_objective

        decoded = self.problem.decode_solution(solution.best_bitstring)

        best_solution = Solution(
            bitstring=solution.best_bitstring,
            selected_indices=decoded.get("selected_indices", []),
            objective_value=solution.best_objective,
            is_feasible=self.problem.is_feasible(solution.best_bitstring),
        )

        # Top solutions
        all_solutions = [
            Solution(
                bitstring=bitstring,
                selected_indices=self.problem.decode_solution(bitstring).get(
                    "selected_indices", []
                ),
                objective_value=obj,
                is_feasible=self.problem.is_feasible(bitstring),
            )
            for bitstring, obj in solution.all_feasible_solutions[:10]
        ]

        return SolverResult(
            solver=SolverType.BRUTE_FORCE,
            best_solution=best_solution,
            all_solutions=all_solutions,
            runtime_s=solution.runtime_s,
        )

    def run_simulated_annealing(self, seed: Optional[int] = None) -> SolverResult:
        """Run simulated annealing solver.
        
        Args:
            seed: Random seed
            
        Returns:
            SolverResult with annealing solution
        """
        print(f"\n{'='*60}")
        print("Running Simulated Annealing Solver")
        print(f"{'='*60}")

        solution = solve_simulated_annealing(
            self.problem,
            initial_temperature=10.0,
            cooling_rate=0.95,
            max_iterations=10000,
            seed=seed,
        )

        decoded = self.problem.decode_solution(solution.best_bitstring)

        best_solution = Solution(
            bitstring=solution.best_bitstring,
            selected_indices=decoded.get("selected_indices", []),
            objective_value=solution.best_objective,
            is_feasible=self.problem.is_feasible(solution.best_bitstring),
        )

        return SolverResult(
            solver=SolverType.SIMULATED_ANNEALING,
            best_solution=best_solution,
            all_solutions=[best_solution],  # SA only tracks best
            runtime_s=solution.runtime_s,
        )

    def run_greedy(self) -> SolverResult:
        """Run greedy heuristic solver.
        
        Returns:
            SolverResult with greedy solution
        """
        print(f"\n{'='*60}")
        print("Running Greedy Heuristic Solver")
        print(f"{'='*60}")

        solution = solve_greedy(self.problem)

        decoded = self.problem.decode_solution(solution.best_bitstring)

        best_solution = Solution(
            bitstring=solution.best_bitstring,
            selected_indices=decoded.get("selected_indices", []),
            objective_value=solution.best_objective,
            is_feasible=self.problem.is_feasible(solution.best_bitstring),
        )

        return SolverResult(
            solver=SolverType.GREEDY,
            best_solution=best_solution,
            all_solutions=[best_solution],  # Greedy is deterministic
            runtime_s=solution.runtime_s,
        )

    def run_solvers(
        self,
        solvers: List[SolverType],
        qaoa_params: Optional[QAOAParams] = None,
    ) -> Dict[SolverType, SolverResult]:
        """Run all requested solvers.
        
        Args:
            solvers: List of solvers to run
            qaoa_params: QAOA parameters (required if QUANTUM_QAOA in solvers)
            
        Returns:
            Dict mapping solver type to results
        """
        results = {}

        for solver in solvers:
            try:
                if solver == SolverType.QUANTUM_QAOA:
                    if qaoa_params is None:
                        raise ValueError("qaoa_params required for QUANTUM_QAOA")
                    results[solver] = self.run_quantum_qaoa(qaoa_params)

                elif solver == SolverType.BRUTE_FORCE:
                    results[solver] = self.run_brute_force()

                elif solver == SolverType.SIMULATED_ANNEALING:
                    results[solver] = self.run_simulated_annealing()

                elif solver == SolverType.GREEDY:
                    results[solver] = self.run_greedy()

                else:
                    print(f"Warning: Unknown solver {solver}")

            except Exception as e:
                print(f"Error running {solver}: {e}")
                # Continue with other solvers

        self.results = results
        return results

    def calculate_metrics(self) -> Metrics:
        """Calculate comprehensive metrics across all solver results.
        
        Returns:
            Metrics object
        """
        if not self.results:
            raise ValueError("No results to calculate metrics from")

        # Prepare solver results for benchmarking
        solver_results = {}
        for solver_type, result in self.results.items():
            solver_results[solver_type.value] = {
                "best_bitstring": result.best_solution.bitstring,
                "best_objective": result.best_solution.objective_value,
                "runtime_s": result.runtime_s,
            }

        # Generate benchmarking report
        report = generate_benchmarking_report(
            solver_results,
            self.problem,
            optimal_objective=self.optimal_objective,
        )

        # Extract metrics
        comparison = report["comparison"]
        best_solver = comparison["best_solver"]

        # Calculate probability of optimal (for quantum)
        prob_optimal = None
        if SolverType.QUANTUM_QAOA in self.results and self.optimal_bitstring:
            qaoa_result = self.results[SolverType.QUANTUM_QAOA]
            # Find optimal in all solutions
            for sol in qaoa_result.all_solutions:
                if sol.bitstring == self.optimal_bitstring:
                    prob_optimal = sol.probability
                    break

        # Feasibility rate
        feasible_count = sum(
            1 for r in self.results.values() if r.best_solution.is_feasible
        )
        feasibility_rate = feasible_count / len(self.results)

        # Sharpe ratio (portfolio-specific)
        sharpe_ratio = None
        if hasattr(self.problem, "calculate_sharpe_ratio"):
            best_result = self.results[SolverType(best_solver)]
            if best_result.best_solution.is_feasible:
                sharpe_ratio = self.problem.calculate_sharpe_ratio(
                    best_result.best_solution.bitstring
                )

        # Approximation ratio
        approximation_ratio = None
        if self.optimal_objective is not None:
            best_obj = comparison["best_objective"]
            approximation_ratio = best_obj / self.optimal_objective

        return Metrics(
            approximation_ratio=approximation_ratio,
            prob_optimal=prob_optimal,
            feasibility_rate=feasibility_rate,
            sharpe_ratio=sharpe_ratio,
            best_objective=comparison["best_objective"],
            optimal_objective=self.optimal_objective,
        )

    def get_results_summary(self) -> Dict:
        """Get summary of results for logging/display.
        
        Returns:
            Summary dict
        """
        summary = {
            "num_solvers": len(self.results),
            "solvers_run": [s.value for s in self.results.keys()],
        }

        if self.results:
            # Best solver
            best_solver = min(
                self.results.items(),
                key=lambda x: x[1].best_solution.objective_value
            )
            summary["best_solver"] = best_solver[0].value
            summary["best_objective"] = best_solver[1].best_solution.objective_value

            # All objectives
            summary["objectives"] = {
                solver.value: result.best_solution.objective_value
                for solver, result in self.results.items()
            }

            # Runtimes
            summary["runtimes_s"] = {
                solver.value: result.runtime_s
                for solver, result in self.results.items()
            }

        return summary


def run_optimization_pipeline(
    problem: Problem,
    solvers: List[SolverType],
    qaoa_params: Optional[QAOAParams] = None,
    backend_manager: Optional[BackendManager] = None,
) -> tuple[Dict[SolverType, SolverResult], Metrics]:
    """Run complete optimization pipeline (convenience function).
    
    Args:
        problem: Problem to solve
        solvers: List of solvers to run
        qaoa_params: QAOA parameters (if needed)
        backend_manager: Backend manager
        
    Returns:
        Tuple of (results dict, metrics)
    """
    pipeline = OptimizationPipeline(problem, backend_manager)
    results = pipeline.run_solvers(solvers, qaoa_params)
    metrics = pipeline.calculate_metrics()

    # Print summary
    summary = pipeline.get_results_summary()
    print(f"\n{'='*60}")
    print("Optimization Pipeline Complete")
    print(f"{'='*60}")
    print(f"Solvers run: {', '.join(summary['solvers_run'])}")
    print(f"Best solver: {summary['best_solver']}")
    print(f"Best objective: {summary['best_objective']:.4f}")
    if pipeline.optimal_objective:
        print(f"Optimal objective: {pipeline.optimal_objective:.4f}")
    print(f"{'='*60}\n")

    return results, metrics
