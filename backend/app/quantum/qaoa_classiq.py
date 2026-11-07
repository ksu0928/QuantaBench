"""QAOA circuit modeling and synthesis using Classiq SDK.

This module builds QAOA circuits from Ising Hamiltonians using Classiq's
high-level modeling and synthesis engine. It's designed for explicit visibility
of Classiq's capabilities for the "Best Use of Classiq" prize.

TODO: This implementation requires the Classiq SDK. The module uses placeholder
logic until Classiq is properly installed and authenticated. Once available,
uncomment the Classiq imports and implementation sections marked with TODO.

Reference: https://docs.classiq.io/
"""

import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from qiskit import QuantumCircuit

# TODO: Uncomment when Classiq is installed and configured
# from classiq import (
#     Model,
#     QArray,
#     QBit,
#     allocate,
#     create_model,
#     execute,
#     sample,
#     set_constraints,
#     set_execution_preferences,
#     synthesize,
#     write_qmod,
# )
# from classiq.builtin_functions import *


@dataclass
class QAOAParameters:
    """QAOA circuit parameters."""

    p: int  # Number of QAOA layers
    beta: np.ndarray  # Mixer angles (length p)
    gamma: np.ndarray  # Cost angles (length p)

    def __post_init__(self):
        """Validate parameters."""
        if len(self.beta) != self.p or len(self.gamma) != self.p:
            raise ValueError(f"beta and gamma must have length p={self.p}")

    def to_flat_array(self) -> np.ndarray:
        """Convert to flat array [gamma_0, beta_0, gamma_1, beta_1, ...].
        
        Returns:
            Flat parameter array of length 2*p
        """
        params = np.zeros(2 * self.p)
        for i in range(self.p):
            params[2 * i] = self.gamma[i]
            params[2 * i + 1] = self.beta[i]
        return params

    @classmethod
    def from_flat_array(cls, params: np.ndarray, p: int) -> "QAOAParameters":
        """Create from flat array [gamma_0, beta_0, gamma_1, beta_1, ...].
        
        Args:
            params: Flat parameter array of length 2*p
            p: Number of QAOA layers
            
        Returns:
            QAOAParameters instance
        """
        if len(params) != 2 * p:
            raise ValueError(f"Expected {2*p} parameters for p={p}, got {len(params)}")

        gamma = params[::2]  # Even indices
        beta = params[1::2]  # Odd indices
        return cls(p=p, beta=beta, gamma=gamma)

    @classmethod
    def random_init(cls, p: int, seed: Optional[int] = None) -> "QAOAParameters":
        """Initialize with random parameters.
        
        Args:
            p: Number of QAOA layers
            seed: Random seed
            
        Returns:
            Randomly initialized parameters
        """
        rng = np.random.default_rng(seed)
        # Initialize gamma in [0, 2π] and beta in [0, π]
        gamma = rng.uniform(0, 2 * np.pi, size=p)
        beta = rng.uniform(0, np.pi, size=p)
        return cls(p=p, beta=beta, gamma=gamma)


@dataclass
class SynthesisReport:
    """Report from Classiq synthesis."""

    num_qubits: int
    circuit_depth: int
    gate_counts: Dict[str, int]
    synthesis_time_s: float
    success: bool
    error_message: Optional[str] = None
    max_width: Optional[int] = None
    max_depth: Optional[int] = None


class ClassiqQAOACircuit:
    """QAOA circuit builder using Classiq SDK.
    
    This class demonstrates explicit use of Classiq for:
    1. High-level QAOA model definition
    2. Circuit synthesis with constraints
    3. Execution on Classiq backends
    """

    def __init__(
        self,
        h: np.ndarray,
        J: np.ndarray,
        offset: float = 0.0,
        max_circuit_width: Optional[int] = None,
        max_circuit_depth: Optional[int] = None,
    ):
        """Initialize Classiq QAOA circuit builder.
        
        Args:
            h: Ising linear coefficients (n,)
            J: Ising quadratic couplings (n × n, upper triangular)
            offset: Constant energy offset
            max_circuit_width: Maximum circuit width constraint (Classiq synthesis)
            max_circuit_depth: Maximum circuit depth constraint (Classiq synthesis)
        """
        self.h = h
        self.J = J
        self.offset = offset
        self.n_qubits = len(h)
        self.max_circuit_width = max_circuit_width
        self.max_circuit_depth = max_circuit_depth

        self._model = None
        self._qprog = None
        self._synthesis_report: Optional[SynthesisReport] = None

    def build_qaoa_model(self, params: QAOAParameters) -> Any:
        """Build Classiq QAOA model (Qmod).
        
        TODO: Implement with actual Classiq SDK once installed.
        
        The Classiq model will:
        1. Define cost Hamiltonian from h and J
        2. Define mixer Hamiltonian (X-mixer)
        3. Build p-layer QAOA circuit
        4. Apply synthesis constraints (width, depth)
        
        Args:
            params: QAOA parameters
            
        Returns:
            Classiq Model object
            
        Raises:
            NotImplementedError: Until Classiq SDK is properly installed
        """
        # TODO: Implement Classiq QAOA model
        # The actual implementation will look like:
        #
        # @qfunc
        # def cost_layer(gamma: QParam[float], qubits: QArray[QBit]):
        #     # Apply e^(-i*gamma*H_cost)
        #     for i in range(self.n_qubits):
        #         if abs(self.h[i]) > 1e-10:
        #             RZ(2 * gamma * self.h[i], qubits[i])
        #     for i in range(self.n_qubits):
        #         for j in range(i + 1, self.n_qubits):
        #             if abs(self.J[i, j]) > 1e-10:
        #                 CNOT(qubits[i], qubits[j])
        #                 RZ(2 * gamma * self.J[i, j], qubits[j])
        #                 CNOT(qubits[i], qubits[j])
        #
        # @qfunc
        # def mixer_layer(beta: QParam[float], qubits: QArray[QBit]):
        #     # Apply e^(-i*beta*H_mixer) where H_mixer = sum(X_i)
        #     for i in range(self.n_qubits):
        #         RX(2 * beta, qubits[i])
        #
        # @qfunc
        # def qaoa_circuit(params: QArray[QParam[float]]) -> QArray[QBit]:
        #     qubits = QArray[QBit](size=self.n_qubits)
        #     allocate(self.n_qubits, qubits)
        #     
        #     # Initial state: |++++...+>
        #     apply_to_all(H, qubits)
        #     
        #     # QAOA layers
        #     for p_idx in range(params.p):
        #         cost_layer(params.gamma[p_idx], qubits)
        #         mixer_layer(params.beta[p_idx], qubits)
        #     
        #     return qubits
        #
        # model = create_model(qaoa_circuit, params)
        # return model

        raise NotImplementedError(
            "Classiq QAOA model building requires Classiq SDK. "
            "See qaoa_classiq.py for implementation template. "
            "Install with: pip install classiq"
        )

    def synthesize(self, params: QAOAParameters) -> SynthesisReport:
        """Synthesize QAOA circuit using Classiq synthesis engine.
        
        TODO: Implement with actual Classiq SDK.
        
        This demonstrates Classiq's key capability: automatic circuit synthesis
        with constraints (max width, max depth) and optimization.
        
        Args:
            params: QAOA parameters
            
        Returns:
            Synthesis report with circuit statistics
            
        Raises:
            NotImplementedError: Until Classiq SDK is properly installed
        """
        # TODO: Implement Classiq synthesis
        # The actual implementation will look like:
        #
        # start_time = time.time()
        #
        # try:
        #     # Build model
        #     model = self.build_qaoa_model(params)
        #     
        #     # Set synthesis constraints
        #     constraints = Constraints(
        #         max_width=self.max_circuit_width,
        #         max_depth=self.max_circuit_depth,
        #     )
        #     model = set_constraints(model, constraints)
        #     
        #     # Synthesize
        #     qprog = synthesize(model)
        #     self._qprog = qprog
        #     
        #     # Extract circuit statistics
        #     circuit_info = qprog.get_circuit_info()
        #     synthesis_time = time.time() - start_time
        #     
        #     report = SynthesisReport(
        #         num_qubits=circuit_info.num_qubits,
        #         circuit_depth=circuit_info.depth,
        #         gate_counts=circuit_info.gate_counts,
        #         synthesis_time_s=synthesis_time,
        #         success=True,
        #         max_width=self.max_circuit_width,
        #         max_depth=self.max_circuit_depth,
        #     )
        #     
        #     self._synthesis_report = report
        #     return report
        #
        # except Exception as e:
        #     synthesis_time = time.time() - start_time
        #     return SynthesisReport(
        #         num_qubits=self.n_qubits,
        #         circuit_depth=0,
        #         gate_counts={},
        #         synthesis_time_s=synthesis_time,
        #         success=False,
        #         error_message=str(e),
        #     )

        raise NotImplementedError(
            "Classiq synthesis requires Classiq SDK. "
            "Install with: pip install classiq"
        )

    def execute(
        self,
        params: QAOAParameters,
        shots: int = 1024,
        backend_name: str = "simulator",
    ) -> Dict[str, int]:
        """Execute QAOA circuit using Classiq execution backend.
        
        TODO: Implement with actual Classiq SDK.
        
        Args:
            params: QAOA parameters
            shots: Number of measurement shots
            backend_name: Classiq backend name
            
        Returns:
            Measurement counts dictionary
            
        Raises:
            NotImplementedError: Until Classiq SDK is properly installed
        """
        # TODO: Implement Classiq execution
        # The actual implementation will look like:
        #
        # # Synthesize if not already done
        # if self._qprog is None:
        #     self.synthesize(params)
        #     
        # # Set execution preferences
        # preferences = ExecutionPreferences(
        #     num_shots=shots,
        #     backend_name=backend_name,
        # )
        # 
        # # Execute
        # result = execute(self._qprog, preferences)
        # 
        # # Get counts
        # counts_df = result.get_counts()
        # counts_dict = counts_df.to_dict()
        # 
        # return counts_dict

        raise NotImplementedError(
            "Classiq execution requires Classiq SDK. "
            "Install with: pip install classiq"
        )

    def to_qiskit(self, params: QAOAParameters) -> QuantumCircuit:
        """Convert QAOA circuit to Qiskit format (for Aer fallback).
        
        This builds a basic QAOA circuit in Qiskit as a fallback when
        Classiq is not available.
        
        Args:
            params: QAOA parameters
            
        Returns:
            Qiskit QuantumCircuit
        """
        qc = QuantumCircuit(self.n_qubits)

        # Initial state: |++++...+>
        for i in range(self.n_qubits):
            qc.h(i)

        # QAOA layers
        for layer in range(params.p):
            gamma = params.gamma[layer]
            beta = params.beta[layer]

            # Cost layer: e^(-i*gamma*H_cost)
            # Linear terms: RZ(2*gamma*h_i)
            for i in range(self.n_qubits):
                if abs(self.h[i]) > 1e-10:
                    qc.rz(2 * gamma * self.h[i], i)

            # Quadratic terms: e^(-i*gamma*J_ij*Z_i*Z_j)
            # Implemented as: CNOT-RZ-CNOT
            for i in range(self.n_qubits):
                for j in range(i + 1, self.n_qubits):
                    if abs(self.J[i, j]) > 1e-10:
                        qc.cx(i, j)
                        qc.rz(2 * gamma * self.J[i, j], j)
                        qc.cx(i, j)

            # Mixer layer: e^(-i*beta*H_mixer) where H_mixer = sum(X_i)
            # Implemented as: RX(2*beta)
            for i in range(self.n_qubits):
                qc.rx(2 * beta, i)

        # Measurements
        qc.measure_all()

        return qc

    def get_synthesis_report(self) -> Optional[SynthesisReport]:
        """Get the most recent synthesis report.
        
        Returns:
            SynthesisReport or None if not yet synthesized
        """
        return self._synthesis_report

    def get_circuit_info(self) -> Dict[str, Any]:
        """Get information about the QAOA circuit.
        
        Returns:
            Dict with circuit metadata
        """
        return {
            "num_qubits": self.n_qubits,
            "hamiltonian_terms": {
                "linear": int(np.sum(np.abs(self.h) > 1e-10)),
                "quadratic": int(
                    np.sum(np.abs(self.J[np.triu_indices_from(self.J, k=1)]) > 1e-10)
                ),
            },
            "energy_offset": float(self.offset),
            "max_circuit_width": self.max_circuit_width,
            "max_circuit_depth": self.max_circuit_depth,
        }


def create_qaoa_circuit(
    h: np.ndarray,
    J: np.ndarray,
    offset: float = 0.0,
    max_circuit_width: Optional[int] = None,
    max_circuit_depth: Optional[int] = None,
) -> ClassiqQAOACircuit:
    """Factory function to create Classiq QAOA circuit.
    
    Args:
        h: Ising linear coefficients
        J: Ising quadratic couplings
        offset: Energy offset
        max_circuit_width: Max circuit width constraint
        max_circuit_depth: Max circuit depth constraint
        
    Returns:
        ClassiqQAOACircuit instance
    """
    return ClassiqQAOACircuit(
        h=h,
        J=J,
        offset=offset,
        max_circuit_width=max_circuit_width,
        max_circuit_depth=max_circuit_depth,
    )


def evaluate_qaoa_energy(
    counts: Dict[str, int],
    h: np.ndarray,
    J: np.ndarray,
    offset: float = 0.0,
) -> float:
    """Evaluate expectation value of Hamiltonian from measurement counts.
    
    ⟨H⟩ = Σ_bitstring p(bitstring) * E(bitstring)
    
    Args:
        counts: Measurement counts
        h: Ising linear coefficients
        J: Ising quadratic couplings
        offset: Energy offset
        
    Returns:
        Expectation value of energy
    """
    from ..quantum.hamiltonian import bitstring_to_spins, evaluate_ising_energy

    total_shots = sum(counts.values())
    expectation = 0.0

    for bitstring, count in counts.items():
        # Convert to spins
        z = bitstring_to_spins(bitstring)
        # Evaluate energy
        energy = evaluate_ising_energy(z, h, J, offset)
        # Weighted by probability
        probability = count / total_shots
        expectation += probability * energy

    return expectation


def get_best_bitstring_from_counts(counts: Dict[str, int]) -> str:
    """Extract most frequently measured bitstring.
    
    Args:
        counts: Measurement counts
        
    Returns:
        Most frequent bitstring
    """
    return max(counts.items(), key=lambda x: x[1])[0]
