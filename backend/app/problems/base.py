"""Abstract base class for optimization problems."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Tuple

import numpy as np


class Problem(ABC):
    """Abstract interface for optimization problems.
    
    All problems must implement:
    - QUBO matrix construction
    - Solution decoding from bitstrings
    - Objective function evaluation
    - Constraint validation
    """

    def __init__(self, params: Dict[str, Any], seed: int = None):
        """Initialize problem with parameters.
        
        Args:
            params: Problem-specific parameters
            seed: Random seed for reproducibility
        """
        self.params = params
        self.seed = seed
        self.rng = np.random.default_rng(seed)
        self._qubo_matrix: np.ndarray = None
        self._offset: float = 0.0

    @abstractmethod
    def build_qubo(self) -> Tuple[np.ndarray, float]:
        """Construct QUBO matrix Q and constant offset.
        
        The objective is: minimize x^T Q x + offset
        where x is a binary vector.
        
        Returns:
            Tuple of (Q matrix, offset constant)
        """
        pass

    @abstractmethod
    def decode_solution(self, bitstring: str) -> Dict[str, Any]:
        """Decode a binary solution string into problem-specific format.
        
        Args:
            bitstring: Binary string (e.g., "10011")
            
        Returns:
            Dict with solution details (indices, values, etc.)
        """
        pass

    @abstractmethod
    def evaluate_objective(self, bitstring: str) -> float:
        """Evaluate objective function for a given solution.
        
        Args:
            bitstring: Binary solution string
            
        Returns:
            Objective value (lower is better for minimization)
        """
        pass

    @abstractmethod
    def is_feasible(self, bitstring: str) -> bool:
        """Check if solution satisfies all constraints.
        
        Args:
            bitstring: Binary solution string
            
        Returns:
            True if feasible, False otherwise
        """
        pass

    @abstractmethod
    def get_problem_info(self) -> Dict[str, Any]:
        """Get metadata about the problem instance.
        
        Returns:
            Dict with problem size, constraints, etc.
        """
        pass

    def get_qubo_matrix(self) -> Tuple[np.ndarray, float]:
        """Get cached QUBO matrix or build if not cached.
        
        Returns:
            Tuple of (Q matrix, offset)
        """
        if self._qubo_matrix is None:
            self._qubo_matrix, self._offset = self.build_qubo()
        return self._qubo_matrix.copy(), self._offset

    def evaluate_qubo(self, bitstring: str) -> float:
        """Evaluate QUBO objective directly from matrix.
        
        Args:
            bitstring: Binary solution string
            
        Returns:
            QUBO objective value
        """
        Q, offset = self.get_qubo_matrix()
        x = np.array([int(b) for b in bitstring])
        return float(x @ Q @ x) + offset

    def num_variables(self) -> int:
        """Get number of binary variables.
        
        Returns:
            Number of variables in the problem
        """
        Q, _ = self.get_qubo_matrix()
        return Q.shape[0]

    def all_bitstrings(self) -> List[str]:
        """Generate all possible bitstrings for exhaustive search.
        
        Returns:
            List of all binary strings of length n
        """
        n = self.num_variables()
        return [format(i, f"0{n}b") for i in range(2**n)]

    def best_feasible_solution(self) -> Tuple[str, float]:
        """Find optimal feasible solution via brute force.
        
        Only practical for small problems (n <= 20).
        
        Returns:
            Tuple of (best_bitstring, best_objective)
        """
        n = self.num_variables()
        if n > 20:
            raise ValueError(
                f"Brute force infeasible for n={n} variables (2^{n} states)"
            )

        best_bitstring = None
        best_objective = float("inf")

        for bitstring in self.all_bitstrings():
            if self.is_feasible(bitstring):
                obj = self.evaluate_objective(bitstring)
                if obj < best_objective:
                    best_objective = obj
                    best_bitstring = bitstring

        if best_bitstring is None:
            raise ValueError("No feasible solution found")

        return best_bitstring, best_objective

    def validate_qubo_consistency(self, tolerance: float = 1e-6) -> bool:
        """Verify QUBO objective matches problem objective for all bitstrings.
        
        Unit test helper for small problems.
        
        Args:
            tolerance: Numerical tolerance for comparison
            
        Returns:
            True if objectives match within tolerance
        """
        n = self.num_variables()
        if n > 10:
            raise ValueError(
                f"Validation infeasible for n={n} (use smaller test case)"
            )

        for bitstring in self.all_bitstrings():
            qubo_val = self.evaluate_qubo(bitstring)
            prob_val = self.evaluate_objective(bitstring)
            if abs(qubo_val - prob_val) > tolerance:
                return False

        return True
