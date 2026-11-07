"""Simulated annealing solver for optimization problems.

Implements classic simulated annealing with configurable cooling schedule,
temperature parameters, and seeded randomness for reproducibility.
"""

import time
from dataclasses import dataclass
from typing import Optional

import numpy as np

from ..problems.base import Problem


@dataclass
class AnnealingSolution:
    """Solution from simulated annealing."""

    best_bitstring: str
    best_objective: float
    final_bitstring: str
    final_objective: float
    num_iterations: int
    num_accepted: int
    acceptance_rate: float
    runtime_s: float
    converged_at_iteration: Optional[int] = None


class SimulatedAnnealingSolver:
    """Simulated annealing solver with geometric cooling."""

    def __init__(
        self,
        initial_temperature: float = 10.0,
        final_temperature: float = 0.01,
        cooling_rate: float = 0.95,
        max_iterations: int = 10000,
        convergence_window: int = 100,
        seed: Optional[int] = None,
    ):
        """Initialize simulated annealing solver.
        
        Args:
            initial_temperature: Starting temperature T_0
            final_temperature: Stopping temperature T_final
            cooling_rate: Geometric cooling factor α (T_new = α * T_old)
            max_iterations: Maximum iterations
            convergence_window: Iterations without improvement for convergence
            seed: Random seed for reproducibility
        """
        self.initial_temperature = initial_temperature
        self.final_temperature = final_temperature
        self.cooling_rate = cooling_rate
        self.max_iterations = max_iterations
        self.convergence_window = convergence_window
        self.rng = np.random.default_rng(seed)

    def solve(self, problem: Problem) -> AnnealingSolution:
        """Solve problem with simulated annealing.
        
        Algorithm:
        1. Start with random solution
        2. Generate neighbor by flipping one bit
        3. Accept if better, or with probability exp(-ΔE/T)
        4. Cool temperature: T_new = α * T_old
        5. Repeat until T < T_final or convergence
        
        Args:
            problem: Problem instance
            
        Returns:
            AnnealingSolution
        """
        start_time = time.time()

        n = problem.num_variables()

        # Initialize with random solution
        current_bitstring = self._random_bitstring(n)
        current_objective = problem.evaluate_objective(current_bitstring)

        # Track best solution found
        best_bitstring = current_bitstring
        best_objective = current_objective

        # Convergence tracking
        iterations_without_improvement = 0
        converged_at = None

        # Annealing loop
        temperature = self.initial_temperature
        iteration = 0
        num_accepted = 0

        while (
            temperature > self.final_temperature
            and iteration < self.max_iterations
            and iterations_without_improvement < self.convergence_window
        ):
            iteration += 1

            # Generate neighbor by flipping one random bit
            neighbor_bitstring = self._flip_random_bit(current_bitstring)
            neighbor_objective = problem.evaluate_objective(neighbor_bitstring)

            # Compute energy difference
            delta_energy = neighbor_objective - current_objective

            # Acceptance criterion
            if delta_energy < 0:
                # Always accept improvements
                accept = True
            else:
                # Accept worse solutions with probability exp(-ΔE/T)
                acceptance_prob = np.exp(-delta_energy / temperature)
                accept = self.rng.random() < acceptance_prob

            if accept:
                current_bitstring = neighbor_bitstring
                current_objective = neighbor_objective
                num_accepted += 1

                # Update best if improved
                if current_objective < best_objective:
                    best_bitstring = current_bitstring
                    best_objective = current_objective
                    iterations_without_improvement = 0
                else:
                    iterations_without_improvement += 1
            else:
                iterations_without_improvement += 1

            # Cool temperature
            temperature *= self.cooling_rate

            # Log progress periodically
            if iteration % 1000 == 0:
                print(f"  Iteration {iteration}: T={temperature:.4f}, "
                      f"best_obj={best_objective:.4f}")

        if iterations_without_improvement >= self.convergence_window:
            converged_at = iteration - self.convergence_window

        runtime = time.time() - start_time

        return AnnealingSolution(
            best_bitstring=best_bitstring,
            best_objective=best_objective,
            final_bitstring=current_bitstring,
            final_objective=current_objective,
            num_iterations=iteration,
            num_accepted=num_accepted,
            acceptance_rate=num_accepted / iteration if iteration > 0 else 0.0,
            runtime_s=runtime,
            converged_at_iteration=converged_at,
        )

    def _random_bitstring(self, n: int) -> str:
        """Generate random binary string of length n.
        
        Args:
            n: Length of bitstring
            
        Returns:
            Random bitstring
        """
        bits = self.rng.integers(0, 2, size=n)
        return "".join(str(b) for b in bits)

    def _flip_random_bit(self, bitstring: str) -> str:
        """Flip one random bit in bitstring.
        
        Args:
            bitstring: Input bitstring
            
        Returns:
            Bitstring with one bit flipped
        """
        n = len(bitstring)
        flip_index = self.rng.integers(0, n)

        bits = list(bitstring)
        bits[flip_index] = "1" if bits[flip_index] == "0" else "0"

        return "".join(bits)


def solve_simulated_annealing(
    problem: Problem,
    initial_temperature: float = 10.0,
    cooling_rate: float = 0.95,
    max_iterations: int = 10000,
    seed: Optional[int] = None,
) -> AnnealingSolution:
    """Solve problem with simulated annealing (convenience function).
    
    Args:
        problem: Problem instance
        initial_temperature: Starting temperature
        cooling_rate: Cooling factor
        max_iterations: Maximum iterations
        seed: Random seed
        
    Returns:
        AnnealingSolution
    """
    solver = SimulatedAnnealingSolver(
        initial_temperature=initial_temperature,
        cooling_rate=cooling_rate,
        max_iterations=max_iterations,
        seed=seed,
    )
    return solver.solve(problem)
