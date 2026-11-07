"""Unit tests for metrics calculation."""

import numpy as np
import pytest

from app.metrics import (
    calculate_approximation_ratio,
    calculate_feasibility_rate,
    calculate_portfolio_performance,
    calculate_prob_optimal,
    calculate_quantum_metrics,
    calculate_sharpe_ratio,
    calculate_solution_metrics,
    compare_solvers,
    generate_benchmarking_report,
)
from app.problems.portfolio import PortfolioOptimization


class TestApproximationRatio:
    """Test approximation ratio calculation."""

    def test_optimal_solution(self):
        """Test ratio for optimal solution."""
        ratio = calculate_approximation_ratio(10.0, 10.0)
        assert ratio == 1.0

    def test_worse_than_optimal(self):
        """Test ratio for suboptimal solution."""
        ratio = calculate_approximation_ratio(15.0, 10.0)
        assert ratio == 1.5

    def test_zero_optimal(self):
        """Test edge case with zero optimal."""
        ratio = calculate_approximation_ratio(0.0, 0.0)
        assert ratio == 1.0

        ratio = calculate_approximation_ratio(5.0, 0.0)
        assert ratio == float("inf")


class TestProbOptimal:
    """Test probability of measuring optimal."""

    def test_always_optimal(self):
        """Test when only optimal is measured."""
        counts = {"101": 100}
        prob = calculate_prob_optimal(counts, "101")
        assert prob == 1.0

    def test_never_optimal(self):
        """Test when optimal is never measured."""
        counts = {"000": 50, "111": 50}
        prob = calculate_prob_optimal(counts, "101")
        assert prob == 0.0

    def test_partial_optimal(self):
        """Test when optimal measured 40% of time."""
        counts = {"000": 30, "101": 40, "111": 30}
        prob = calculate_prob_optimal(counts, "101")
        assert prob == 0.4


class TestFeasibilityRate:
    """Test feasibility rate calculation."""

    @pytest.fixture
    def sample_returns(self):
        """Generate sample returns."""
        np.random.seed(42)
        return np.random.randn(100, 10) * 0.01

    def test_all_feasible(self, sample_returns):
        """Test when all solutions are feasible."""
        problem = PortfolioOptimization(
            returns=sample_returns,
            num_assets=4,
            target_size=2,
            seed=42,
        )

        # All with exactly 2 assets
        counts = {"1100": 30, "1010": 40, "0011": 30}
        rate = calculate_feasibility_rate(counts, problem)
        assert rate == 1.0

    def test_none_feasible(self, sample_returns):
        """Test when no solutions are feasible."""
        problem = PortfolioOptimization(
            returns=sample_returns,
            num_assets=4,
            target_size=2,
            seed=42,
        )

        # All with wrong number of assets
        counts = {"1110": 50, "1111": 50}
        rate = calculate_feasibility_rate(counts, problem)
        assert rate == 0.0

    def test_partial_feasibility(self, sample_returns):
        """Test mixed feasibility."""
        problem = PortfolioOptimization(
            returns=sample_returns,
            num_assets=4,
            target_size=2,
            seed=42,
        )

        # 60 feasible, 40 infeasible
        counts = {"1100": 60, "1110": 40}
        rate = calculate_feasibility_rate(counts, problem)
        assert rate == 0.6


class TestSharpeRatio:
    """Test Sharpe ratio calculation."""

    @pytest.fixture
    def sample_returns(self):
        """Generate sample returns."""
        np.random.seed(42)
        return np.random.randn(100, 10) * 0.01

    def test_feasible_solution(self, sample_returns):
        """Test Sharpe ratio for feasible solution."""
        problem = PortfolioOptimization(
            returns=sample_returns,
            num_assets=4,
            target_size=2,
            seed=42,
        )

        sharpe = calculate_sharpe_ratio("1100", problem)
        assert sharpe is not None
        assert isinstance(sharpe, float)

    def test_infeasible_solution_returns_none(self, sample_returns):
        """Test that infeasible solution returns None."""
        problem = PortfolioOptimization(
            returns=sample_returns,
            num_assets=4,
            target_size=2,
            seed=42,
        )

        sharpe = calculate_sharpe_ratio("1110", problem)
        assert sharpe is None


class TestSolutionMetrics:
    """Test comprehensive solution metrics."""

    @pytest.fixture
    def sample_returns(self):
        """Generate sample returns."""
        np.random.seed(42)
        return np.random.randn(100, 10) * 0.01

    def test_basic_metrics(self, sample_returns):
        """Test basic metric calculation."""
        problem = PortfolioOptimization(
            returns=sample_returns,
            num_assets=4,
            target_size=2,
            seed=42,
        )

        metrics = calculate_solution_metrics("1100", problem)

        assert "objective_value" in metrics
        assert "is_feasible" in metrics
        assert metrics["is_feasible"] is True

    def test_with_optimal(self, sample_returns):
        """Test metrics with optimal objective."""
        problem = PortfolioOptimization(
            returns=sample_returns,
            num_assets=4,
            target_size=2,
            seed=42,
        )

        metrics = calculate_solution_metrics(
            "1100", problem, optimal_objective=10.0
        )

        assert "approximation_ratio" in metrics

    def test_portfolio_specific_metrics(self, sample_returns):
        """Test portfolio-specific metrics included."""
        problem = PortfolioOptimization(
            returns=sample_returns,
            num_assets=4,
            target_size=2,
            seed=42,
        )

        metrics = calculate_solution_metrics("1100", problem)

        assert "sharpe_ratio" in metrics
        assert "annual_return" in metrics
        assert "annual_volatility" in metrics
        assert "num_selected" in metrics


class TestQuantumMetrics:
    """Test quantum execution metrics."""

    @pytest.fixture
    def sample_returns(self):
        """Generate sample returns."""
        np.random.seed(42)
        return np.random.randn(100, 10) * 0.01

    def test_basic_quantum_metrics(self, sample_returns):
        """Test basic quantum metrics calculation."""
        problem = PortfolioOptimization(
            returns=sample_returns,
            num_assets=3,
            target_size=2,
            seed=42,
        )

        counts = {"110": 60, "101": 30, "011": 10}

        metrics = calculate_quantum_metrics(counts, problem)

        assert metrics["best_bitstring"] == "110"  # Most frequent
        assert "best_objective" in metrics
        assert "feasibility_rate" in metrics
        assert metrics["num_unique_solutions"] == 3
        assert metrics["total_shots"] == 100

    def test_with_optimal_info(self, sample_returns):
        """Test metrics with optimal information."""
        problem = PortfolioOptimization(
            returns=sample_returns,
            num_assets=3,
            target_size=2,
            seed=42,
        )

        counts = {"110": 60, "101": 30, "011": 10}

        metrics = calculate_quantum_metrics(
            counts,
            problem,
            optimal_bitstring="110",
            optimal_objective=5.0,
        )

        assert "prob_optimal" in metrics
        assert metrics["prob_optimal"] == 0.6
        assert "approximation_ratio" in metrics
        assert metrics["found_optimal"] is True


class TestSolverComparison:
    """Test comparison of multiple solvers."""

    @pytest.fixture
    def sample_returns(self):
        """Generate sample returns."""
        np.random.seed(42)
        return np.random.randn(100, 10) * 0.01

    def test_basic_comparison(self, sample_returns):
        """Test basic solver comparison."""
        problem = PortfolioOptimization(
            returns=sample_returns,
            num_assets=4,
            target_size=2,
            seed=42,
        )

        solver_results = {
            "quantum_qaoa": {
                "best_bitstring": "1100",
                "best_objective": 12.0,
            },
            "brute_force": {
                "best_bitstring": "1010",
                "best_objective": 10.0,
            },
            "greedy": {
                "best_bitstring": "0110",
                "best_objective": 15.0,
            },
        }

        comparison = compare_solvers(solver_results, problem)

        assert comparison["best_solver"] == "brute_force"
        assert comparison["best_objective"] == 10.0
        assert comparison["worst_solver"] == "greedy"
        assert comparison["rankings"]["brute_force"] == 1
        assert comparison["rankings"]["quantum_qaoa"] == 2
        assert comparison["rankings"]["greedy"] == 3

    def test_with_optimal(self, sample_returns):
        """Test comparison with known optimal."""
        problem = PortfolioOptimization(
            returns=sample_returns,
            num_assets=4,
            target_size=2,
            seed=42,
        )

        solver_results = {
            "quantum": {"best_bitstring": "1100", "best_objective": 10.0},
            "classical": {"best_bitstring": "1010", "best_objective": 10.0},
        }

        comparison = compare_solvers(
            solver_results, problem, optimal_objective=10.0
        )

        assert "approximation_ratios_vs_optimal" in comparison
        assert comparison["optimal_found_by"] == ["quantum", "classical"]

    def test_feasibility_checking(self, sample_returns):
        """Test feasibility checking in comparison."""
        problem = PortfolioOptimization(
            returns=sample_returns,
            num_assets=4,
            target_size=2,
            seed=42,
        )

        solver_results = {
            "solver1": {"best_bitstring": "1100", "best_objective": 10.0},
            "solver2": {"best_bitstring": "1110", "best_objective": 8.0},  # Infeasible
        }

        comparison = compare_solvers(solver_results, problem)

        assert comparison["all_feasible"] is False
        assert "solver1" in comparison["feasible_solvers"]
        assert "solver2" not in comparison["feasible_solvers"]


class TestPortfolioPerformance:
    """Test portfolio performance metrics."""

    @pytest.fixture
    def sample_returns(self):
        """Generate sample returns."""
        np.random.seed(42)
        return np.random.randn(100, 10) * 0.01

    def test_feasible_portfolio(self, sample_returns):
        """Test metrics for feasible portfolio."""
        problem = PortfolioOptimization(
            returns=sample_returns,
            num_assets=4,
            target_size=2,
            seed=42,
        )

        metrics = calculate_portfolio_performance("1100", problem)

        assert metrics["is_feasible"] is True
        assert metrics["num_assets_selected"] == 2
        assert "sharpe_ratio" in metrics
        assert "annual_return" in metrics
        assert "annual_volatility" in metrics

    def test_infeasible_portfolio(self, sample_returns):
        """Test error for infeasible portfolio."""
        problem = PortfolioOptimization(
            returns=sample_returns,
            num_assets=4,
            target_size=2,
            seed=42,
        )

        metrics = calculate_portfolio_performance("1110", problem)

        assert metrics["is_feasible"] is False
        assert "error" in metrics


class TestBenchmarkingReport:
    """Test comprehensive benchmarking report."""

    @pytest.fixture
    def sample_returns(self):
        """Generate sample returns."""
        np.random.seed(42)
        return np.random.randn(100, 10) * 0.01

    def test_full_report_generation(self, sample_returns):
        """Test generating full benchmarking report."""
        problem = PortfolioOptimization(
            returns=sample_returns,
            num_assets=4,
            target_size=2,
            seed=42,
        )

        solver_results = {
            "quantum_qaoa": {
                "best_bitstring": "1100",
                "best_objective": 12.0,
                "runtime_s": 5.0,
            },
            "brute_force": {
                "best_bitstring": "1010",
                "best_objective": 10.0,
                "runtime_s": 1.0,
            },
            "simulated_annealing": {
                "best_bitstring": "0110",
                "best_objective": 11.0,
                "runtime_s": 2.0,
            },
        }

        report = generate_benchmarking_report(
            solver_results, problem, optimal_objective=10.0
        )

        # Check structure
        assert "problem_info" in report
        assert "num_solvers" in report
        assert report["num_solvers"] == 3
        assert "comparison" in report
        assert "solver_metrics" in report
        assert "runtime_analysis" in report
        assert "assessment" in report

        # Check runtime analysis
        assert report["runtime_analysis"]["fastest_solver"] == "brute_force"
        assert report["runtime_analysis"]["fastest_time_s"] == 1.0

    def test_honest_assessment(self, sample_returns):
        """Test honest assessment when classical wins."""
        problem = PortfolioOptimization(
            returns=sample_returns,
            num_assets=4,
            target_size=2,
            seed=42,
        )

        solver_results = {
            "quantum_qaoa": {
                "best_bitstring": "1100",
                "best_objective": 15.0,  # Worse
                "runtime_s": 10.0,
            },
            "brute_force": {
                "best_bitstring": "1010",
                "best_objective": 10.0,  # Better
                "runtime_s": 1.0,
            },
        }

        report = generate_benchmarking_report(
            solver_results, problem, optimal_objective=10.0
        )

        assessment = report["assessment"]

        # Should honestly report classical won
        assert "classical" in assessment["quantum_vs_classical"].lower()
        assert "outperformed" in assessment["quantum_vs_classical"].lower()

    def test_assessment_when_quantum_wins(self, sample_returns):
        """Test assessment when quantum wins."""
        problem = PortfolioOptimization(
            returns=sample_returns,
            num_assets=4,
            target_size=2,
            seed=42,
        )

        solver_results = {
            "quantum_qaoa": {
                "best_bitstring": "1010",
                "best_objective": 10.0,  # Better
                "runtime_s": 5.0,
            },
            "greedy": {
                "best_bitstring": "1100",
                "best_objective": 15.0,  # Worse
                "runtime_s": 0.5,
            },
        }

        report = generate_benchmarking_report(solver_results, problem)

        assessment = report["assessment"]

        # Should report quantum won
        assert "quantum" in assessment["quantum_vs_classical"].lower()
        assert "outperformed" in assessment["quantum_vs_classical"].lower()

    def test_portfolio_analysis_included(self, sample_returns):
        """Test that portfolio analysis is included."""
        problem = PortfolioOptimization(
            returns=sample_returns,
            num_assets=4,
            target_size=2,
            seed=42,
        )

        solver_results = {
            "quantum": {
                "best_bitstring": "1100",
                "best_objective": 10.0,
                "runtime_s": 5.0,
            },
        }

        report = generate_benchmarking_report(
            solver_results, problem, include_portfolio_metrics=True
        )

        assert "portfolio_analysis" in report
        assert "quantum" in report["portfolio_analysis"]
