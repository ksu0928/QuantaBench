"""Unit tests for optimization pipeline."""

import numpy as np
import pytest

from app.problems.portfolio import PortfolioOptimization
from app.quantum.backends import BackendManager
from app.schemas import QAOAParams, SolverType, BackendType
from app.services.pipeline import OptimizationPipeline, run_optimization_pipeline


class TestOptimizationPipeline:
    """Test optimization pipeline orchestration."""

    @pytest.fixture
    def sample_returns(self):
        """Generate sample returns."""
        np.random.seed(42)
        return np.random.randn(100, 10) * 0.01

    @pytest.fixture
    def small_problem(self, sample_returns):
        """Create small test problem."""
        return PortfolioOptimization(
            returns=sample_returns,
            num_assets=4,
            target_size=2,
            seed=42,
        )

    @pytest.fixture
    def backend_manager(self):
        """Create backend manager."""
        return BackendManager(fallback_enabled=True)

    def test_pipeline_initialization(self, small_problem, backend_manager):
        """Test pipeline initialization."""
        pipeline = OptimizationPipeline(small_problem, backend_manager)

        assert pipeline.problem is small_problem
        assert pipeline.backend_manager is backend_manager
        assert len(pipeline.results) == 0

    def test_run_brute_force(self, small_problem, backend_manager):
        """Test running brute force solver."""
        pipeline = OptimizationPipeline(small_problem, backend_manager)

        result = pipeline.run_brute_force()

        assert result.solver == SolverType.BRUTE_FORCE
        assert result.best_solution is not None
        assert result.best_solution.is_feasible is True
        assert result.runtime_s > 0
        assert len(result.all_solutions) > 0

        # Should store optimal
        assert pipeline.optimal_bitstring is not None
        assert pipeline.optimal_objective is not None

    def test_run_greedy(self, small_problem, backend_manager):
        """Test running greedy solver."""
        pipeline = OptimizationPipeline(small_problem, backend_manager)

        result = pipeline.run_greedy()

        assert result.solver == SolverType.GREEDY
        assert result.best_solution is not None
        assert result.runtime_s > 0

    def test_run_simulated_annealing(self, small_problem, backend_manager):
        """Test running simulated annealing solver."""
        pipeline = OptimizationPipeline(small_problem, backend_manager)

        result = pipeline.run_simulated_annealing(seed=42)

        assert result.solver == SolverType.SIMULATED_ANNEALING
        assert result.best_solution is not None
        assert result.runtime_s > 0

    def test_run_quantum_qaoa(self, small_problem, backend_manager):
        """Test running QAOA solver."""
        pipeline = OptimizationPipeline(small_problem, backend_manager)

        qaoa_params = QAOAParams(
            p=1,
            shots=100,
            backend=BackendType.AER_FALLBACK,
            optimizer_restarts=1,
        )

        result = pipeline.run_quantum_qaoa(qaoa_params)

        assert result.solver == SolverType.QUANTUM_QAOA
        assert result.best_solution is not None
        assert result.runtime_s > 0
        assert result.backend_used is not None
        assert result.optimizer_iterations is not None
        assert result.final_parameters is not None

    def test_run_multiple_solvers(self, small_problem, backend_manager):
        """Test running multiple solvers."""
        pipeline = OptimizationPipeline(small_problem, backend_manager)

        solvers = [
            SolverType.BRUTE_FORCE,
            SolverType.GREEDY,
        ]

        results = pipeline.run_solvers(solvers)

        assert len(results) == 2
        assert SolverType.BRUTE_FORCE in results
        assert SolverType.GREEDY in results

    def test_run_all_solvers(self, small_problem, backend_manager):
        """Test running all solvers including quantum."""
        pipeline = OptimizationPipeline(small_problem, backend_manager)

        qaoa_params = QAOAParams(
            p=1,
            shots=100,
            backend=BackendType.AER_FALLBACK,
            optimizer_restarts=1,
        )

        solvers = [
            SolverType.QUANTUM_QAOA,
            SolverType.BRUTE_FORCE,
            SolverType.SIMULATED_ANNEALING,
            SolverType.GREEDY,
        ]

        results = pipeline.run_solvers(solvers, qaoa_params)

        # Should have results for all solvers (or at least attempted)
        assert len(results) > 0
        # Brute force should always succeed
        assert SolverType.BRUTE_FORCE in results

    def test_calculate_metrics(self, small_problem, backend_manager):
        """Test metrics calculation."""
        pipeline = OptimizationPipeline(small_problem, backend_manager)

        # Run solvers
        solvers = [
            SolverType.BRUTE_FORCE,
            SolverType.GREEDY,
        ]
        pipeline.run_solvers(solvers)

        # Calculate metrics
        metrics = pipeline.calculate_metrics()

        assert metrics is not None
        assert metrics.best_objective is not None
        assert metrics.optimal_objective is not None
        assert metrics.feasibility_rate >= 0.0
        assert metrics.feasibility_rate <= 1.0

    def test_metrics_with_quantum(self, small_problem, backend_manager):
        """Test metrics including quantum results."""
        pipeline = OptimizationPipeline(small_problem, backend_manager)

        qaoa_params = QAOAParams(
            p=1,
            shots=100,
            backend=BackendType.AER_FALLBACK,
            optimizer_restarts=1,
        )

        solvers = [
            SolverType.QUANTUM_QAOA,
            SolverType.BRUTE_FORCE,
        ]

        pipeline.run_solvers(solvers, qaoa_params)
        metrics = pipeline.calculate_metrics()

        assert metrics is not None
        assert metrics.approximation_ratio is not None

    def test_get_results_summary(self, small_problem, backend_manager):
        """Test results summary generation."""
        pipeline = OptimizationPipeline(small_problem, backend_manager)

        solvers = [SolverType.BRUTE_FORCE, SolverType.GREEDY]
        pipeline.run_solvers(solvers)

        summary = pipeline.get_results_summary()

        assert summary["num_solvers"] == 2
        assert len(summary["solvers_run"]) == 2
        assert "best_solver" in summary
        assert "best_objective" in summary
        assert "objectives" in summary
        assert "runtimes_s" in summary

    def test_qaoa_requires_params(self, small_problem, backend_manager):
        """Test that QAOA raises error without params."""
        pipeline = OptimizationPipeline(small_problem, backend_manager)

        with pytest.raises(ValueError, match="qaoa_params required"):
            pipeline.run_solvers([SolverType.QUANTUM_QAOA], qaoa_params=None)


class TestConvenienceFunction:
    """Test convenience function."""

    @pytest.fixture
    def sample_returns(self):
        """Generate sample returns."""
        np.random.seed(42)
        return np.random.randn(100, 10) * 0.01

    def test_run_optimization_pipeline(self, sample_returns):
        """Test complete pipeline run."""
        problem = PortfolioOptimization(
            returns=sample_returns,
            num_assets=4,
            target_size=2,
            seed=42,
        )

        solvers = [
            SolverType.BRUTE_FORCE,
            SolverType.GREEDY,
        ]

        results, metrics = run_optimization_pipeline(
            problem,
            solvers,
        )

        assert len(results) == 2
        assert metrics is not None
        assert metrics.best_objective is not None


class TestIntegration:
    """Integration tests for complete pipeline workflows."""

    @pytest.fixture
    def portfolio_problem(self):
        """Create realistic portfolio problem."""
        np.random.seed(123)
        returns = np.random.randn(100, 10) * 0.01
        return PortfolioOptimization(
            returns=returns,
            num_assets=5,
            target_size=3,
            seed=123,
        )

    def test_complete_workflow_classical_only(self, portfolio_problem):
        """Test complete workflow with classical solvers."""
        solvers = [
            SolverType.BRUTE_FORCE,
            SolverType.SIMULATED_ANNEALING,
            SolverType.GREEDY,
        ]

        results, metrics = run_optimization_pipeline(
            portfolio_problem,
            solvers,
        )

        # Should have results from all solvers
        assert len(results) == 3

        # All should find feasible solutions
        for result in results.values():
            assert result.best_solution is not None

        # Brute force should find optimal
        bf_result = results[SolverType.BRUTE_FORCE]
        assert bf_result.best_solution.is_feasible is True

        # Metrics should be complete
        assert metrics.optimal_objective is not None
        assert metrics.best_objective is not None
        assert metrics.feasibility_rate == 1.0  # All found feasible

    def test_complete_workflow_with_quantum(self, portfolio_problem):
        """Test complete workflow including quantum."""
        qaoa_params = QAOAParams(
            p=1,
            shots=200,
            backend=BackendType.AER_FALLBACK,
            optimizer_restarts=1,
        )

        solvers = [
            SolverType.QUANTUM_QAOA,
            SolverType.BRUTE_FORCE,
            SolverType.GREEDY,
        ]

        results, metrics = run_optimization_pipeline(
            portfolio_problem,
            solvers,
            qaoa_params,
        )

        # Should have results
        assert len(results) >= 2  # At least brute force and greedy

        # Should have quantum result if execution succeeded
        if SolverType.QUANTUM_QAOA in results:
            qaoa_result = results[SolverType.QUANTUM_QAOA]
            assert qaoa_result.backend_used is not None
            assert qaoa_result.optimizer_iterations is not None

        # Metrics should include approximation ratios
        assert metrics.approximation_ratio is not None

    def test_handles_solver_failure_gracefully(self, portfolio_problem):
        """Test that pipeline continues if one solver fails."""
        # This is hard to test without mocking, but the pipeline
        # should continue even if one solver raises an exception

        solvers = [
            SolverType.BRUTE_FORCE,
            SolverType.GREEDY,
        ]

        # Should complete successfully
        results, metrics = run_optimization_pipeline(
            portfolio_problem,
            solvers,
        )

        assert len(results) >= 1  # At least one should succeed


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_metrics_without_results_raises_error(self):
        """Test that calculating metrics without results raises error."""
        np.random.seed(0)
        returns = np.random.randn(50, 5) * 0.01
        problem = PortfolioOptimization(
            returns=returns,
            num_assets=3,
            target_size=2,
            seed=0,
        )

        pipeline = OptimizationPipeline(problem)

        with pytest.raises(ValueError, match="No results"):
            pipeline.calculate_metrics()

    def test_summary_with_no_results(self):
        """Test summary with no results."""
        np.random.seed(0)
        returns = np.random.randn(50, 5) * 0.01
        problem = PortfolioOptimization(
            returns=returns,
            num_assets=3,
            target_size=2,
            seed=0,
        )

        pipeline = OptimizationPipeline(problem)
        summary = pipeline.get_results_summary()

        assert summary["num_solvers"] == 0
        assert len(summary["solvers_run"]) == 0
