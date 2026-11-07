"""QUBO to Ising Hamiltonian conversion.

QUBO formulation: minimize x^T Q x + offset, where x ∈ {0, 1}^n
Ising formulation: minimize Σ_i h_i z_i + Σ_{i<j} J_{ij} z_i z_j + offset', where z ∈ {-1, +1}^n

Conversion: x_i = (1 - z_i) / 2  (so x=0 → z=+1, x=1 → z=-1)
"""

from typing import Dict, Tuple

import numpy as np


def qubo_to_ising(
    Q: np.ndarray, qubo_offset: float = 0.0
) -> Tuple[np.ndarray, np.ndarray, float]:
    """Convert QUBO matrix to Ising Hamiltonian coefficients.
    
    QUBO: minimize x^T Q x + qubo_offset, x ∈ {0,1}^n
    Ising: minimize Σ_i h_i z_i + Σ_{i<j} J_{ij} z_i z_j + ising_offset, z ∈ {-1,+1}^n
    
    Substitution: x_i = (1 - z_i) / 2
    
    Derivation:
    x^T Q x = Σ_{i,j} Q_{ij} x_i x_j
            = Σ_{i,j} Q_{ij} (1 - z_i)/2 * (1 - z_j)/2
            = (1/4) Σ_{i,j} Q_{ij} (1 - z_i - z_j + z_i z_j)
            = (1/4) Σ_{i,j} Q_{ij} - (1/4) Σ_{i,j} Q_{ij} z_i - (1/4) Σ_{i,j} Q_{ij} z_j 
                + (1/4) Σ_{i,j} Q_{ij} z_i z_j
    
    Collecting terms:
    - Constant: (1/4) Σ_{i,j} Q_{ij}
    - Linear (h_i): -(1/2) Σ_j Q_{ij}  [combining i and j terms]
    - Quadratic (J_{ij}): (1/4) Q_{ij} for i < j  [using Q_{ij} + Q_{ji} for off-diagonal]
    
    Args:
        Q: QUBO matrix (n × n), can be asymmetric
        qubo_offset: Constant offset in QUBO formulation
        
    Returns:
        Tuple of (h, J, ising_offset) where:
            - h: Linear coefficients (n,)
            - J: Quadratic coupling matrix (n × n), upper triangular
            - ising_offset: Constant offset in Ising formulation
    """
    n = Q.shape[0]
    
    # Linear coefficients: h_i = -(1/2) * Σ_j Q_{ij}
    # This accounts for both Q_{ij} and Q_{ji} terms
    h = -0.5 * np.sum(Q, axis=1)
    
    # Quadratic couplings: J_{ij} = (1/4) * (Q_{ij} + Q_{ji}) for i < j
    # Store as upper triangular matrix
    J = np.zeros((n, n))
    for i in range(n):
        for j in range(i + 1, n):
            J[i, j] = 0.25 * (Q[i, j] + Q[j, i])
    
    # Constant offset: (1/4) * Σ_{i,j} Q_{ij} + qubo_offset
    ising_offset = 0.25 * np.sum(Q) + qubo_offset
    
    return h, J, ising_offset


def ising_to_qubo(
    h: np.ndarray, J: np.ndarray, ising_offset: float = 0.0
) -> Tuple[np.ndarray, float]:
    """Convert Ising Hamiltonian to QUBO matrix (inverse operation).
    
    Ising: minimize Σ_i h_i z_i + Σ_{i<j} J_{ij} z_i z_j + ising_offset
    QUBO: minimize x^T Q x + qubo_offset
    
    Substitution: z_i = 1 - 2*x_i
    
    Args:
        h: Linear coefficients (n,)
        J: Quadratic coupling matrix (n × n)
        ising_offset: Constant offset in Ising formulation
        
    Returns:
        Tuple of (Q, qubo_offset)
    """
    n = len(h)
    Q = np.zeros((n, n))
    
    # Expand (1 - 2x_i)(1 - 2x_j) = 1 - 2x_i - 2x_j + 4x_i x_j
    for i in range(n):
        # Diagonal from linear terms: h_i * (1 - 2x_i)
        Q[i, i] += -2 * h[i]
        
        for j in range(i + 1, n):
            # Quadratic terms: J_{ij} * (1 - 2x_i - 2x_j + 4x_i x_j)
            if J[i, j] != 0:
                Q[i, j] += 4 * J[i, j]  # x_i x_j coefficient
                Q[j, i] += 4 * J[i, j]  # Symmetric
                Q[i, i] += -2 * J[i, j]  # -2x_i term
                Q[j, j] += -2 * J[i, j]  # -2x_j term
    
    # Constant: Σ h_i + Σ_{i<j} J_{ij} + ising_offset
    qubo_offset = np.sum(h) + np.sum(J[np.triu_indices_from(J, k=1)]) + ising_offset
    
    return Q, qubo_offset


def evaluate_ising_energy(
    z: np.ndarray, h: np.ndarray, J: np.ndarray, offset: float = 0.0
) -> float:
    """Evaluate Ising Hamiltonian energy for a spin configuration.
    
    Energy: Σ_i h_i z_i + Σ_{i<j} J_{ij} z_i z_j + offset
    
    Args:
        z: Spin configuration (n,), values in {-1, +1}
        h: Linear coefficients (n,)
        J: Quadratic coupling matrix (n × n)
        offset: Constant offset
        
    Returns:
        Energy value
    """
    linear_term = np.dot(h, z)
    
    # Only upper triangular to avoid double counting
    quadratic_term = 0.0
    n = len(z)
    for i in range(n):
        for j in range(i + 1, n):
            quadratic_term += J[i, j] * z[i] * z[j]
    
    return float(linear_term + quadratic_term + offset)


def bitstring_to_spins(bitstring: str) -> np.ndarray:
    """Convert binary bitstring to spin configuration.
    
    Convention: x=0 → z=+1, x=1 → z=-1
    
    Args:
        bitstring: Binary string (e.g., "10011")
        
    Returns:
        Spin array with values {-1, +1}
    """
    x = np.array([int(b) for b in bitstring])
    return 1 - 2 * x


def spins_to_bitstring(z: np.ndarray) -> str:
    """Convert spin configuration to binary bitstring.
    
    Convention: z=+1 → x=0, z=-1 → x=1
    
    Args:
        z: Spin array with values {-1, +1}
        
    Returns:
        Binary string
    """
    x = ((1 - z) / 2).astype(int)
    return "".join(str(b) for b in x)


def verify_qubo_ising_equivalence(
    Q: np.ndarray, 
    qubo_offset: float,
    h: np.ndarray,
    J: np.ndarray,
    ising_offset: float,
    test_all_bitstrings: bool = True,
    tolerance: float = 1e-9,
) -> Dict[str, any]:
    """Verify that QUBO and Ising formulations produce identical energies.
    
    Args:
        Q: QUBO matrix
        qubo_offset: QUBO constant offset
        h: Ising linear coefficients
        J: Ising quadratic couplings
        ising_offset: Ising constant offset
        test_all_bitstrings: If True, test all 2^n configurations (only for n <= 20)
        tolerance: Numerical tolerance for comparison
        
    Returns:
        Dict with verification results
    """
    n = Q.shape[0]
    
    if test_all_bitstrings and n > 20:
        raise ValueError(
            f"Cannot test all bitstrings for n={n} (2^{n} configurations). "
            "Set test_all_bitstrings=False or use n <= 20."
        )
    
    num_tested = 0
    num_passed = 0
    max_error = 0.0
    failed_examples = []
    
    # Test configurations
    if test_all_bitstrings:
        # Test all 2^n bitstrings
        test_range = range(2**n)
    else:
        # Test a sample of random bitstrings
        rng = np.random.default_rng(42)
        test_range = rng.integers(0, 2**n, size=min(1000, 2**n))
    
    for i in test_range:
        bitstring = format(i, f"0{n}b")
        
        # QUBO energy
        x = np.array([int(b) for b in bitstring])
        qubo_energy = float(x @ Q @ x) + qubo_offset
        
        # Ising energy
        z = bitstring_to_spins(bitstring)
        ising_energy = evaluate_ising_energy(z, h, J, ising_offset)
        
        # Compare
        error = abs(qubo_energy - ising_energy)
        max_error = max(max_error, error)
        num_tested += 1
        
        if error <= tolerance:
            num_passed += 1
        else:
            if len(failed_examples) < 5:  # Keep first few failures
                failed_examples.append({
                    "bitstring": bitstring,
                    "qubo_energy": qubo_energy,
                    "ising_energy": ising_energy,
                    "error": error,
                })
    
    success = num_passed == num_tested
    
    return {
        "success": success,
        "num_tested": num_tested,
        "num_passed": num_passed,
        "max_error": max_error,
        "tolerance": tolerance,
        "failed_examples": failed_examples,
    }


def get_ising_hamiltonian_dict(
    h: np.ndarray, J: np.ndarray, offset: float
) -> Dict[str, any]:
    """Convert Ising coefficients to dictionary format for easier inspection.
    
    Args:
        h: Linear coefficients (n,)
        J: Quadratic coupling matrix (n × n)
        offset: Constant offset
        
    Returns:
        Dict with linear, quadratic, and offset terms
    """
    n = len(h)
    
    linear = {i: float(h[i]) for i in range(n) if abs(h[i]) > 1e-10}
    
    quadratic = {}
    for i in range(n):
        for j in range(i + 1, n):
            if abs(J[i, j]) > 1e-10:
                quadratic[(i, j)] = float(J[i, j])
    
    return {
        "linear": linear,
        "quadratic": quadratic,
        "offset": float(offset),
        "num_qubits": n,
    }
