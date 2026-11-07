"""Portfolio optimization problem with mean-variance formulation."""

from typing import Any, Dict, List, Tuple

import numpy as np

from .base import Problem


class PortfolioOptimization(Problem):
    """Mean-variance portfolio optimization with cardinality constraint.
    
    Objective: Minimize q * x^T Σ x - μ^T x + λ * (sum(x) - K)^2
    
    Where:
    - x_i ∈ {0, 1} indicates if asset i is selected
    - Σ is the covariance matrix
    - μ is the expected returns vector
    - q is the risk aversion factor
    - K is the target portfolio size
    - λ is the cardinality constraint penalty (auto-tuned)
    
    The QUBO formulation directly encodes this objective.
    """

    def __init__(
        self,
        returns: np.ndarray,
        num_assets: int,
        target_size: int,
        risk_factor: float = 0.5,
        lambda_penalty: float = None,
        seed: int = None,
    ):
        """Initialize portfolio optimization problem.
        
        Args:
            returns: Daily returns array (T x N) for N assets over T days
            num_assets: Number of assets to consider (subset of available)
            target_size: Target portfolio size K
            risk_factor: Risk aversion factor q ∈ [0, 1]
            lambda_penalty: Cardinality penalty (auto-tuned if None)
            seed: Random seed for asset selection
        """
        params = {
            "num_assets": num_assets,
            "target_size": target_size,
            "risk_factor": risk_factor,
            "lambda_penalty": lambda_penalty,
        }
        super().__init__(params, seed)

        # Select subset of assets if needed
        total_assets = returns.shape[1]
        if num_assets > total_assets:
            raise ValueError(
                f"num_assets ({num_assets}) exceeds available assets ({total_assets})"
            )

        self.asset_indices = self.rng.choice(
            total_assets, size=num_assets, replace=False
        )
        self.returns = returns[:, self.asset_indices]

        # Calculate statistics
        self.mean_returns = np.mean(self.returns, axis=0)
        self.cov_matrix = np.cov(self.returns, rowvar=False)

        # Annualize (assuming 252 trading days)
        self.mean_returns_annual = self.mean_returns * 252
        self.cov_matrix_annual = self.cov_matrix * 252

        self.num_assets = num_assets
        self.target_size = target_size
        self.risk_factor = risk_factor

        # Auto-tune lambda if not provided
        if lambda_penalty is None:
            self.lambda_penalty = self._auto_tune_lambda()
        else:
            self.lambda_penalty = lambda_penalty

    def _auto_tune_lambda(self) -> float:
        """Auto-tune lambda so constraint violation costs more than best objective gain.
        
        Strategy:
        1. Estimate range of objective values for feasible solutions
        2. Compute penalty for worst constraint violation (all assets selected)
        3. Set lambda so penalty >> objective range
        
        Returns:
            Tuned lambda value
        """
        # Estimate max return gain (all positive returns)
        max_return_contribution = np.sum(np.maximum(self.mean_returns_annual, 0))

        # Estimate max risk cost (diagonal dominates for q near 1)
        max_risk_contribution = (
            self.risk_factor * np.sum(np.diag(self.cov_matrix_annual))
        )

        # Objective range estimate
        obj_range = max(abs(max_return_contribution), abs(max_risk_contribution))

        # Worst constraint violation: |sum(x) - K|_max = max(N - K, K)
        max_violation = max(self.num_assets - self.target_size, self.target_size)

        # Set lambda so that penalty for max violation is 10x the objective range
        # This ensures any infeasible solution is worse than any feasible one
        lambda_min = (10 * obj_range) / (max_violation**2)

        # Add safety margin
        return lambda_min * 1.5

    def build_qubo(self) -> Tuple[np.ndarray, float]:
        """Build QUBO matrix for portfolio optimization.
        
        Objective: minimize q * x^T Σ x - μ^T x + λ * (Σx_i - K)^2
        
        Expanding the cardinality term:
        λ * (Σx_i - K)^2 = λ * (Σx_i^2 + ΣΣx_i*x_j - 2K*Σx_i + K^2)
                         = λ * (Σx_i + ΣΣx_i*x_j - 2K*Σx_i + K^2)  [since x_i^2 = x_i]
                         = λ * (1 - 2K)*Σx_i + λ*ΣΣx_i*x_j + λ*K^2
        
        QUBO form: x^T Q x + offset
        
        Returns:
            Tuple of (Q matrix, constant offset)
        """
        n = self.num_assets
        Q = np.zeros((n, n))

        # Risk term: q * Σ
        Q += self.risk_factor * self.cov_matrix_annual

        # Cardinality penalty off-diagonal: λ * x_i * x_j for i != j
        for i in range(n):
            for j in range(n):
                if i != j:
                    Q[i, j] += self.lambda_penalty

        # Diagonal terms: -μ_i + λ * (1 - 2K)
        for i in range(n):
            Q[i, i] += -self.mean_returns_annual[i] + self.lambda_penalty * (
                1 - 2 * self.target_size
            )

        # Constant offset
        offset = self.lambda_penalty * (self.target_size**2)

        return Q, offset

    def decode_solution(self, bitstring: str) -> Dict[str, Any]:
        """Decode binary solution to selected asset indices.
        
        Args:
            bitstring: Binary string where '1' indicates asset is selected
            
        Returns:
            Dict with selected_indices, portfolio_size, and asset_mapping
        """
        x = np.array([int(b) for b in bitstring])
        selected_mask = x == 1
        selected_indices = np.where(selected_mask)[0].tolist()
        actual_asset_indices = self.asset_indices[selected_mask].tolist()

        return {
            "selected_indices": selected_indices,
            "actual_asset_indices": actual_asset_indices,
            "portfolio_size": len(selected_indices),
            "mean_return": float(np.sum(self.mean_returns_annual[selected_mask]))
            if len(selected_indices) > 0
            else 0.0,
            "variance": float(
                x @ self.cov_matrix_annual @ x if len(selected_indices) > 0 else 0.0
            ),
        }

    def evaluate_objective(self, bitstring: str) -> float:
        """Evaluate portfolio objective including penalty.
        
        Args:
            bitstring: Binary solution string
            
        Returns:
            Objective value (lower is better)
        """
        x = np.array([int(b) for b in bitstring])

        # Risk term
        risk = self.risk_factor * (x @ self.cov_matrix_annual @ x)

        # Return term (negative because we want to maximize returns)
        returns = -np.dot(self.mean_returns_annual, x)

        # Cardinality penalty
        portfolio_size = np.sum(x)
        cardinality_penalty = self.lambda_penalty * (
            (portfolio_size - self.target_size) ** 2
        )

        return float(risk + returns + cardinality_penalty)

    def is_feasible(self, bitstring: str) -> bool:
        """Check if solution satisfies cardinality constraint.
        
        Args:
            bitstring: Binary solution string
            
        Returns:
            True if exactly K assets are selected
        """
        return bitstring.count("1") == self.target_size

    def get_problem_info(self) -> Dict[str, Any]:
        """Get problem metadata.
        
        Returns:
            Dict with problem details
        """
        return {
            "problem_type": "portfolio_optimization",
            "num_assets": self.num_assets,
            "target_size": self.target_size,
            "risk_factor": self.risk_factor,
            "lambda_penalty": self.lambda_penalty,
            "mean_returns_annual": self.mean_returns_annual.tolist(),
            "cov_matrix_shape": self.cov_matrix_annual.shape,
            "asset_indices": self.asset_indices.tolist(),
        }

    def calculate_sharpe_ratio(self, bitstring: str) -> float:
        """Calculate Sharpe ratio for a solution (assuming risk-free rate = 0).
        
        Args:
            bitstring: Binary solution string
            
        Returns:
            Sharpe ratio (return / volatility)
        """
        if not self.is_feasible(bitstring):
            return float("-inf")

        x = np.array([int(b) for b in bitstring])
        portfolio_return = np.dot(self.mean_returns_annual, x)
        portfolio_variance = x @ self.cov_matrix_annual @ x
        portfolio_std = np.sqrt(portfolio_variance)

        if portfolio_std < 1e-10:
            return 0.0

        return float(portfolio_return / portfolio_std)

    def calculate_metrics(self, bitstring: str) -> Dict[str, float]:
        """Calculate all portfolio metrics for a solution.
        
        Args:
            bitstring: Binary solution string
            
        Returns:
            Dict with metrics (returns, risk, sharpe, etc.)
        """
        x = np.array([int(b) for b in bitstring])
        
        portfolio_return = float(np.dot(self.mean_returns_annual, x))
        portfolio_variance = float(x @ self.cov_matrix_annual @ x)
        portfolio_std = float(np.sqrt(portfolio_variance))
        
        sharpe = self.calculate_sharpe_ratio(bitstring)
        
        return {
            "annual_return": portfolio_return,
            "annual_volatility": portfolio_std,
            "annual_variance": portfolio_variance,
            "sharpe_ratio": sharpe,
            "num_selected": int(np.sum(x)),
            "is_feasible": self.is_feasible(bitstring),
        }


def create_portfolio_problem(
    returns: np.ndarray,
    num_assets: int,
    target_size: int,
    risk_factor: float = 0.5,
    lambda_penalty: float = None,
    seed: int = None,
) -> PortfolioOptimization:
    """Factory function to create portfolio optimization problem.
    
    Args:
        returns: Daily returns array (T x N)
        num_assets: Number of assets to consider
        target_size: Target portfolio size
        risk_factor: Risk aversion factor
        lambda_penalty: Cardinality penalty (auto-tuned if None)
        seed: Random seed
        
    Returns:
        PortfolioOptimization instance
    """
    return PortfolioOptimization(
        returns=returns,
        num_assets=num_assets,
        target_size=target_size,
        risk_factor=risk_factor,
        lambda_penalty=lambda_penalty,
        seed=seed,
    )
