"""Unit tests for portfolio optimization problem."""

import numpy as np
import pytest

from app.problems.portfolio import PortfolioOptimization, create_portfolio_problem
from app.quantum.hamiltonian import qubo_to_ising, verify_qubo_ising_equivalence


class TestPortfolioOptimization:
    """Test portfolio optimization problem."""

    @pytest.fixture
    def sample_returns(self):
        """Generate sample returns data."""
        np.random.seed(42)
        # 100 days, 10 assets
        returns = np.random.randn(100, 10) * 0.01  # 1% daily volatility
        returns += np.random.randn(10) * 0.0001  # Add small positive drift
        return returns

    def test_initialization(self, sample_returns):
        """Test problem initialization."""
        problem = PortfolioOptimization(
            returns=sample_returns,
            num_assets=6,
            target_size=3,
            risk_factor=0.5,
            seed=42,
        )

        assert problem.num_assets == 6
        assert problem.target_size == 3
        assert problem.risk_factor == 0.5
        assert problem.returns.shape[1] == 6
        assert problem.lambda_penalty > 0  # Auto-tuned

    def test_auto_tune_lambda(self, sample_returns):
        """Test lambda auto-tuning."""
        problem = PortfolioOptimization(
            returns=sample_returns,
            num_assets=6,
            target_size=3,
            risk_factor=0.5,
            seed=42,
        )

        # Lambda should be positive
        assert problem.lambda_penalty > 0

        # Check that constraint violations are heavily penalized
        # Feasible solution: exactly K=3 assets
        feasible = "100100"
        feasible_obj = problem.evaluate_objective(feasible)

        # Infeasible: all assets selected
        infeasible_all = "111111"
        infeasible_obj = problem.evaluate_objective(infeasible_all)

        # Infeasible should be worse (higher objective)
        assert infeasible_obj > feasible_obj

    def test_qubo_construction(self, sample_returns):
        """Test QUBO matrix construction."""
        problem = PortfolioOptimization(
            returns=sample_returns,
            num_assets=4,
            target_size=2,
            risk_factor=0.5,
            lambda_penalty=10.0,
            seed=42,
        )

        Q, offset = problem.build_qubo()

        assert Q.shape == (4, 4)
        assert isinstance(offset, float)

        # QUBO should be real-valued
        assert Q.dtype in [np.float32, np.float64]

    def test_feasibility_check(self, sample_returns):
        """Test feasibility checking."""
        problem = PortfolioOptimization(
            returns=sample_returns,
            num_assets=5,
            target_size=3,
            seed=42,
        )

        assert problem.is_feasible("11100")  # 3 selected
        assert problem.is_feasible("10101")  # 3 selected
        assert not problem.is_feasible("11110")  # 4 selected
        assert not problem.is_feasible("11000")  # 2 selected
        assert not problem.is_feasible("00000")  # 0 selected

    def test_solution_decoding(self, sample_returns):
        """Test solution decoding."""
        problem = PortfolioOptimization(
            returns=sample_returns,
            num_assets=5,
            target_size=3,
            seed=42,
        )

        solution = problem.decode_solution("10110")

        assert solution["portfolio_size"] == 3
        assert solution["selected_indices"] == [0, 2, 3]
        assert "mean_return" in solution
        assert "variance" in solution

    def test_objective_evaluation(self, sample_returns):
        """Test objective function evaluation."""
        problem = PortfolioOptimization(
            returns=sample_returns,
            num_assets=4,
            target_size=2,
            risk_factor=0.5,
            lambda_penalty=10.0,
            seed=42,
        )

        # Feasible solution should have lower penalty
        feasible_obj = problem.evaluate_objective("1100")
        infeasible_obj = problem.evaluate_objective("1110")

        assert isinstance(feasible_obj, float)
        assert isinstance(infeasible_obj, float)
        # Infeasible should be worse due to penalty
        assert infeasible_obj > feasible_obj

    def test_qubo_objective_consistency(self, sample_returns):
        """Test that QUBO evaluation matches problem objective."""
        problem = PortfolioOptimization(
            returns=sample_returns,
            num_assets=4,
            target_size=2,
            risk_factor=0.5,
            lambda_penalty=10.0,
            seed=42,
        )

        # Verify for all bitstrings (2^4 = 16)
        assert problem.validate_qubo_consistency(tolerance=1e-6)

    def test_sharpe_ratio_calculation(self, sample_returns):
        """Test Sharpe ratio calculation."""
        problem = PortfolioOptimization(
            returns=sample_returns,
            num_assets=5,
            target_size=3,
            seed=42,
        )

        # Feasible solution
        sharpe = problem.calculate_sharpe_ratio("11100")
        assert isinstance(sharpe, float)
        assert not np.isnan(sharpe)

        # Infeasible solution should return -inf
        sharpe_infeasible = problem.calculate_sharpe_ratio("11110")
        assert sharpe_infeasible == float("-inf")

    def test_metrics_calculation(self, sample_returns):
        """Test comprehensive metrics calculation."""
        problem = PortfolioOptimization(
            returns=sample_returns,
            num_assets=5,
            target_size=3,
            seed=42,
        )

        metrics = problem.calculate_metrics("11100")

        assert "annual_return" in metrics
        assert "annual_volatility" in metrics
        assert "sharpe_ratio" in metrics
        assert "num_selected" in metrics
        assert "is_feasible" in metrics

        assert metrics["num_selected"] == 3
        assert metrics["is_feasible"] is True

    def test_best_feasible_solution(self, sample_returns):
        """Test finding optimal solution via brute force."""
        problem = PortfolioOptimization(
            returns=sample_returns,
            num_assets=5,
            target_size=2,
            risk_factor=0.5,
            seed=42,
        )

        best_bitstring, best_obj = problem.best_feasible_solution()

        # Should be feasible
        assert problem.is_feasible(best_bitstring)
        assert best_bitstring.count("1") == 2

        # Should be optimal among feasible solutions
        for bitstring in problem.all_bitstrings():
            if problem.is_feasible(bitstring):
                obj = problem.evaluate_objective(bitstring)
                assert obj >= best_obj - 1e-9  # Allow for numerical precision

    def test_problem_info(self, sample_returns):
        """Test problem metadata retrieval."""
        problem = PortfolioOptimization(
            returns=sample_returns,
            num_assets=6,
            target_size=3,
            risk_factor=0.6,
            seed=42,
        )

        info = problem.get_problem_info()

        assert info["problem_type"] == "portfolio_optimization"
        assert info["num_assets"] == 6
        assert info["target_size"] == 3
        assert info["risk_factor"] == 0.6
        assert "lambda_penalty" in info
        assert "mean_returns_annual" in info

    def test_ising_conversion_n6(self, sample_returns):
        """Test QUBO to Ising conversion for n=6 portfolio problem."""
        problem = PortfolioOptimization(
            returns=sample_returns,
            num_assets=6,
            target_size=3,
            risk_factor=0.5,
            seed=42,
        )

        Q, qubo_offset = problem.get_qubo_matrix()
        h, J, ising_offset = qubo_to_ising(Q, qubo_offset)

        # Verify energy equivalence for all 2^6 = 64 configurations
        result = verify_qubo_ising_equivalence(
            Q, qubo_offset, h, J, ising_offset, test_all_bitstrings=True
        )

        assert result["success"], f"Ising conversion failed: {result}"
        assert result["max_error"] < 1e-9
        assert result["num_tested"] == 64

    def test_factory_function(self, sample_returns):
        """Test factory function."""
        problem = create_portfolio_problem(
            returns=sample_returns,
            num_assets=5,
            target_size=2,
            risk_factor=0.7,
            seed=123,
        )

        assert isinstance(problem, PortfolioOptimization)
        assert problem.num_assets == 5
        assert problem.target_size == 2
        assert problem.risk_factor == 0.7

    def test_invalid_target_size(self, sample_returns):
        """Test that target_size > num_assets raises error."""
        with pytest.raises(ValueError):
            PortfolioOptimization(
                returns=sample_returns,
                num_assets=5,
                target_size=6,  # Invalid: > num_assets
                seed=42,
            )

    def test_deterministic_with_seed(self, sample_returns):
        """Test that same seed produces same problem."""
        problem1 = PortfolioOptimization(
            returns=sample_returns,
            num_assets=6,
            target_size=3,
            seed=42,
        )

        problem2 = PortfolioOptimization(
            returns=sample_returns,
            num_assets=6,
            target_size=3,
            seed=42,
        )

        # Should select same assets
        assert np.array_equal(problem1.asset_indices, problem2.asset_indices)

        # Should have same QUBO
        Q1, offset1 = problem1.get_qubo_matrix()
        Q2, offset2 = problem2.get_qubo_matrix()
        assert np.allclose(Q1, Q2)
        assert np.isclose(offset1, offset2)

    def test_different_seeds_produce_different_problems(self, sample_returns):
        """Test that different seeds produce different problems."""
        problem1 = PortfolioOptimization(
            returns=sample_returns,
            num_assets=6,
            target_size=3,
            seed=42,
        )

        problem2 = PortfolioOptimization(
            returns=sample_returns,
            num_assets=6,
            target_size=3,
            seed=123,
        )

        # Should select different assets
        assert not np.array_equal(problem1.asset_indices, problem2.asset_indices)


class TestPortfolioConstraints:
    """Test portfolio constraints and edge cases."""

    def test_all_assets_selected_is_infeasible(self):
        """Test that selecting all assets violates constraint."""
        np.random.seed(0)
        returns = np.random.randn(50, 5) * 0.01

        problem = PortfolioOptimization(
            returns=returns,
            num_assets=5,
            target_size=3,
            seed=0,
        )

        assert not problem.is_feasible("11111")

    def test_no_assets_selected_is_infeasible(self):
        """Test that selecting no assets violates constraint."""
        np.random.seed(0)
        returns = np.random.randn(50, 5) * 0.01

        problem = PortfolioOptimization(
            returns=returns,
            num_assets=5,
            target_size=3,
            seed=0,
        )

        assert not problem.is_feasible("00000")

    def test_risk_factor_zero(self):
        """Test with risk factor = 0 (maximize returns only)."""
        np.random.seed(0)
        returns = np.random.randn(50, 5) * 0.01

        problem = PortfolioOptimization(
            returns=returns,
            num_assets=5,
            target_size=3,
            risk_factor=0.0,
            seed=0,
        )

        Q, offset = problem.build_qubo()
        assert Q.shape == (5, 5)

    def test_risk_factor_one(self):
        """Test with risk factor = 1 (minimize risk only)."""
        np.random.seed(0)
        returns = np.random.randn(50, 5) * 0.01

        problem = PortfolioOptimization(
            returns=returns,
            num_assets=5,
            target_size=3,
            risk_factor=1.0,
            seed=0,
        )

        Q, offset = problem.build_qubo()
        assert Q.shape == (5, 5)
