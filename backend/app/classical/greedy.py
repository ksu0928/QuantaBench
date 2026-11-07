"""Greedy heuristic solver for optimization problems.

Implements a simple greedy construction heuristic that builds solutions
incrementally by selecting variables that provide the best immediate improvement.
"""

import time
from dataclasses import dataclass
from typing import List, Optional, Set

import numpy as np

from ..problems.base import Problem


@dataclass
class GreedySolution:
    """Solution from greedy solver."""

    best_bitstring: str
    best_objective: float
    construction_sequence: List[int]  # Order in which variables were selected
    num_evaluated: int
    runtime_s: float


class GreedySolver:
    """Greedy construction heuristic solver."""

    def __init__(self, seed: Optional[int] = None):
        """Initialize greedy solver.
        
        Args:
            seed: Random seed for tie-breaking
        """
        self.rng = np.random.default_rng(seed)

    def solve(self, problem: Problem) -> GreedySolution:
        """Solve problem with greedy heuristic.
        
        Algorithm:
        1. Start with all variables = 0
        2. Greedily add variables (set to 1) that give best objective improvement
        3. Continue until no improvement possible or constraints violated
        
        Note: This is a simple greedy approach. For portfolio problems,
        it selects assets one-by-one based on improvement to objective.
        
        Args:
            problem: Problem instance
            
        Returns:
            GreedySolution
        """
        start_time = time.time()

        n = problem.num_variables()

        # Start with empty solution (all zeros)
        current_bits = [0] * n
        selected_vars: Set[int] = set()
        construction_sequence = []
        num_evaluated = 0

        # Greedy construction
        while True:
            best_var = None
            best_objective = float("inf")

            # Try adding each non-selected variable
            for i in range(n):
                if i in selected_vars:
                    continue

                # Try setting variable i to 1
                candidate_bits = current_bits.copy()
                candidate_bits[i] = 1
                candidate_bitstring = "".join(str(b) for b in candidate_bits)

                # Evaluate
                objective = problem.evaluate_objective(candidate_bitstring)
                num_evaluated += 1

                # Track best
                if objective < best_objective:
                    best_objective = objective
                    best_var = i

            # If no improvement or all variables selected, stop
            if best_var is None:
                break

            # Add best variable
            current_bits[best_var] = 1
            selected_vars.add(best_var)
            construction_sequence.append(best_var)

            # Check if we should stop (e.g., for cardinality-constrained problems)
            # The problem's objective will naturally guide this through penalties

        # Final solution
        final_bitstring = "".join(str(b) for b in current_bits)
        final_objective = problem.evaluate_objective(final_bitstring)
        num_evaluated += 1

        runtime = time.time() - start_time

        return GreedySolution(
            best_bitstring=final_bitstring,
            best_objective=final_objective,
            construction_sequence=construction_sequence,
            num_evaluated=num_evaluated,
            runtime_s=runtime,
        )


class GreedySolverConstrained(GreedySolver):
    """Greedy solver with explicit constraint handling for portfolio problems.
    
    This variant is aware of cardinality constraints and stops when the target
    portfolio size is reached.
    """

    def solve(
        self,
        problem: Problem,
        target_size: Optional[int] = None,
    ) -> GreedySolution:
        """Solve problem with constraint-aware greedy heuristic.
        
        Args:
            problem: Problem instance
            target_size: Target number of variables to select (for portfolio)
            
        Returns:
            GreedySolution
        """
        start_time = time.time()

        n = problem.num_variables()

        # Infer target size from problem if not provided
        if target_size is None:
            # Try to get from problem metadata
            info = problem.get_problem_info()
            target_size = info.get("target_size", n // 2)

        # Start with empty solution
        current_bits = [0] * n
        selected_vars: Set[int] = set()
        construction_sequence = []
        num_evaluated = 0

        # Greedy construction until target size reached
        while len(selected_vars) < target_size:
            best_var = None
            best_objective = float("inf")

            # Try adding each non-selected variable
            for i in range(n):
                if i in selected_vars:
                    continue

                # Try setting variable i to 1
                candidate_bits = current_bits.copy()
                candidate_bits[i] = 1
                candidate_bitstring = "".join(str(b) for b in candidate_bits)

                # Evaluate
                objective = problem.evaluate_objective(candidate_bitstring)
                num_evaluated += 1

                # Track best
                if objective < best_objective:
                    best_objective = objective
                    best_var = i

            # Add best variable
            if best_var is None:
                break

            current_bits[best_var] = 1
            selected_vars.add(best_var)
            construction_sequence.append(best_var)

        # Final solution
        final_bitstring = "".join(str(b) for b in current_bits)
        final_objective = problem.evaluate_objective(final_bitstring)
        num_evaluated += 1

        runtime = time.time() - start_time

        return GreedySolution(
            best_bitstring=final_bitstring,
            best_objective=final_objective,
            construction_sequence=construction_sequence,
            num_evaluated=num_evaluated,
            runtime_s=runtime,
        )


def solve_greedy(problem: Problem) -> GreedySolution:
    """Solve problem with greedy heuristic (convenience function).
    
    Args:
        problem: Problem instance
        
    Returns:
        GreedySolution
    """
    # Check if this is a portfolio problem with target size
    info = problem.get_problem_info()

    if "target_size" in info:
        solver = GreedySolverConstrained()
        return solver.solve(problem, target_size=info["target_size"])
    else:
        solver = GreedySolver()
        return solver.solve(problem)
