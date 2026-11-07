"""Max-Cut optimization problem (stretch goal)."""

from typing import Any, Dict, Tuple

import numpy as np

from .base import Problem


class MaxCutOptimization(Problem):
    """Max-Cut problem: partition graph to maximize cut edges.
    
    Objective: Maximize Σ_{(i,j) ∈ E} (x_i ⊕ x_j)
              = Maximize Σ_{(i,j) ∈ E} (x_i + x_j - 2*x_i*x_j)
    
    Where x_i ∈ {0, 1} indicates which partition node i belongs to.
    
    Convert to minimization QUBO:
    Minimize -Σ_{(i,j) ∈ E} (x_i + x_j - 2*x_i*x_j)
    """

    def __init__(
        self,
        num_nodes: int,
        edge_probability: float = 0.5,
        adjacency_matrix: np.ndarray = None,
        seed: int = None,
    ):
        """Initialize Max-Cut problem.
        
        Args:
            num_nodes: Number of graph nodes
            edge_probability: Probability of edge in random graph
            adjacency_matrix: Pre-defined adjacency matrix (if None, generate random)
            seed: Random seed
        """
        params = {
            "num_nodes": num_nodes,
            "edge_probability": edge_probability,
        }
        super().__init__(params, seed)

        self.num_nodes = num_nodes

        if adjacency_matrix is not None:
            self.adjacency = adjacency_matrix
        else:
            # Generate random graph (upper triangular, symmetric)
            self.adjacency = np.zeros((num_nodes, num_nodes))
            for i in range(num_nodes):
                for j in range(i + 1, num_nodes):
                    if self.rng.random() < edge_probability:
                        self.adjacency[i, j] = 1
                        self.adjacency[j, i] = 1

        self.num_edges = int(np.sum(self.adjacency) / 2)

    def build_qubo(self) -> Tuple[np.ndarray, float]:
        """Build QUBO matrix for Max-Cut.
        
        Minimize: -Σ_{(i,j) ∈ E} (x_i + x_j - 2*x_i*x_j)
                = Σ_{(i,j) ∈ E} 2*x_i*x_j - Σ_{(i,j) ∈ E} (x_i + x_j)
        
        Returns:
            Tuple of (Q matrix, offset)
        """
        n = self.num_nodes
        Q = np.zeros((n, n))

        for i in range(n):
            for j in range(i + 1, n):
                if self.adjacency[i, j] > 0:
                    # Off-diagonal: 2 * A_ij (appears twice, so add 1 each)
                    Q[i, j] += 1.0
                    Q[j, i] += 1.0
                    # Diagonal: -A_ij
                    Q[i, i] -= 1.0
                    Q[j, j] -= 1.0

        return Q, 0.0

    def decode_solution(self, bitstring: str) -> Dict[str, Any]:
        """Decode binary solution to graph partition.
        
        Args:
            bitstring: Binary string indicating partition assignment
            
        Returns:
            Dict with partition sets and cut edges
        """
        x = np.array([int(b) for b in bitstring])
        partition_0 = np.where(x == 0)[0].tolist()
        partition_1 = np.where(x == 1)[0].tolist()

        # Count cut edges
        cut_edges = []
        for i in range(self.num_nodes):
            for j in range(i + 1, self.num_nodes):
                if self.adjacency[i, j] > 0 and x[i] != x[j]:
                    cut_edges.append((i, j))

        return {
            "partition_0": partition_0,
            "partition_1": partition_1,
            "cut_edges": cut_edges,
            "cut_size": len(cut_edges),
        }

    def evaluate_objective(self, bitstring: str) -> float:
        """Evaluate Max-Cut objective (minimization form).
        
        Args:
            bitstring: Binary solution string
            
        Returns:
            Negative cut size (lower is better)
        """
        decoded = self.decode_solution(bitstring)
        # Return negative because we minimize (maximize cut = minimize -cut)
        return float(-decoded["cut_size"])

    def is_feasible(self, bitstring: str) -> bool:
        """Max-Cut has no hard constraints; all solutions are feasible.
        
        Args:
            bitstring: Binary solution string
            
        Returns:
            Always True
        """
        return True

    def get_problem_info(self) -> Dict[str, Any]:
        """Get problem metadata.
        
        Returns:
            Dict with graph details
        """
        return {
            "problem_type": "maxcut",
            "num_nodes": self.num_nodes,
            "num_edges": self.num_edges,
            "edge_probability": self.params.get("edge_probability", "N/A"),
        }


def create_maxcut_problem(
    num_nodes: int,
    edge_probability: float = 0.5,
    adjacency_matrix: np.ndarray = None,
    seed: int = None,
) -> MaxCutOptimization:
    """Factory function for Max-Cut problem.
    
    Args:
        num_nodes: Number of graph nodes
        edge_probability: Edge probability for random graph
        adjacency_matrix: Pre-defined adjacency (optional)
        seed: Random seed
        
    Returns:
        MaxCutOptimization instance
    """
    return MaxCutOptimization(
        num_nodes=num_nodes,
        edge_probability=edge_probability,
        adjacency_matrix=adjacency_matrix,
        seed=seed,
    )
