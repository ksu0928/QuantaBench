"""Brute force exact solver for small optimization problems.

This solver exhaustively evaluates all 2^n possible solutions and finds the
global optimum. Only practical for n <= 20.
"""

import time
from dataclasses import dataclass
from typing import List, Tuple

import numpy as np

from ..problems.base import Problem


@dataclass
class BruteForceSolution:
    """Solution from brute force solver."""

    best_bitstring: str
    best_objective: float
    all_feasible_solutions: List[Tuple[str, float]]
    num_evaluated: int
    num_feasible: int
    runtime_s: float


class BruteForceSolver:
    """Exhaustive search solver for optimization problems."""

    def __init__(self, max_size: int = 20):
        """Initialize brute force solver.
        
        Args:
            max_size: Maximum problem size (number of variables)
        """
        self.max_size = max_size

    def solve(self, problem: Problem) -> BruteForceSolution:
        """Solve problem via exhaustive search.
        
        Args:
            problem: Problem instance
            
        Returns:
            BruteForceSolution with optimal solution
            
        Raises:
            ValueError: If problem size exceeds max_size
        """
        n = problem.num_variables()

        if n > self.max_size:
            raise ValueError(
                f"Problem size n={n} exceeds max_size={self.max_size}. "
                f"Brute force requires evaluating 2^{n} = {2**n:,} solutions."
            )

        start_time = time.time()

        best_bitstring = None
        best_objective = float("inf")
        all_feasible = []

        # Evaluate all 2^n solutions
        for i in range(2**n):
            bitstring = format(i, f"0{n}b")

            # Check feasibility
            if not problem.is_feasible(bitstring):
                continue

            # Evaluate objective
            objective = problem.evaluate_objective(bitstring)
            all_feasible.append((bitstring, objective))

            # Track best
            if objective < best_objective:
                best_objective = objective
                best_bitstring = bitstring

        runtime = time.time() - start_time

        if best_bitstring is None:
            raise ValueError("No feasible solution found")

        # Sort feasible solutions by objective
        all_feasible.sort(key=lambda x: x[1])

        return BruteForceSolution(
            best_bitstring=best_bitstring,
            best_objective=best_objective,
            all_feasible_solutions=all_feasible,
            num_evaluated=2**n,
            num_feasible=len(all_feasible),
            runtime_s=runtime,
        )

    def get_optimal_value(self, problem: Problem) -> float:
        """Get optimal objective value (convenience method).
        
        Args:
            problem: Problem instance
            
        Returns:
            Optimal objective value
        """
        solution = self.solve(problem)
        return solution.best_objective

    def get_optimal_solution(self, problem: Problem) -> str:
        """Get optimal solution bitstring (convenience method).
        
        Args:
            problem: Problem instance
            
        Returns:
            Optimal bitstring
        """
        solution = self.solve(problem)
        return solution.best_bitstring


def solve_brute_force(problem: Problem) -> BruteForceSolution:
    """Solve problem with brute force (convenience function).
    
    Args:
        problem: Problem instance
        
    Returns:
        BruteForceSolution
    """
    solver = BruteForceSolver()
    return solver.solve(problem)
