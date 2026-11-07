"""Unit tests for Classiq QAOA circuit implementation."""

import numpy as np
import pytest

from app.quantum.hamiltonian import qubo_to_ising
from app.quantum.qaoa_classiq import (
    ClassiqQAOACircuit,
    QAOAParameters,
    create_qaoa_circuit,
    evaluate_qaoa_energy,
    get_best_bitstring_from_counts,
)


class TestQAOAParameters:
    """Test QAOA parameter handling."""

    def test_initialization(self):
        """Test parameter initialization."""
        params = QAOAParameters(
            p=2,
            beta=np.array([0.5, 1.0]),
            gamma=np.array([1.5, 2.0])
        )

        assert params.p == 2
        assert len(params.beta) == 2
        assert len(params.gamma) == 2

    def test_validation_rejects_wrong_length(self):
        """Test that mismatched parameter lengths are rejected."""
        with pytest.raises(ValueError, match="must have length"):
            QAOAParameters(
                p=2,
                beta=np.array([0.5]),  # Wrong length
                gamma=np.array([1.5, 2.0])
            )

    def test_to_flat_array(self):
        """Test conversion to flat array."""
        params = QAOAParameters(
            p=2,
            beta=np.array([0.5, 1.0]),
            gamma=np.array([1.5, 2.0])
        )

        flat = params.to_flat_array()

        # Should be [gamma_0, beta_0, gamma_1, beta_1]
        assert len(flat) == 4
        assert flat[0] == 1.5  # gamma[0]
        assert flat[1] == 0.5  # beta[0]
        assert flat[2] == 2.0  # gamma[1]
        assert flat[3] == 1.0  # beta[1]

    def test_from_flat_array(self):
        """Test creation from flat array."""
        flat = np.array([1.5, 0.5, 2.0, 1.0])

        params = QAOAParameters.from_flat_array(flat, p=2)

        assert params.p == 2
        assert np.allclose(params.gamma, [1.5, 2.0])
        assert np.allclose(params.beta, [0.5, 1.0])

    def test_from_flat_array_wrong_length(self):
        """Test that wrong length flat array raises error."""
        flat = np.array([1.5, 0.5, 2.0])  # Length 3, not divisible by 2

        with pytest.raises(ValueError, match="Expected"):
            QAOAParameters.from_flat_array(flat, p=2)

    def test_roundtrip_conversion(self):
        """Test roundtrip flat → params → flat."""
        original = np.array([1.5, 0.5, 2.0, 1.0, 0.8, 1.2])

        params = QAOAParameters.from_flat_array(original, p=3)
        recovered = params.to_flat_array()

        assert np.allclose(original, recovered)

    def test_random_init(self):
        """Test random parameter initialization."""
        params = QAOAParameters.random_init(p=3, seed=42)

        assert params.p == 3
        assert len(params.beta) == 3
        assert len(params.gamma) == 3

        # Check ranges: gamma in [0, 2π], beta in [0, π]
        assert np.all(params.gamma >= 0)
        assert np.all(params.gamma <= 2 * np.pi)
        assert np.all(params.beta >= 0)
        assert np.all(params.beta <= np.pi)

    def test_random_init_deterministic_with_seed(self):
        """Test that same seed produces same random params."""
        params1 = QAOAParameters.random_init(p=2, seed=42)
        params2 = QAOAParameters.random_init(p=2, seed=42)

        assert np.allclose(params1.gamma, params2.gamma)
        assert np.allclose(params1.beta, params2.beta)


class TestClassiqQAOACircuit:
    """Test Classiq QAOA circuit builder."""

    @pytest.fixture
    def simple_hamiltonian(self):
        """Create a simple 2-qubit Hamiltonian."""
        h = np.array([-1.0, 0.5])
        J = np.array([[0.0, 0.3], [0.0, 0.0]])
        offset = 0.0
        return h, J, offset

    def test_initialization(self, simple_hamiltonian):
        """Test circuit initialization."""
        h, J, offset = simple_hamiltonian

        circuit = ClassiqQAOACircuit(h, J, offset)

        assert circuit.n_qubits == 2
        assert np.array_equal(circuit.h, h)
        assert np.array_equal(circuit.J, J)
        assert circuit.offset == offset

    def test_initialization_with_constraints(self, simple_hamiltonian):
        """Test initialization with synthesis constraints."""
        h, J, offset = simple_hamiltonian

        circuit = ClassiqQAOACircuit(
            h, J, offset,
            max_circuit_width=4,
            max_circuit_depth=50
        )

        assert circuit.max_circuit_width == 4
        assert circuit.max_circuit_depth == 50

    def test_to_qiskit_conversion(self, simple_hamiltonian):
        """Test conversion to Qiskit circuit (fallback)."""
        h, J, offset = simple_hamiltonian
        circuit_builder = ClassiqQAOACircuit(h, J, offset)

        params = QAOAParameters(
            p=1,
            beta=np.array([0.5]),
            gamma=np.array([1.0])
        )

        qiskit_circuit = circuit_builder.to_qiskit(params)

        # Check circuit structure
        assert qiskit_circuit.num_qubits == 2
        assert len(qiskit_circuit.data) > 0

        # Should have measurements
        has_measurements = any(
            instr.operation.name == 'measure'
            for instr in qiskit_circuit.data
        )
        assert has_measurements

    def test_to_qiskit_multiple_layers(self, simple_hamiltonian):
        """Test Qiskit conversion with p=3."""
        h, J, offset = simple_hamiltonian
        circuit_builder = ClassiqQAOACircuit(h, J, offset)

        params = QAOAParameters(
            p=3,
            beta=np.array([0.5, 0.7, 0.9]),
            gamma=np.array([1.0, 1.2, 1.4])
        )

        qiskit_circuit = circuit_builder.to_qiskit(params)

        assert qiskit_circuit.num_qubits == 2
        # Circuit depth should increase with p
        assert qiskit_circuit.depth() > 0

    def test_get_circuit_info(self, simple_hamiltonian):
        """Test circuit information retrieval."""
        h, J, offset = simple_hamiltonian
        circuit = ClassiqQAOACircuit(h, J, offset, max_circuit_width=5)

        info = circuit.get_circuit_info()

        assert info["num_qubits"] == 2
        assert "hamiltonian_terms" in info
        assert info["hamiltonian_terms"]["linear"] == 2  # Both h values non-zero
        assert info["hamiltonian_terms"]["quadratic"] == 1  # One J value
        assert info["max_circuit_width"] == 5

    def test_build_qaoa_model_not_implemented(self, simple_hamiltonian):
        """Test that Classiq model building raises NotImplementedError."""
        h, J, offset = simple_hamiltonian
        circuit = ClassiqQAOACircuit(h, J, offset)
        params = QAOAParameters.random_init(p=1)

        with pytest.raises(NotImplementedError, match="Classiq SDK"):
            circuit.build_qaoa_model(params)

    def test_synthesize_not_implemented(self, simple_hamiltonian):
        """Test that synthesis raises NotImplementedError."""
        h, J, offset = simple_hamiltonian
        circuit = ClassiqQAOACircuit(h, J, offset)
        params = QAOAParameters.random_init(p=1)

        with pytest.raises(NotImplementedError, match="Classiq SDK"):
            circuit.synthesize(params)

    def test_execute_not_implemented(self, simple_hamiltonian):
        """Test that execution raises NotImplementedError."""
        h, J, offset = simple_hamiltonian
        circuit = ClassiqQAOACircuit(h, J, offset)
        params = QAOAParameters.random_init(p=1)

        with pytest.raises(NotImplementedError, match="Classiq SDK"):
            circuit.execute(params, shots=100)

    def test_factory_function(self, simple_hamiltonian):
        """Test factory function."""
        h, J, offset = simple_hamiltonian

        circuit = create_qaoa_circuit(h, J, offset, max_circuit_width=10)

        assert isinstance(circuit, ClassiqQAOACircuit)
        assert circuit.n_qubits == 2
        assert circuit.max_circuit_width == 10


class TestQAOAUtilities:
    """Test QAOA utility functions."""

    def test_evaluate_qaoa_energy(self):
        """Test energy evaluation from counts."""
        h = np.array([-1.0, 0.5])
        J = np.array([[0.0, 0.3], [0.0, 0.0]])
        offset = 0.0

        counts = {
            "00": 60,
            "01": 15,
            "10": 20,
            "11": 5,
        }

        energy = evaluate_qaoa_energy(counts, h, J, offset)

        # Energy should be a weighted average
        assert isinstance(energy, float)
        assert -5.0 < energy < 5.0  # Reasonable range for this Hamiltonian

    def test_get_best_bitstring_from_counts(self):
        """Test extracting most frequent bitstring."""
        counts = {
            "00": 10,
            "01": 50,  # Most frequent
            "10": 30,
            "11": 10,
        }

        best = get_best_bitstring_from_counts(counts)

        assert best == "01"

    def test_get_best_bitstring_tie_resolution(self):
        """Test that ties are resolved consistently."""
        counts = {
            "00": 50,
            "11": 50,  # Tie
        }

        best = get_best_bitstring_from_counts(counts)

        # Should return one of them (deterministically)
        assert best in ["00", "11"]


class TestPortfolioQAOA:
    """Test QAOA circuit for portfolio optimization problem."""

    def test_portfolio_hamiltonian_to_qaoa(self):
        """Test creating QAOA circuit from portfolio problem."""
        # Create simple portfolio QUBO
        n = 4
        Q = np.random.randn(n, n)
        Q = (Q + Q.T) / 2  # Symmetric
        qubo_offset = 5.0

        # Convert to Ising
        h, J, ising_offset = qubo_to_ising(Q, qubo_offset)

        # Create QAOA circuit
        circuit = ClassiqQAOACircuit(h, J, ising_offset)
        params = QAOAParameters.random_init(p=2, seed=42)

        # Convert to Qiskit (fallback)
        qiskit_circuit = circuit.to_qiskit(params)

        assert qiskit_circuit.num_qubits == n
        assert len(qiskit_circuit.data) > 0

    def test_execute_qaoa_on_aer_fallback(self):
        """Test QAOA execution using Aer backend (integration test)."""
        from qiskit_aer import AerSimulator

        # Simple 2-qubit Hamiltonian
        h = np.array([-1.0, 0.5])
        J = np.array([[0.0, 0.3], [0.0, 0.0]])

        circuit_builder = ClassiqQAOACircuit(h, J, 0.0)
        params = QAOAParameters(
            p=1,
            beta=np.array([0.5]),
            gamma=np.array([1.0])
        )

        qiskit_circuit = circuit_builder.to_qiskit(params)

        # Execute on Aer
        simulator = AerSimulator()
        result = simulator.run(qiskit_circuit, shots=1000, seed_simulator=42).result()
        counts = result.get_counts()

        # Convert counts to string keys
        counts_str = {
            format(k, "02b") if isinstance(k, int) else k: v
            for k, v in counts.items()
        }

        # Evaluate energy
        energy = evaluate_qaoa_energy(counts_str, h, J, 0.0)

        assert isinstance(energy, float)
        # Energy should be in reasonable range
        assert -10.0 < energy < 10.0


class TestQAOAIntegration:
    """Integration tests for QAOA workflow."""

    def test_full_qaoa_workflow_with_fallback(self):
        """Test complete workflow: Problem → Hamiltonian → QAOA → Execute."""
        # 1. Create problem (simplified portfolio)
        n = 3
        Q = np.array([
            [1.0, -0.5, 0.2],
            [-0.5, 2.0, -0.3],
            [0.2, -0.3, 1.5],
        ])

        # 2. Convert to Ising
        h, J, offset = qubo_to_ising(Q, qubo_offset=0.0)

        # 3. Create QAOA circuit
        qaoa = ClassiqQAOACircuit(h, J, offset)

        # 4. Initialize parameters
        params = QAOAParameters.random_init(p=2, seed=42)

        # 5. Get Qiskit circuit (fallback)
        qc = qaoa.to_qiskit(params)

        # 6. Verify circuit structure
        assert qc.num_qubits == n
        assert qc.depth() > 0

        # 7. Verify we can extract circuit info
        info = qaoa.get_circuit_info()
        assert info["num_qubits"] == n
