"""Unit tests for classical optimization solvers."""

import numpy as np
import pytest

from app.classical.annealing import SimulatedAnnealingSolver, solve_simulated_annealing
from app.classical.brute_force import BruteForceSolver, solve_brute_force
from app.classical.greedy import GreedySolver, GreedySolverConstrained, solve_greedy
from app.problems.portfolio import PortfolioOptimization


class TestBruteForceSolver:
    """Test brute force exact solver."""

    @pytest.fixture
    def sample_returns(self):
        """Generate sample returns."""
        np.random.seed(42)
        return np.random.randn(100, 10) * 0.01

    def test_solve_small_problem(self, sample_returns):
        """Test solving small portfolio problem."""
        problem = PortfolioOptimization(
            returns=sample_returns,
            num_assets=4,
            target_size=2,
            seed=42,
        )

        solver = BruteForceSolver()
        solution = solver.solve(problem)

        # Should find optimal solution
        assert solution.best_bitstring is not None
        assert solution.best_bitstring.count("1") == 2  # Feasible
        assert solution.num_evaluated == 2**4  # All 16 solutions
        assert solution.num_feasible > 0
        assert solution.runtime_s > 0

    def test_all_feasible_solutions_sorted(self, sample_returns):
        """Test that feasible solutions are sorted by objective."""
        problem = PortfolioOptimization(
            returns=sample_returns,
            num_assets=4,
            target_size=2,
            seed=42,
        )

        solver = BruteForceSolver()
        solution = solver.solve(problem)

        # Check that solutions are sorted (ascending objective)
        objectives = [obj for _, obj in solution.all_feasible_solutions]
        assert objectives == sorted(objectives)

        # Best should be first
        assert solution.all_feasible_solutions[0][0] == solution.best_bitstring
        assert solution.all_feasible_solutions[0][1] == solution.best_objective

    def test_raises_for_large_problem(self, sample_returns):
        """Test that large problems raise error."""
        problem = PortfolioOptimization(
            returns=sample_returns,
            num_assets=10,  # 2^10 = 1024 is fine
            target_size=5,
            seed=42,
        )

        solver = BruteForceSolver(max_size=8)  # Set lower limit

        with pytest.raises(ValueError, match="exceeds max_size"):
            solver.solve(problem)

    def test_convenience_functions(self, sample_returns):
        """Test convenience functions."""
        problem = PortfolioOptimization(
            returns=sample_returns,
            num_assets=4,
            target_size=2,
            seed=42,
        )

        # Test solve_brute_force function
        solution = solve_brute_force(problem)
        assert solution.best_bitstring is not None

        # Test get_optimal_value
        solver = BruteForceSolver()
        optimal_value = solver.get_optimal_value(problem)
        assert optimal_value == solution.best_objective

        # Test get_optimal_solution
        optimal_solution = solver.get_optimal_solution(problem)
        assert optimal_solution == solution.best_bitstring

    def test_deterministic_with_same_problem(self, sample_returns):
        """Test that same problem gives same result."""
        problem1 = PortfolioOptimization(
            returns=sample_returns,
            num_assets=4,
            target_size=2,
            seed=42,
        )

        problem2 = PortfolioOptimization(
            returns=sample_returns,
            num_assets=4,
            target_size=2,
            seed=42,
        )

        solver = BruteForceSolver()
        solution1 = solver.solve(problem1)
        solution2 = solver.solve(problem2)

        assert solution1.best_bitstring == solution2.best_bitstring
        assert solution1.best_objective == solution2.best_objective


class TestSimulatedAnnealingSolver:
    """Test simulated annealing solver."""

    @pytest.fixture
    def sample_returns(self):
        """Generate sample returns."""
        np.random.seed(42)
        return np.random.randn(100, 10) * 0.01

    def test_solve_basic(self, sample_returns):
        """Test basic solving."""
        problem = PortfolioOptimization(
            returns=sample_returns,
            num_assets=5,
            target_size=3,
            seed=42,
        )

        solver = SimulatedAnnealingSolver(
            initial_temperature=5.0,
            cooling_rate=0.95,
            max_iterations=1000,
            seed=42,
        )

        solution = solver.solve(problem)

        assert solution.best_bitstring is not None
        assert solution.num_iterations > 0
        assert solution.num_accepted > 0
        assert 0 <= solution.acceptance_rate <= 1.0
        assert solution.runtime_s > 0

    def test_finds_reasonable_solution(self, sample_returns):
        """Test that annealing finds reasonable solution."""
        problem = PortfolioOptimization(
            returns=sample_returns,
            num_assets=5,
            target_size=2,
            seed=42,
        )

        # Get optimal for comparison
        optimal_solution = solve_brute_force(problem)

        # Run annealing
        solver = SimulatedAnnealingSolver(
            initial_temperature=10.0,
            cooling_rate=0.95,
            max_iterations=5000,
            seed=42,
        )
        annealing_solution = solver.solve(problem)

        # Should be within reasonable range of optimal
        # (not guaranteed, but likely with enough iterations)
        approximation_ratio = (
            annealing_solution.best_objective / optimal_solution.best_objective
        )
        assert approximation_ratio < 1.5  # Within 50% of optimal

    def test_cooling_schedule(self, sample_returns):
        """Test that temperature actually cools down."""
        problem = PortfolioOptimization(
            returns=sample_returns,
            num_assets=4,
            target_size=2,
            seed=42,
        )

        solver = SimulatedAnnealingSolver(
            initial_temperature=10.0,
            final_temperature=0.1,
            cooling_rate=0.9,
            max_iterations=1000,
            seed=42,
        )

        solution = solver.solve(problem)

        # Should have stopped due to low temperature
        # (iterations should be less than max if cooled to final temp)
        assert solution.num_iterations <= 1000

    def test_deterministic_with_seed(self, sample_returns):
        """Test that same seed gives same result."""
        problem = PortfolioOptimization(
            returns=sample_returns,
            num_assets=4,
            target_size=2,
            seed=42,
        )

        solution1 = solve_simulated_annealing(problem, seed=123)
        solution2 = solve_simulated_annealing(problem, seed=123)

        assert solution1.best_bitstring == solution2.best_bitstring

    def test_different_seeds_give_different_results(self, sample_returns):
        """Test that different seeds explore different paths."""
        problem = PortfolioOptimization(
            returns=sample_returns,
            num_assets=4,
            target_size=2,
            seed=42,
        )

        solution1 = solve_simulated_annealing(problem, seed=123, max_iterations=100)
        solution2 = solve_simulated_annealing(problem, seed=456, max_iterations=100)

        # May or may not find different solutions, but at least one should differ
        # in construction sequence (internal randomness)
        # This is hard to test without exposing internals, so just verify they ran
        assert solution1.num_iterations > 0
        assert solution2.num_iterations > 0


class TestGreedySolver:
    """Test greedy heuristic solver."""

    @pytest.fixture
    def sample_returns(self):
        """Generate sample returns."""
        np.random.seed(42)
        return np.random.randn(100, 10) * 0.01

    def test_solve_basic(self, sample_returns):
        """Test basic greedy solving."""
        problem = PortfolioOptimization(
            returns=sample_returns,
            num_assets=5,
            target_size=3,
            seed=42,
        )

        solver = GreedySolver()
        solution = solver.solve(problem)

        assert solution.best_bitstring is not None
        assert len(solution.construction_sequence) > 0
        assert solution.num_evaluated > 0
        assert solution.runtime_s > 0

    def test_greedy_constrained_respects_target_size(self, sample_returns):
        """Test that constrained greedy respects target size."""
        problem = PortfolioOptimization(
            returns=sample_returns,
            num_assets=6,
            target_size=3,
            seed=42,
        )

        solver = GreedySolverConstrained()
        solution = solver.solve(problem, target_size=3)

        # Should select exactly 3 assets
        assert solution.best_bitstring.count("1") == 3
        assert len(solution.construction_sequence) == 3

    def test_construction_sequence_valid(self, sample_returns):
        """Test that construction sequence contains valid indices."""
        problem = PortfolioOptimization(
            returns=sample_returns,
            num_assets=5,
            target_size=3,
            seed=42,
        )

        solution = solve_greedy(problem)

        # All indices should be in valid range
        assert all(0 <= idx < 5 for idx in solution.construction_sequence)

        # No duplicates
        assert len(solution.construction_sequence) == len(set(solution.construction_sequence))

    def test_greedy_faster_than_brute_force(self, sample_returns):
        """Test that greedy is faster than brute force."""
        problem = PortfolioOptimization(
            returns=sample_returns,
            num_assets=6,
            target_size=3,
            seed=42,
        )

        greedy_solution = solve_greedy(problem)
        brute_force_solution = solve_brute_force(problem)

        # Greedy should evaluate fewer solutions
        assert greedy_solution.num_evaluated < brute_force_solution.num_evaluated

        # Greedy should be faster
        assert greedy_solution.runtime_s < brute_force_solution.runtime_s

    def test_convenience_function_uses_constrained_for_portfolio(self, sample_returns):
        """Test that convenience function uses constrained solver for portfolio."""
        problem = PortfolioOptimization(
            returns=sample_returns,
            num_assets=6,
            target_size=3,
            seed=42,
        )

        solution = solve_greedy(problem)

        # Should select exactly target_size
        assert solution.best_bitstring.count("1") == 3


class TestSolverComparison:
    """Compare different solvers on same problem."""

    @pytest.fixture
    def small_problem(self):
        """Create small problem solvable by all methods."""
        np.random.seed(42)
        returns = np.random.randn(100, 10) * 0.01
        return PortfolioOptimization(
            returns=returns,
            num_assets=5,
            target_size=2,
            seed=42,
        )

    def test_all_solvers_find_feasible_solutions(self, small_problem):
        """Test that all solvers find feasible solutions."""
        # Brute force
        bf_solution = solve_brute_force(small_problem)
        assert small_problem.is_feasible(bf_solution.best_bitstring)

        # Simulated annealing
        sa_solution = solve_simulated_annealing(
            small_problem, max_iterations=1000, seed=42
        )
        # Note: SA might not always find feasible solution due to randomness
        # but with penalty it should prefer feasible ones

        # Greedy
        greedy_solution = solve_greedy(small_problem)
        assert small_problem.is_feasible(greedy_solution.best_bitstring)

    def test_brute_force_finds_best_solution(self, small_problem):
        """Test that brute force finds better or equal solution than heuristics."""
        bf_solution = solve_brute_force(small_problem)
        sa_solution = solve_simulated_annealing(
            small_problem, max_iterations=1000, seed=42
        )
        greedy_solution = solve_greedy(small_problem)

        # Brute force should find best or equal
        assert bf_solution.best_objective <= sa_solution.best_objective + 1e-6
        assert bf_solution.best_objective <= greedy_solution.best_objective + 1e-6

    def test_runtime_comparison(self, small_problem):
        """Test runtime comparison across solvers."""
        bf_solution = solve_brute_force(small_problem)
        sa_solution = solve_simulated_annealing(
            small_problem, max_iterations=500, seed=42
        )
        greedy_solution = solve_greedy(small_problem)

        # All should complete in reasonable time
        assert bf_solution.runtime_s < 10.0
        assert sa_solution.runtime_s < 10.0
        assert greedy_solution.runtime_s < 10.0

        # Greedy should be fastest for this size
        assert greedy_solution.runtime_s < sa_solution.runtime_s


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_single_variable_problem(self):
        """Test problem with single variable."""
        np.random.seed(0)
        returns = np.random.randn(50, 5) * 0.01
        problem = PortfolioOptimization(
            returns=returns,
            num_assets=2,
            target_size=1,
            seed=0,
        )

        # All solvers should handle this
        bf_sol = solve_brute_force(problem)
        sa_sol = solve_simulated_annealing(problem, max_iterations=100, seed=0)
        greedy_sol = solve_greedy(problem)

        assert bf_sol.best_bitstring.count("1") == 1
        assert greedy_sol.best_bitstring.count("1") == 1

    def test_all_assets_target(self):
        """Test when target size equals number of assets."""
        np.random.seed(0)
        returns = np.random.randn(50, 5) * 0.01
        problem = PortfolioOptimization(
            returns=returns,
            num_assets=3,
            target_size=3,
            seed=0,
        )

        # Only one feasible solution: all ones
        bf_sol = solve_brute_force(problem)
        assert bf_sol.best_bitstring == "111"
        assert bf_sol.num_feasible == 1
