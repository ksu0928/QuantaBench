"""Unit tests for QUBO to Ising Hamiltonian conversion."""

import numpy as np
import pytest

from app.quantum.hamiltonian import (
    bitstring_to_spins,
    evaluate_ising_energy,
    get_ising_hamiltonian_dict,
    ising_to_qubo,
    qubo_to_ising,
    spins_to_bitstring,
    verify_qubo_ising_equivalence,
)


class TestBitstringSpinConversion:
    """Test conversions between bitstrings and spin configurations."""

    def test_bitstring_to_spins(self):
        """Test binary to spin conversion."""
        # x=0 → z=+1, x=1 → z=-1
        assert np.array_equal(bitstring_to_spins("000"), np.array([1, 1, 1]))
        assert np.array_equal(bitstring_to_spins("111"), np.array([-1, -1, -1]))
        assert np.array_equal(bitstring_to_spins("101"), np.array([-1, 1, -1]))
        assert np.array_equal(bitstring_to_spins("010"), np.array([1, -1, 1]))

    def test_spins_to_bitstring(self):
        """Test spin to binary conversion."""
        # z=+1 → x=0, z=-1 → x=1
        assert spins_to_bitstring(np.array([1, 1, 1])) == "000"
        assert spins_to_bitstring(np.array([-1, -1, -1])) == "111"
        assert spins_to_bitstring(np.array([-1, 1, -1])) == "101"
        assert spins_to_bitstring(np.array([1, -1, 1])) == "010"

    def test_roundtrip_conversion(self):
        """Test roundtrip bitstring → spins → bitstring."""
        test_cases = ["000", "111", "101010", "11001100"]
        for bitstring in test_cases:
            spins = bitstring_to_spins(bitstring)
            recovered = spins_to_bitstring(spins)
            assert recovered == bitstring


class TestQUBOtoIsing:
    """Test QUBO to Ising Hamiltonian conversion."""

    def test_simple_2qubit_symmetric(self):
        """Test conversion with a simple 2-qubit symmetric QUBO."""
        # QUBO: x0^2 - x1^2 + 2*x0*x1
        Q = np.array([[1.0, 1.0], [1.0, -1.0]])
        h, J, offset = qubo_to_ising(Q, qubo_offset=0.0)

        # Verify conversion
        result = verify_qubo_ising_equivalence(
            Q, 0.0, h, J, offset, test_all_bitstrings=True
        )
        assert result["success"], f"Failed: {result}"
        assert result["max_error"] < 1e-9

    def test_simple_2qubit_asymmetric(self):
        """Test conversion with asymmetric QUBO."""
        # Asymmetric off-diagonal
        Q = np.array([[2.0, 3.0], [1.0, -2.0]])
        h, J, offset = qubo_to_ising(Q, qubo_offset=5.0)

        result = verify_qubo_ising_equivalence(
            Q, 5.0, h, J, offset, test_all_bitstrings=True
        )
        assert result["success"], f"Failed: {result}"

    def test_3qubit_all_interactions(self):
        """Test 3-qubit system with all pairwise interactions."""
        Q = np.array([
            [1.0, 0.5, 0.3],
            [0.5, -1.0, 0.7],
            [0.3, 0.7, 0.5],
        ])
        h, J, offset = qubo_to_ising(Q, qubo_offset=-2.0)

        result = verify_qubo_ising_equivalence(
            Q, -2.0, h, J, offset, test_all_bitstrings=True
        )
        assert result["success"], f"Failed: {result}"

    def test_diagonal_only_qubo(self):
        """Test QUBO with only diagonal terms (no interactions)."""
        Q = np.diag([1.0, -2.0, 3.0, -0.5])
        h, J, offset = qubo_to_ising(Q)

        # J should be all zeros
        assert np.allclose(J, 0.0)

        result = verify_qubo_ising_equivalence(
            Q, 0.0, h, J, offset, test_all_bitstrings=True
        )
        assert result["success"]

    def test_offdiagonal_only_qubo(self):
        """Test QUBO with only off-diagonal interactions."""
        Q = np.array([
            [0.0, 1.0, 0.5],
            [1.0, 0.0, 0.3],
            [0.5, 0.3, 0.0],
        ])
        h, J, offset = qubo_to_ising(Q)

        result = verify_qubo_ising_equivalence(
            Q, 0.0, h, J, offset, test_all_bitstrings=True
        )
        assert result["success"]

    def test_larger_problem_n6(self):
        """Test conversion for n=6 problem (portfolio size)."""
        np.random.seed(42)
        n = 6
        Q = np.random.randn(n, n)
        Q = (Q + Q.T) / 2  # Make symmetric
        qubo_offset = np.random.randn()

        h, J, offset = qubo_to_ising(Q, qubo_offset)

        result = verify_qubo_ising_equivalence(
            Q, qubo_offset, h, J, offset, test_all_bitstrings=True
        )
        assert result["success"], f"n=6 test failed: {result}"
        assert result["max_error"] < 1e-9

    def test_roundtrip_qubo_ising_qubo(self):
        """Test roundtrip: QUBO → Ising → QUBO."""
        Q_original = np.array([
            [2.0, -1.0, 0.5],
            [-1.0, 3.0, -0.3],
            [0.5, -0.3, -1.0],
        ])
        qubo_offset_original = 5.0

        # Forward conversion
        h, J, ising_offset = qubo_to_ising(Q_original, qubo_offset_original)

        # Reverse conversion
        Q_recovered, qubo_offset_recovered = ising_to_qubo(h, J, ising_offset)

        # Verify energies match for all bitstrings
        for i in range(2**3):
            bitstring = format(i, "03b")
            x = np.array([int(b) for b in bitstring])

            energy_original = float(x @ Q_original @ x) + qubo_offset_original
            energy_recovered = float(x @ Q_recovered @ x) + qubo_offset_recovered

            assert np.isclose(energy_original, energy_recovered, atol=1e-9)


class TestIsingEnergy:
    """Test Ising energy evaluation."""

    def test_ising_energy_no_interactions(self):
        """Test energy with only linear terms."""
        h = np.array([1.0, -2.0, 0.5])
        J = np.zeros((3, 3))
        offset = 0.0

        # All spins +1: energy = sum(h)
        z = np.array([1, 1, 1])
        energy = evaluate_ising_energy(z, h, J, offset)
        assert np.isclose(energy, np.sum(h))

        # All spins -1: energy = -sum(h)
        z = np.array([-1, -1, -1])
        energy = evaluate_ising_energy(z, h, J, offset)
        assert np.isclose(energy, -np.sum(h))

    def test_ising_energy_with_interactions(self):
        """Test energy with quadratic terms."""
        h = np.array([0.0, 0.0])
        J = np.array([[0.0, 1.0], [0.0, 0.0]])  # Only J[0,1] = 1.0
        offset = 0.0

        # z = [+1, +1]: energy = 1.0
        energy = evaluate_ising_energy(np.array([1, 1]), h, J, offset)
        assert np.isclose(energy, 1.0)

        # z = [+1, -1]: energy = -1.0
        energy = evaluate_ising_energy(np.array([1, -1]), h, J, offset)
        assert np.isclose(energy, -1.0)

        # z = [-1, +1]: energy = -1.0
        energy = evaluate_ising_energy(np.array([-1, 1]), h, J, offset)
        assert np.isclose(energy, -1.0)

        # z = [-1, -1]: energy = 1.0
        energy = evaluate_ising_energy(np.array([-1, -1]), h, J, offset)
        assert np.isclose(energy, 1.0)


class TestPortfolioQUBO:
    """Test QUBO to Ising conversion on realistic portfolio problem."""

    def test_portfolio_n4_k2(self):
        """Test small portfolio problem: 4 assets, select 2."""
        # Simplified portfolio QUBO
        # Risk component (covariance-like)
        cov = np.array([
            [0.04, 0.01, 0.02, 0.01],
            [0.01, 0.03, 0.01, 0.02],
            [0.02, 0.01, 0.05, 0.01],
            [0.01, 0.02, 0.01, 0.04],
        ])

        # Returns
        mu = np.array([0.10, 0.08, 0.12, 0.09])

        # Parameters
        q = 0.5  # risk factor
        K = 2    # target size
        lam = 5.0  # penalty

        # Build QUBO: q*Cov - mu + lambda*(1-2K) on diagonal, lambda off-diagonal
        n = 4
        Q = q * cov
        for i in range(n):
            Q[i, i] += -mu[i] + lam * (1 - 2 * K)
            for j in range(i + 1, n):
                Q[i, j] += lam
                Q[j, i] += lam

        qubo_offset = lam * K**2

        # Convert to Ising
        h, J, ising_offset = qubo_to_ising(Q, qubo_offset)

        # Verify all 16 bitstrings have matching energies
        result = verify_qubo_ising_equivalence(
            Q, qubo_offset, h, J, ising_offset, test_all_bitstrings=True
        )
        assert result["success"], f"Portfolio test failed: {result}"


class TestHamiltonianDict:
    """Test dictionary representation of Ising Hamiltonian."""

    def test_hamiltonian_dict_format(self):
        """Test conversion to dict format."""
        h = np.array([1.0, -2.0, 0.0, 0.5])
        J = np.array([
            [0.0, 0.3, 0.0, 0.0],
            [0.0, 0.0, -0.5, 0.0],
            [0.0, 0.0, 0.0, 0.2],
            [0.0, 0.0, 0.0, 0.0],
        ])
        offset = 3.14

        ham_dict = get_ising_hamiltonian_dict(h, J, offset)

        assert ham_dict["num_qubits"] == 4
        assert ham_dict["offset"] == 3.14

        # Check linear terms (should exclude near-zero)
        assert 0 in ham_dict["linear"]
        assert 1 in ham_dict["linear"]
        assert 2 not in ham_dict["linear"]  # h[2] = 0
        assert 3 in ham_dict["linear"]

        # Check quadratic terms
        assert (0, 1) in ham_dict["quadratic"]
        assert (1, 2) in ham_dict["quadratic"]
        assert (2, 3) in ham_dict["quadratic"]
        assert (0, 2) not in ham_dict["quadratic"]  # J[0,2] = 0


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_single_qubit(self):
        """Test with single qubit."""
        Q = np.array([[2.0]])
        h, J, offset = qubo_to_ising(Q)

        assert len(h) == 1
        assert J.shape == (1, 1)

        result = verify_qubo_ising_equivalence(
            Q, 0.0, h, J, offset, test_all_bitstrings=True
        )
        assert result["success"]

    def test_zero_matrix(self):
        """Test with all-zero QUBO."""
        Q = np.zeros((3, 3))
        h, J, offset = qubo_to_ising(Q)

        assert np.allclose(h, 0.0)
        assert np.allclose(J, 0.0)
        assert np.isclose(offset, 0.0)

    def test_large_problem_sampling(self):
        """Test that sampling works for large n."""
        n = 15
        np.random.seed(123)
        Q = np.random.randn(n, n)
        Q = (Q + Q.T) / 2

        h, J, offset = qubo_to_ising(Q)

        # Should not raise error with sampling
        result = verify_qubo_ising_equivalence(
            Q, 0.0, h, J, offset, test_all_bitstrings=False
        )
        assert result["num_tested"] == 1000  # Default sample size
        assert result["success"]

    def test_verification_raises_for_too_large_n(self):
        """Test that verification raises error for n > 20 with test_all."""
        n = 21
        Q = np.eye(n)
        h, J, offset = qubo_to_ising(Q)

        with pytest.raises(ValueError, match="Cannot test all bitstrings"):
            verify_qubo_ising_equivalence(
                Q, 0.0, h, J, offset, test_all_bitstrings=True
            )
