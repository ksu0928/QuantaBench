"""Unit tests for quantum backend adapters."""

import pytest
from qiskit import QuantumCircuit

from app.quantum.backends import (
    AerBackend,
    BackendError,
    BackendManager,
    ClassiqBackend,
    ExecutionResult,
    QBraidBackend,
    get_backend_manager,
)


class TestAerBackend:
    """Test Aer simulator backend."""

    def test_is_always_available(self):
        """Test that Aer is always available."""
        backend = AerBackend()
        assert backend.is_available() is True

    def test_execute_simple_circuit(self):
        """Test execution of a simple circuit."""
        backend = AerBackend()

        # Create simple Bell state circuit
        circuit = QuantumCircuit(2)
        circuit.h(0)
        circuit.cx(0, 1)
        circuit.measure_all()

        result = backend.execute_circuit(circuit, shots=1000, seed=42)

        assert isinstance(result, ExecutionResult)
        assert result.shots == 1000
        assert result.backend_name == "aer_simulator"
        assert len(result.counts) > 0
        assert sum(result.counts.values()) == 1000

        # Bell state should produce ~50% |00⟩ and ~50% |11⟩
        assert "00" in result.counts
        assert "11" in result.counts

    def test_execute_without_measurements(self):
        """Test that circuit without measurements gets measured automatically."""
        backend = AerBackend()

        circuit = QuantumCircuit(2)
        circuit.h(0)
        circuit.cx(0, 1)
        # No explicit measurements

        result = backend.execute_circuit(circuit, shots=100)

        assert isinstance(result, ExecutionResult)
        assert len(result.counts) > 0

    def test_deterministic_with_seed(self):
        """Test that same seed produces same results."""
        backend = AerBackend()

        circuit = QuantumCircuit(2)
        circuit.h(0)
        circuit.cx(0, 1)
        circuit.measure_all()

        result1 = backend.execute_circuit(circuit, shots=1000, seed=42)
        result2 = backend.execute_circuit(circuit, shots=1000, seed=42)

        assert result1.counts == result2.counts

    def test_different_seeds_produce_different_results(self):
        """Test that different seeds produce different results."""
        backend = AerBackend()

        circuit = QuantumCircuit(2)
        circuit.h(0)
        circuit.cx(0, 1)
        circuit.measure_all()

        result1 = backend.execute_circuit(circuit, shots=1000, seed=42)
        result2 = backend.execute_circuit(circuit, shots=1000, seed=123)

        # Results should differ (statistically unlikely to be identical)
        assert result1.counts != result2.counts

    def test_metadata_contains_circuit_info(self):
        """Test that metadata contains circuit information."""
        backend = AerBackend()

        circuit = QuantumCircuit(3)
        circuit.h(0)
        circuit.cx(0, 1)
        circuit.cx(1, 2)
        circuit.measure_all()

        result = backend.execute_circuit(circuit, shots=100, seed=0)

        assert "num_qubits" in result.metadata
        assert result.metadata["num_qubits"] == 3
        assert "circuit_depth" in result.metadata
        assert "method" in result.metadata

    def test_get_info(self):
        """Test backend info retrieval."""
        backend = AerBackend(method="statevector")

        info = backend.get_info()

        assert info["name"] == "aer_simulator"
        assert info["provider"] == "qiskit_aer"
        assert info["type"] == "simulator"
        assert info["method"] == "statevector"
        assert info["available"] is True

    def test_single_qubit_circuit(self):
        """Test single qubit circuit execution."""
        backend = AerBackend()

        circuit = QuantumCircuit(1)
        circuit.x(0)
        circuit.measure_all()

        result = backend.execute_circuit(circuit, shots=100)

        # Should measure |1⟩ 100% of the time
        assert result.counts.get("1", 0) == 100

    def test_execution_time_recorded(self):
        """Test that execution time is recorded."""
        backend = AerBackend()

        circuit = QuantumCircuit(2)
        circuit.h(0)
        circuit.cx(0, 1)
        circuit.measure_all()

        result = backend.execute_circuit(circuit, shots=1000)

        assert result.execution_time_s > 0
        assert result.execution_time_s < 10  # Should be fast


class TestClassiqBackend:
    """Test Classiq backend adapter."""

    def test_is_available_checks_import(self):
        """Test that availability check looks for classiq import."""
        backend = ClassiqBackend()

        # Should return True or False depending on whether classiq is installed
        available = backend.is_available()
        assert isinstance(available, bool)

    def test_get_info(self):
        """Test backend info structure."""
        backend = ClassiqBackend(device_name="simulator")

        info = backend.get_info()

        assert info["name"] == "classiq_simulator"
        assert info["provider"] == "classiq"
        assert info["device"] == "simulator"
        assert "available" in info

    def test_execute_not_yet_implemented(self):
        """Test that execute raises NotImplementedError for now."""
        backend = ClassiqBackend()

        with pytest.raises(NotImplementedError, match="task #7"):
            backend.execute_circuit(None, shots=1000)


class TestQBraidBackend:
    """Test qBraid backend adapter."""

    def test_is_available_checks_import(self):
        """Test that availability check looks for qbraid import."""
        backend = QBraidBackend()

        available = backend.is_available()
        assert isinstance(available, bool)

    def test_get_info(self):
        """Test backend info structure."""
        backend = QBraidBackend(device_id="qbraid:qbraid:sim:qir-sv")

        info = backend.get_info()

        assert "qbraid" in info["name"]
        assert info["provider"] == "qbraid"
        assert info["device_id"] == "qbraid:qbraid:sim:qir-sv"
        assert "available" in info

    def test_execute_not_yet_implemented(self):
        """Test that execute raises NotImplementedError for now."""
        backend = QBraidBackend()

        with pytest.raises(NotImplementedError, match="task #8"):
            backend.execute_circuit(None, shots=1000)


class TestBackendManager:
    """Test backend manager and fallback logic."""

    def test_initialization(self):
        """Test manager initialization."""
        manager = BackendManager()

        assert manager.fallback_enabled is True
        assert "aer_fallback" in manager.backends

    def test_register_and_get_backend(self):
        """Test backend registration and retrieval."""
        manager = BackendManager()
        backend = AerBackend()

        manager.register_backend("test_backend", backend)

        retrieved = manager.get_backend("test_backend")
        assert retrieved is backend

    def test_get_nonexistent_backend(self):
        """Test getting non-existent backend returns None."""
        manager = BackendManager()

        backend = manager.get_backend("nonexistent")
        assert backend is None

    def test_execute_with_aer_backend(self):
        """Test execution with Aer backend (no fallback needed)."""
        manager = BackendManager()
        backend = AerBackend()
        manager.register_backend("aer_test", backend)

        circuit = QuantumCircuit(2)
        circuit.h(0)
        circuit.cx(0, 1)
        circuit.measure_all()

        result, fell_back = manager.execute_with_fallback(
            "aer_test", circuit, shots=100, seed=42
        )

        assert isinstance(result, ExecutionResult)
        assert fell_back is False
        assert result.backend_name == "aer_simulator"

    def test_fallback_on_unavailable_backend(self):
        """Test automatic fallback when backend not available."""
        manager = BackendManager(fallback_enabled=True)

        circuit = QuantumCircuit(2)
        circuit.h(0)
        circuit.cx(0, 1)
        circuit.measure_all()

        # Request non-existent backend
        result, fell_back = manager.execute_with_fallback(
            "nonexistent", circuit, shots=100, seed=42
        )

        assert isinstance(result, ExecutionResult)
        assert fell_back is True
        assert result.backend_name == "aer_simulator"

    def test_fallback_disabled_raises_error(self):
        """Test that disabled fallback raises error."""
        manager = BackendManager(fallback_enabled=False)

        circuit = QuantumCircuit(2)
        circuit.h(0)
        circuit.cx(0, 1)
        circuit.measure_all()

        with pytest.raises(BackendError, match="not found"):
            manager.execute_with_fallback("nonexistent", circuit, shots=100)

    def test_list_available_backends(self):
        """Test listing available backends."""
        manager = BackendManager()
        backend1 = AerBackend()
        backend2 = ClassiqBackend()

        manager.register_backend("aer1", backend1)
        manager.register_backend("classiq1", backend2)

        backends = manager.list_available_backends()

        assert len(backends) >= 2  # At least aer_fallback and our additions
        assert any(b["name"] == "aer_simulator" for b in backends)

    def test_global_backend_manager(self):
        """Test global backend manager singleton."""
        manager1 = get_backend_manager()
        manager2 = get_backend_manager()

        assert manager1 is manager2  # Same instance


class TestExecutionResult:
    """Test ExecutionResult dataclass."""

    def test_creation(self):
        """Test ExecutionResult creation."""
        result = ExecutionResult(
            counts={"00": 50, "11": 50},
            shots=100,
            backend_name="test_backend",
            execution_time_s=0.123,
            metadata={"key": "value"}
        )

        assert result.counts == {"00": 50, "11": 50}
        assert result.shots == 100
        assert result.backend_name == "test_backend"
        assert result.execution_time_s == 0.123
        assert result.metadata["key"] == "value"


class TestBackendError:
    """Test BackendError exception."""

    def test_creation_with_message(self):
        """Test error creation with message."""
        error = BackendError("test_backend", "Something went wrong")

        assert error.backend_name == "test_backend"
        assert "test_backend" in str(error)
        assert "Something went wrong" in str(error)

    def test_creation_with_original_error(self):
        """Test error creation with original exception."""
        original = ValueError("Original error")
        error = BackendError("test_backend", "Wrapped error", original)

        assert error.backend_name == "test_backend"
        assert error.original_error is original


class TestIntegration:
    """Integration tests for backend system."""

    def test_bell_state_measurement_distribution(self):
        """Test that Bell state produces expected measurement distribution."""
        backend = AerBackend()

        circuit = QuantumCircuit(2)
        circuit.h(0)
        circuit.cx(0, 1)
        circuit.measure_all()

        result = backend.execute_circuit(circuit, shots=10000, seed=42)

        # Should see roughly equal distribution of |00⟩ and |11⟩
        count_00 = result.counts.get("00", 0)
        count_11 = result.counts.get("11", 0)
        count_01 = result.counts.get("01", 0)
        count_10 = result.counts.get("10", 0)

        # |00⟩ and |11⟩ should be dominant
        assert count_00 > 4000
        assert count_11 > 4000

        # |01⟩ and |10⟩ should be rare (ideally 0, but allow small counts)
        assert count_01 < 100
        assert count_10 < 100

    def test_ghz_state_3_qubits(self):
        """Test 3-qubit GHZ state."""
        backend = AerBackend()

        circuit = QuantumCircuit(3)
        circuit.h(0)
        circuit.cx(0, 1)
        circuit.cx(0, 2)
        circuit.measure_all()

        result = backend.execute_circuit(circuit, shots=10000, seed=42)

        # Should see |000⟩ and |111⟩
        count_000 = result.counts.get("000", 0)
        count_111 = result.counts.get("111", 0)

        assert count_000 > 4000
        assert count_111 > 4000
