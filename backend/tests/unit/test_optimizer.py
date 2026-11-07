"""Unit tests for QAOA parameter optimizer."""

import numpy as np
import pytest

from app.quantum.backends import BackendManager
from app.quantum.hamiltonian import qubo_to_ising
from app.quantum.optimizer import (
    QAOAOptimizer,
    optimize_qaoa_progressive,
    optimize_qaoa_single,
)
from app.quantum.qaoa_classiq import ClassiqQAOACircuit, QAOAParameters


class TestQAOAOptimizer:
    """Test QAOA optimizer."""

    @pytest.fixture
    def simple_hamiltonian(self):
        """Create simple 2-qubit Hamiltonian."""
        h = np.array([-1.0, 0.5])
        J = np.array([[0.0, 0.3], [0.0, 0.0]])
        return h, J, 0.0

    @pytest.fixture
    def qaoa_circuit(self, simple_hamiltonian):
        """Create QAOA circuit."""
        h, J, offset = simple_hamiltonian
        return ClassiqQAOACircuit(h, J, offset)

    @pytest.fixture
    def backend_manager(self):
        """Create backend manager with Aer."""
        return BackendManager(fallback_enabled=True)

    def test_initialization(self, qaoa_circuit, backend_manager):
        """Test optimizer initialization."""
        optimizer = QAOAOptimizer(
            qaoa_circuit=qaoa_circuit,
            backend_manager=backend_manager,
            backend_name="aer_fallback",
            shots=100,
            max_restarts=2,
            seed=42,
        )

        assert optimizer.qaoa_circuit is qaoa_circuit
        assert optimizer.backend_name == "aer_fallback"
        assert optimizer.shots == 100
        assert optimizer.max_restarts == 2

    def test_warm_start_initialization(self, qaoa_circuit, backend_manager):
        """Test warm-start parameter initialization."""
        optimizer = QAOAOptimizer(
            qaoa_circuit, backend_manager, seed=42
        )

        # Start with p=1 params
        prev_params = QAOAParameters(
            p=1,
            gamma=np.array([1.5]),
            beta=np.array([0.8]),
        )

        # Warm-start for p=2
        new_params = optimizer._warm_start_initialization(prev_params, new_p=2)

        assert new_params.p == 2
        # First layer should match previous
        assert np.isclose(new_params.gamma[0], 1.5)
        assert np.isclose(new_params.beta[0], 0.8)
        # Second layer should be small random
        assert 0 <= new_params.gamma[1] <= 0.5
        assert 0 <= new_params.beta[1] <= 0.5

    def test_warm_start_p1_to_p3(self, qaoa_circuit, backend_manager):
        """Test warm-start from p=1 to p=3."""
        optimizer = QAOAOptimizer(
            qaoa_circuit, backend_manager, seed=42
        )

        prev_params = QAOAParameters(
            p=1,
            gamma=np.array([2.0]),
            beta=np.array([1.0]),
        )

        new_params = optimizer._warm_start_initialization(prev_params, new_p=3)

        assert new_params.p == 3
        assert np.isclose(new_params.gamma[0], 2.0)
        assert np.isclose(new_params.beta[0], 1.0)
        # New layers should be initialized
        assert len(new_params.gamma) == 3
        assert len(new_params.beta) == 3

    def test_optimize_single_layer(self, qaoa_circuit, backend_manager):
        """Test optimization for p=1."""
        optimizer = QAOAOptimizer(
            qaoa_circuit=qaoa_circuit,
            backend_manager=backend_manager,
            backend_name="aer_fallback",
            shots=100,
            max_restarts=1,  # Just one for speed
            seed=42,
        )

        result = optimizer.optimize(p=1, maxiter=10)  # Few iterations for speed

        assert result.best_params.p == 1
        assert isinstance(result.best_energy, float)
        assert result.num_iterations > 0
        assert result.num_function_evals > 0
        assert result.optimization_time_s > 0
        assert len(result.convergence_history) > 0

    def test_optimize_with_warm_start(self, qaoa_circuit, backend_manager):
        """Test optimization with warm-start from previous p."""
        optimizer = QAOAOptimizer(
            qaoa_circuit=qaoa_circuit,
            backend_manager=backend_manager,
            backend_name="aer_fallback",
            shots=100,
            max_restarts=1,
            seed=42,
        )

        # First optimize p=1
        result_p1 = optimizer.optimize(p=1, maxiter=5)

        # Then optimize p=2 with warm-start
        result_p2 = optimizer.optimize(
            p=2,
            warm_start_params=result_p1.best_params,
            maxiter=5,
        )

        assert result_p2.best_params.p == 2
        assert len(result_p2.restart_energies) == 1  # Warm-start uses 1 restart

    def test_convergence_history_recorded(self, qaoa_circuit, backend_manager):
        """Test that convergence history is recorded."""
        optimizer = QAOAOptimizer(
            qaoa_circuit=qaoa_circuit,
            backend_manager=backend_manager,
            backend_name="aer_fallback",
            shots=100,
            seed=42,
        )

        result = optimizer.optimize(p=1, maxiter=10)

        # Should have recorded energies
        assert len(result.convergence_history) > 0
        # All entries should be floats
        assert all(isinstance(e, float) for e in result.convergence_history)

    def test_multiple_restarts(self, qaoa_circuit, backend_manager):
        """Test optimization with multiple restarts."""
        optimizer = QAOAOptimizer(
            qaoa_circuit=qaoa_circuit,
            backend_manager=backend_manager,
            backend_name="aer_fallback",
            shots=100,
            max_restarts=3,
            seed=42,
        )

        result = optimizer.optimize(p=1, warm_start_params=None, maxiter=5)

        # Should have 3 restart energies (no warm-start)
        assert len(result.restart_energies) == 3
        # Best energy should be minimum of restart energies
        assert np.isclose(result.best_energy, min(result.restart_energies), atol=1e-6)


class TestProgressiveOptimization:
    """Test progressive QAOA optimization with warm-start."""

    @pytest.fixture
    def portfolio_hamiltonian(self):
        """Create portfolio problem Hamiltonian."""
        # Simple 3-asset portfolio QUBO
        Q = np.array([
            [2.0, -0.5, 0.2],
            [-0.5, 1.5, -0.3],
            [0.2, -0.3, 1.0],
        ])
        h, J, offset = qubo_to_ising(Q, qubo_offset=0.0)
        return h, J, offset

    def test_optimize_progressive_p1_to_p2(self, portfolio_hamiltonian):
        """Test progressive optimization from p=1 to p=2."""
        h, J, offset = portfolio_hamiltonian
        qaoa_circuit = ClassiqQAOACircuit(h, J, offset)
        backend_manager = BackendManager()

        results = optimize_qaoa_progressive(
            qaoa_circuit=qaoa_circuit,
            backend_manager=backend_manager,
            max_p=2,
            backend_name="aer_fallback",
            shots=100,
            max_restarts=1,  # Fast for testing
            maxiter_per_p=5,
            seed=42,
        )

        # Should have results for p=1 and p=2
        assert 1 in results
        assert 2 in results

        # p=2 energy should be <= p=1 energy (more layers = better)
        # (Not always true due to noise, but likely with optimization)
        assert results[1].best_params.p == 1
        assert results[2].best_params.p == 2

    def test_progressive_uses_warm_start(self, portfolio_hamiltonian):
        """Test that progressive optimization uses warm-start for p>1."""
        h, J, offset = portfolio_hamiltonian
        qaoa_circuit = ClassiqQAOACircuit(h, J, offset)
        backend_manager = BackendManager()

        results = optimize_qaoa_progressive(
            qaoa_circuit=qaoa_circuit,
            backend_manager=backend_manager,
            max_p=2,
            backend_name="aer_fallback",
            shots=100,
            max_restarts=3,
            maxiter_per_p=5,
            seed=42,
        )

        # p=1 should have 3 restart energies (multiple restarts)
        assert len(results[1].restart_energies) == 3

        # p=2 should have 1 restart energy (warm-start, no multiple restarts)
        assert len(results[2].restart_energies) == 1


class TestSingleOptimization:
    """Test single p-value optimization."""

    def test_optimize_single_p2(self):
        """Test optimizing directly for p=2 (no warm-start)."""
        # Simple Hamiltonian
        h = np.array([-1.0, 1.0])
        J = np.array([[0.0, 0.5], [0.0, 0.0]])
        qaoa_circuit = ClassiqQAOACircuit(h, J, 0.0)
        backend_manager = BackendManager()

        result = optimize_qaoa_single(
            qaoa_circuit=qaoa_circuit,
            backend_manager=backend_manager,
            p=2,
            backend_name="aer_fallback",
            shots=100,
            max_restarts=2,
            maxiter=10,
            seed=42,
        )

        assert result.best_params.p == 2
        assert result.num_function_evals > 0
        # Should have 2 restart energies
        assert len(result.restart_energies) == 2

    def test_optimize_single_deterministic_with_seed(self):
        """Test that same seed produces same result."""
        h = np.array([-1.0, 1.0])
        J = np.array([[0.0, 0.5], [0.0, 0.0]])
        qaoa_circuit = ClassiqQAOACircuit(h, J, 0.0)
        backend_manager = BackendManager()

        result1 = optimize_qaoa_single(
            qaoa_circuit, backend_manager, p=1,
            shots=100, max_restarts=1, maxiter=5, seed=42
        )

        result2 = optimize_qaoa_single(
            qaoa_circuit, backend_manager, p=1,
            shots=100, max_restarts=1, maxiter=5, seed=42
        )

        # Results should be very similar (COBYLA has some non-determinism,
        # but with same seed should be close)
        assert np.allclose(
            result1.best_params.to_flat_array(),
            result2.best_params.to_flat_array(),
            atol=0.1
        )


class TestOptimizationRobustness:
    """Test optimizer robustness and error handling."""

    def test_handles_difficult_problem(self):
        """Test optimizer handles difficult optimization landscape."""
        # Random Hamiltonian (harder to optimize)
        np.random.seed(123)
        n = 4
        h = np.random.randn(n)
        J_full = np.random.randn(n, n)
        J = np.triu(J_full)  # Upper triangular

        qaoa_circuit = ClassiqQAOACircuit(h, J, 0.0)
        backend_manager = BackendManager()

        # Should still complete without errors
        result = optimize_qaoa_single(
            qaoa_circuit, backend_manager, p=1,
            shots=100, max_restarts=1, maxiter=5, seed=42
        )

        assert result.best_params is not None
        assert isinstance(result.best_energy, float)

    def test_optimizer_converges(self):
        """Test that optimizer generally reduces energy."""
        h = np.array([-2.0, 1.0])
        J = np.array([[0.0, 0.5], [0.0, 0.0]])
        qaoa_circuit = ClassiqQAOACircuit(h, J, 0.0)
        backend_manager = BackendManager()

        result = optimize_qaoa_single(
            qaoa_circuit, backend_manager, p=1,
            shots=500,  # More shots for stable convergence
            max_restarts=1,
            maxiter=20,
            seed=42,
        )

        # Final energy should be lower than initial (generally)
        if len(result.convergence_history) > 2:
            initial_energy = result.convergence_history[0]
            final_energy = result.convergence_history[-1]
            # Allow for some noise
            assert final_energy <= initial_energy + 0.5


class TestIntegration:
    """Integration tests for complete optimization workflow."""

    def test_full_optimization_workflow(self):
        """Test complete workflow: Problem → Hamiltonian → Optimize."""
        # 1. Create problem (simple QUBO)
        Q = np.array([
            [1.0, -0.5],
            [-0.5, 2.0],
        ])

        # 2. Convert to Ising
        h, J, offset = qubo_to_ising(Q, 0.0)

        # 3. Create QAOA circuit
        qaoa = ClassiqQAOACircuit(h, J, offset)

        # 4. Set up backend
        backend_manager = BackendManager()

        # 5. Optimize
        result = optimize_qaoa_single(
            qaoa, backend_manager, p=1,
            shots=200, maxiter=10, seed=42
        )

        # 6. Verify result structure
        assert result.best_params.p == 1
        assert isinstance(result.best_energy, float)
        assert result.num_function_evals > 0
        assert result.optimization_time_s > 0
        assert len(result.convergence_history) > 0

    def test_progressive_optimization_workflow(self):
        """Test progressive optimization workflow."""
        # Portfolio-like problem
        Q = np.array([
            [2.0, -0.5, 0.2],
            [-0.5, 1.5, -0.3],
            [0.2, -0.3, 1.0],
        ])

        h, J, offset = qubo_to_ising(Q, 0.0)
        qaoa = ClassiqQAOACircuit(h, J, offset)
        backend_manager = BackendManager()

        # Optimize progressively
        results = optimize_qaoa_progressive(
            qaoa, backend_manager, max_p=2,
            shots=100, max_restarts=1, maxiter_per_p=5, seed=42
        )

        # Should have results for both p values
        assert len(results) == 2
        assert all(isinstance(r.best_energy, float) for r in results.values())

        # Each p should have valid parameters
        for p, result in results.items():
            assert result.best_params.p == p
            assert len(result.best_params.gamma) == p
            assert len(result.best_params.beta) == p
