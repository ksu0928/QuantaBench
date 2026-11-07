"""Metrics calculation for benchmarking quantum vs classical solvers.

This module provides honest, transparent metrics that report even when
classical methods outperform quantum approaches.
"""

from typing import Dict, List, Optional

import numpy as np

from .problems.base import Problem
from .problems.portfolio import PortfolioOptimization


def calculate_approximation_ratio(
    solution_objective: float,
    optimal_objective: float,
) -> float:
    """Calculate approximation ratio of solution vs optimal.
    
    Approximation ratio = solution_objective / optimal_objective
    
    For minimization problems:
    - Ratio = 1.0 means optimal
    - Ratio > 1.0 means worse than optimal
    - Ratio < 1.0 shouldn't happen (unless optimal is wrong)
    
    Args:
        solution_objective: Objective value of solution
        optimal_objective: Optimal objective value
        
    Returns:
        Approximation ratio
    """
    if optimal_objective == 0:
        # Handle edge case
        if solution_objective == 0:
            return 1.0
        else:
            return float("inf")
    
    return solution_objective / optimal_objective


def calculate_prob_optimal(
    counts: Dict[str, int],
    optimal_bitstring: str,
) -> float:
    """Calculate probability of measuring optimal solution.
    
    P(optimal) = count(optimal) / total_shots
    
    Args:
        counts: Measurement counts from quantum execution
        optimal_bitstring: Known optimal solution
        
    Returns:
        Probability of measuring optimal (0 to 1)
    """
    total_shots = sum(counts.values())
    optimal_count = counts.get(optimal_bitstring, 0)
    
    return optimal_count / total_shots if total_shots > 0 else 0.0


def calculate_feasibility_rate(
    counts: Dict[str, int],
    problem: Problem,
) -> float:
    """Calculate fraction of feasible solutions in measurement outcomes.
    
    Feasibility rate = (shots with feasible solutions) / total_shots
    
    Args:
        counts: Measurement counts
        problem: Problem instance for feasibility checking
        
    Returns:
        Feasibility rate (0 to 1)
    """
    total_shots = sum(counts.values())
    feasible_shots = 0
    
    for bitstring, count in counts.items():
        if problem.is_feasible(bitstring):
            feasible_shots += count
    
    return feasible_shots / total_shots if total_shots > 0 else 0.0


def calculate_sharpe_ratio(
    bitstring: str,
    problem: PortfolioOptimization,
) -> Optional[float]:
    """Calculate Sharpe ratio for portfolio solution.
    
    Sharpe ratio = portfolio_return / portfolio_volatility
    (Assuming risk-free rate = 0)
    
    Args:
        bitstring: Portfolio solution
        problem: PortfolioOptimization instance
        
    Returns:
        Sharpe ratio, or None if not applicable
    """
    if not isinstance(problem, PortfolioOptimization):
        return None
    
    if not problem.is_feasible(bitstring):
        return None
    
    return problem.calculate_sharpe_ratio(bitstring)


def calculate_solution_metrics(
    bitstring: str,
    problem: Problem,
    optimal_objective: Optional[float] = None,
) -> Dict[str, float]:
    """Calculate all metrics for a single solution.
    
    Args:
        bitstring: Solution to evaluate
        problem: Problem instance
        optimal_objective: Known optimal (if available)
        
    Returns:
        Dict of metrics
    """
    metrics = {
        "objective_value": problem.evaluate_objective(bitstring),
        "is_feasible": problem.is_feasible(bitstring),
    }
    
    # Approximation ratio (if optimal known)
    if optimal_objective is not None:
        metrics["approximation_ratio"] = calculate_approximation_ratio(
            metrics["objective_value"], optimal_objective
        )
    
    # Portfolio-specific metrics
    if isinstance(problem, PortfolioOptimization):
        portfolio_metrics = problem.calculate_metrics(bitstring)
        metrics.update({
            "sharpe_ratio": portfolio_metrics["sharpe_ratio"],
            "annual_return": portfolio_metrics["annual_return"],
            "annual_volatility": portfolio_metrics["annual_volatility"],
            "num_selected": portfolio_metrics["num_selected"],
        })
    
    return metrics


def calculate_quantum_metrics(
    counts: Dict[str, int],
    problem: Problem,
    optimal_bitstring: Optional[str] = None,
    optimal_objective: Optional[float] = None,
) -> Dict[str, any]:
    """Calculate comprehensive metrics for quantum execution results.
    
    Args:
        counts: Measurement counts from quantum circuit
        problem: Problem instance
        optimal_bitstring: Known optimal solution (if available)
        optimal_objective: Known optimal objective (if available)
        
    Returns:
        Dict of comprehensive metrics
    """
    # Best measured solution
    best_bitstring = max(counts.items(), key=lambda x: x[1])[0]
    best_objective = problem.evaluate_objective(best_bitstring)
    
    metrics = {
        "best_bitstring": best_bitstring,
        "best_objective": best_objective,
        "best_is_feasible": problem.is_feasible(best_bitstring),
        "feasibility_rate": calculate_feasibility_rate(counts, problem),
        "num_unique_solutions": len(counts),
        "total_shots": sum(counts.values()),
    }
    
    # Optimal comparison metrics
    if optimal_objective is not None:
        metrics["approximation_ratio"] = calculate_approximation_ratio(
            best_objective, optimal_objective
        )
        metrics["optimal_objective"] = optimal_objective
    
    if optimal_bitstring is not None:
        metrics["prob_optimal"] = calculate_prob_optimal(counts, optimal_bitstring)
        metrics["found_optimal"] = best_bitstring == optimal_bitstring
    
    # Portfolio-specific metrics
    if isinstance(problem, PortfolioOptimization) and metrics["best_is_feasible"]:
        metrics["sharpe_ratio"] = calculate_sharpe_ratio(best_bitstring, problem)
    
    return metrics


def compare_solvers(
    solver_results: Dict[str, Dict],
    problem: Problem,
    optimal_objective: Optional[float] = None,
) -> Dict[str, any]:
    """Compare results from multiple solvers (quantum and classical).
    
    Args:
        solver_results: Dict mapping solver_name → result dict
                       Each result should have 'best_bitstring' and 'best_objective'
        problem: Problem instance
        optimal_objective: Known optimal (if available)
        
    Returns:
        Comparison metrics including rankings and relative performance
    """
    # Extract objectives
    objectives = {
        name: result["best_objective"]
        for name, result in solver_results.items()
    }
    
    # Rank solvers by objective (lower is better)
    ranked = sorted(objectives.items(), key=lambda x: x[1])
    
    comparison = {
        "rankings": {name: i + 1 for i, (name, _) in enumerate(ranked)},
        "best_solver": ranked[0][0],
        "best_objective": ranked[0][1],
        "worst_solver": ranked[-1][0],
        "worst_objective": ranked[-1][1],
        "objective_spread": ranked[-1][1] - ranked[0][1],
    }
    
    # Approximation ratios vs best found
    best_found_objective = ranked[0][1]
    comparison["approximation_ratios_vs_best"] = {
        name: calculate_approximation_ratio(obj, best_found_objective)
        for name, obj in objectives.items()
    }
    
    # Approximation ratios vs optimal (if known)
    if optimal_objective is not None:
        comparison["approximation_ratios_vs_optimal"] = {
            name: calculate_approximation_ratio(obj, optimal_objective)
            for name, obj in objectives.items()
        }
        comparison["optimal_objective"] = optimal_objective
        
        # Check if any solver found optimal
        comparison["optimal_found_by"] = [
            name for name, obj in objectives.items()
            if abs(obj - optimal_objective) < 1e-6
        ]
    
    # Feasibility check
    comparison["all_feasible"] = all(
        problem.is_feasible(result["best_bitstring"])
        for result in solver_results.values()
    )
    
    comparison["feasible_solvers"] = [
        name for name, result in solver_results.items()
        if problem.is_feasible(result["best_bitstring"])
    ]
    
    return comparison


def calculate_portfolio_performance(
    bitstring: str,
    problem: PortfolioOptimization,
) -> Dict[str, float]:
    """Calculate comprehensive portfolio performance metrics.
    
    Args:
        bitstring: Portfolio solution
        problem: PortfolioOptimization instance
        
    Returns:
        Dict of portfolio metrics
    """
    if not problem.is_feasible(bitstring):
        return {
            "is_feasible": False,
            "error": "Solution is not feasible",
        }
    
    metrics = problem.calculate_metrics(bitstring)
    decoded = problem.decode_solution(bitstring)
    
    return {
        "is_feasible": True,
        "num_assets_selected": decoded["portfolio_size"],
        "selected_indices": decoded["selected_indices"],
        "annual_return": metrics["annual_return"],
        "annual_volatility": metrics["annual_volatility"],
        "sharpe_ratio": metrics["sharpe_ratio"],
        "variance": metrics["annual_variance"],
        "mean_return": decoded["mean_return"],
    }


def generate_benchmarking_report(
    solver_results: Dict[str, Dict],
    problem: Problem,
    optimal_objective: Optional[float] = None,
    include_portfolio_metrics: bool = True,
) -> Dict[str, any]:
    """Generate comprehensive benchmarking report.
    
    This is the main function for honest benchmarking that reports:
    - Which solver performed best
    - Approximation ratios for all solvers
    - Runtime comparisons
    - Feasibility rates
    - Portfolio-specific metrics (if applicable)
    
    Args:
        solver_results: Results from all solvers
        problem: Problem instance
        optimal_objective: Known optimal (if available)
        include_portfolio_metrics: Include portfolio-specific metrics
        
    Returns:
        Comprehensive benchmarking report
    """
    report = {
        "problem_info": problem.get_problem_info(),
        "num_solvers": len(solver_results),
        "solver_names": list(solver_results.keys()),
    }
    
    # Solver comparison
    report["comparison"] = compare_solvers(
        solver_results, problem, optimal_objective
    )
    
    # Individual solver metrics
    report["solver_metrics"] = {}
    for name, result in solver_results.items():
        solver_metrics = calculate_solution_metrics(
            result["best_bitstring"],
            problem,
            optimal_objective,
        )
        solver_metrics["runtime_s"] = result.get("runtime_s", None)
        report["solver_metrics"][name] = solver_metrics
    
    # Runtime comparison
    runtimes = {
        name: result.get("runtime_s")
        for name, result in solver_results.items()
        if result.get("runtime_s") is not None
    }
    
    if runtimes:
        fastest = min(runtimes.items(), key=lambda x: x[1])
        slowest = max(runtimes.items(), key=lambda x: x[1])
        
        report["runtime_analysis"] = {
            "fastest_solver": fastest[0],
            "fastest_time_s": fastest[1],
            "slowest_solver": slowest[0],
            "slowest_time_s": slowest[1],
            "speedup_factor": slowest[1] / fastest[1] if fastest[1] > 0 else None,
        }
    
    # Portfolio-specific analysis
    if include_portfolio_metrics and isinstance(problem, PortfolioOptimization):
        report["portfolio_analysis"] = {}
        for name, result in solver_results.items():
            if problem.is_feasible(result["best_bitstring"]):
                report["portfolio_analysis"][name] = calculate_portfolio_performance(
                    result["best_bitstring"], problem
                )
    
    # Honest assessment
    report["assessment"] = _generate_honest_assessment(
        report, optimal_objective
    )
    
    return report


def _generate_honest_assessment(
    report: Dict,
    optimal_objective: Optional[float],
) -> Dict[str, str]:
    """Generate honest assessment of results.
    
    This explicitly states when classical methods outperform quantum.
    
    Args:
        report: Benchmarking report
        optimal_objective: Known optimal
        
    Returns:
        Honest assessment text
    """
    comparison = report["comparison"]
    best_solver = comparison["best_solver"]
    
    assessment = {
        "best_performer": best_solver,
    }
    
    # Check if quantum solver exists
    quantum_solvers = [
        name for name in report["solver_names"]
        if "quantum" in name.lower() or "qaoa" in name.lower()
    ]
    
    classical_solvers = [
        name for name in report["solver_names"]
        if name not in quantum_solvers
    ]
    
    if quantum_solvers and classical_solvers:
        # Compare quantum vs classical
        quantum_best = min(
            [(name, report["solver_metrics"][name]["objective_value"])
             for name in quantum_solvers],
            key=lambda x: x[1]
        )
        
        classical_best = min(
            [(name, report["solver_metrics"][name]["objective_value"])
             for name in classical_solvers],
            key=lambda x: x[1]
        )
        
        if quantum_best[1] < classical_best[1]:
            assessment["quantum_vs_classical"] = (
                f"Quantum solver ({quantum_best[0]}) outperformed classical "
                f"by {((classical_best[1] - quantum_best[1]) / classical_best[1] * 100):.2f}%"
            )
        elif quantum_best[1] > classical_best[1]:
            assessment["quantum_vs_classical"] = (
                f"Classical solver ({classical_best[0]}) outperformed quantum "
                f"by {((quantum_best[1] - classical_best[1]) / quantum_best[1] * 100):.2f}%"
            )
        else:
            assessment["quantum_vs_classical"] = "Quantum and classical found same solution"
    
    # Optimal comparison
    if optimal_objective is not None and "optimal_found_by" in comparison:
        if comparison["optimal_found_by"]:
            assessment["optimal_status"] = (
                f"Optimal solution found by: {', '.join(comparison['optimal_found_by'])}"
            )
        else:
            best_ratio = comparison["approximation_ratios_vs_optimal"][best_solver]
            assessment["optimal_status"] = (
                f"No solver found optimal. Best approximation ratio: {best_ratio:.4f} "
                f"({best_solver})"
            )
    
    return assessment
