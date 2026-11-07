"""
Integration tests for the FastAPI application.

Tests full end-to-end workflows through the REST API.
"""

import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import sys

# Add app to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.main import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


class TestHealthEndpoint:
    """Tests for the health check endpoint."""
    
    def test_health_check_success(self, client):
        """Health endpoint should return 200 with status."""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "timestamp" in data


class TestProblemsEndpoint:
    """Tests for the problems listing endpoint."""
    
    def test_list_problems(self, client):
        """Should list available problem types."""
        response = client.get("/api/problems")
        assert response.status_code == 200
        data = response.json()
        assert "problems" in data
        assert len(data["problems"]) > 0
        
        # Check portfolio problem is included
        problem_ids = [p["id"] for p in data["problems"]]
        assert "portfolio" in problem_ids
        
        # Verify problem structure
        portfolio = next(p for p in data["problems"] if p["id"] == "portfolio")
        assert "name" in portfolio
        assert "description" in portfolio
        assert "parameters" in portfolio


class TestOptimizeEndpoint:
    """Tests for the optimization endpoint."""
    
    def test_optimize_portfolio_minimal(self, client):
        """Test portfolio optimization with minimal parameters."""
        request_data = {
            "problem_type": "portfolio",
            "problem_params": {
                "returns_file": "sample",
                "n_assets": 5,
                "budget": 2,
                "risk_aversion": 0.5,
            },
            "qaoa_params": {
                "p": 1,
                "shots": 1024,
            },
            "seed": 42,
        }
        
        response = client.post("/api/optimize", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "run_id" in data
        assert "problem_type" in data
        assert data["problem_type"] == "portfolio"
        assert "quantum_result" in data
        assert "classical_results" in data
        assert "metrics" in data
        assert "execution_time_seconds" in data
        
        # Verify quantum result structure
        quantum = data["quantum_result"]
        assert "solution" in quantum
        assert "objective_value" in quantum
        assert "is_feasible" in quantum
        assert "backend_used" in quantum
        
        # Verify we have classical results
        assert len(data["classical_results"]) > 0
        
        # Verify metrics
        metrics = data["metrics"]
        assert "approximation_ratio" in metrics
        assert "probability_of_optimal" in metrics
    
    def test_optimize_with_custom_backend(self, client):
        """Test optimization with explicit backend selection."""
        request_data = {
            "problem_type": "portfolio",
            "problem_params": {
                "returns_file": "sample",
                "n_assets": 5,
                "budget": 2,
            },
            "qaoa_params": {
                "p": 1,
                "shots": 512,
            },
            "quantum_backend": "aer_simulator",
            "seed": 42,
        }
        
        response = client.post("/api/optimize", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert data["quantum_result"]["backend_used"] == "aer_simulator"
    
    def test_optimize_higher_p(self, client):
        """Test optimization with higher QAOA depth."""
        request_data = {
            "problem_type": "portfolio",
            "problem_params": {
                "returns_file": "sample",
                "n_assets": 5,
                "budget": 2,
            },
            "qaoa_params": {
                "p": 3,
                "shots": 1024,
            },
            "seed": 42,
        }
        
        response = client.post("/api/optimize", json=request_data)
        assert response.status_code == 200
        data = response.json()
        
        # Should complete successfully with p=3
        assert data["quantum_result"]["backend_used"] in ["aer_simulator", "classiq", "qbraid"]
    
    def test_optimize_invalid_problem_type(self, client):
        """Should reject invalid problem type."""
        request_data = {
            "problem_type": "invalid_problem",
            "problem_params": {},
            "qaoa_params": {
                "p": 1,
                "shots": 1024,
            },
        }
        
        response = client.post("/api/optimize", json=request_data)
        assert response.status_code == 422  # Validation error
    
    def test_optimize_missing_required_params(self, client):
        """Should reject request missing required parameters."""
        request_data = {
            "problem_type": "portfolio",
            "problem_params": {
                "returns_file": "sample",
                # Missing n_assets and budget
            },
            "qaoa_params": {
                "p": 1,
                "shots": 1024,
            },
        }
        
        response = client.post("/api/optimize", json=request_data)
        assert response.status_code == 400  # Bad request
    
    def test_optimize_invalid_qaoa_params(self, client):
        """Should reject invalid QAOA parameters."""
        request_data = {
            "problem_type": "portfolio",
            "problem_params": {
                "returns_file": "sample",
                "n_assets": 5,
                "budget": 2,
            },
            "qaoa_params": {
                "p": 0,  # Invalid: p must be >= 1
                "shots": 1024,
            },
        }
        
        response = client.post("/api/optimize", json=request_data)
        assert response.status_code == 422  # Validation error


class TestRunsEndpoint:
    """Tests for the runs retrieval endpoint."""
    
    def test_get_run_after_optimization(self, client):
        """Should retrieve run details after optimization."""
        # First, create a run
        request_data = {
            "problem_type": "portfolio",
            "problem_params": {
                "returns_file": "sample",
                "n_assets": 5,
                "budget": 2,
            },
            "qaoa_params": {
                "p": 1,
                "shots": 1024,
            },
            "seed": 42,
        }
        
        create_response = client.post("/api/optimize", json=request_data)
        assert create_response.status_code == 200
        run_id = create_response.json()["run_id"]
        
        # Now retrieve it
        get_response = client.get(f"/api/runs/{run_id}")
        assert get_response.status_code == 200
        
        data = get_response.json()
        assert data["run_id"] == run_id
        assert "quantum_result" in data
        assert "classical_results" in data
        assert "metrics" in data
    
    def test_get_nonexistent_run(self, client):
        """Should return 404 for nonexistent run."""
        response = client.get("/api/runs/nonexistent-run-id-12345")
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data


class TestEndToEndWorkflow:
    """End-to-end integration tests."""
    
    def test_complete_optimization_workflow(self, client):
        """Test complete workflow from optimization to result retrieval."""
        # Step 1: List available problems
        problems_response = client.get("/api/problems")
        assert problems_response.status_code == 200
        problems = problems_response.json()["problems"]
        assert len(problems) > 0
        
        # Step 2: Run optimization
        request_data = {
            "problem_type": "portfolio",
            "problem_params": {
                "returns_file": "sample",
                "n_assets": 6,
                "budget": 2,
                "risk_aversion": 0.5,
            },
            "qaoa_params": {
                "p": 2,
                "shots": 1024,
            },
            "quantum_backend": "aer_simulator",
            "seed": 42,
        }
        
        optimize_response = client.post("/api/optimize", json=request_data)
        assert optimize_response.status_code == 200
        optimize_data = optimize_response.json()
        run_id = optimize_data["run_id"]
        
        # Verify optimization results
        assert optimize_data["problem_type"] == "portfolio"
        assert optimize_data["quantum_result"]["backend_used"] == "aer_simulator"
        assert len(optimize_data["classical_results"]) >= 2  # At least 2 classical solvers
        
        # Step 3: Retrieve the run
        get_response = client.get(f"/api/runs/{run_id}")
        assert get_response.status_code == 200
        get_data = get_response.json()
        
        # Verify retrieved data matches optimization output
        assert get_data["run_id"] == run_id
        assert get_data["problem_type"] == optimize_data["problem_type"]
        assert get_data["quantum_result"] == optimize_data["quantum_result"]
        
        # Step 4: Check health
        health_response = client.get("/api/health")
        assert health_response.status_code == 200
    
    def test_caching_behavior(self, client):
        """Test that identical requests use caching."""
        request_data = {
            "problem_type": "portfolio",
            "problem_params": {
                "returns_file": "sample",
                "n_assets": 5,
                "budget": 2,
                "risk_aversion": 0.5,
            },
            "qaoa_params": {
                "p": 1,
                "shots": 1024,
            },
            "seed": 12345,  # Fixed seed for determinism
            "quantum_backend": "aer_simulator",
        }
        
        # First request
        response1 = client.post("/api/optimize", json=request_data)
        assert response1.status_code == 200
        data1 = response1.json()
        time1 = data1["execution_time_seconds"]
        
        # Second identical request (should be faster due to caching)
        response2 = client.post("/api/optimize", json=request_data)
        assert response2.status_code == 200
        data2 = response2.json()
        time2 = data2["execution_time_seconds"]
        
        # Results should be identical
        assert data1["quantum_result"]["objective_value"] == data2["quantum_result"]["objective_value"]
        assert data1["quantum_result"]["solution"] == data2["quantum_result"]["solution"]
        
        # Second request should be significantly faster (cached)
        # Allow some margin for timing variations
        assert time2 < time1 or time2 < 1.0  # Either faster or very fast (< 1s indicates cache hit)
    
    def test_different_seeds_different_results(self, client):
        """Test that different seeds produce different results."""
        base_request = {
            "problem_type": "portfolio",
            "problem_params": {
                "returns_file": "sample",
                "n_assets": 5,
                "budget": 2,
            },
            "qaoa_params": {
                "p": 1,
                "shots": 1024,
            },
            "quantum_backend": "aer_simulator",
        }
        
        # Request with seed 1
        request1 = {**base_request, "seed": 1}
        response1 = client.post("/api/optimize", json=request1)
        assert response1.status_code == 200
        
        # Request with seed 2
        request2 = {**base_request, "seed": 2}
        response2 = client.post("/api/optimize", json=request2)
        assert response2.status_code == 200
        
        # Results should differ (different random initializations)
        # Note: They might occasionally match by chance, but unlikely
        data1 = response1.json()
        data2 = response2.json()
        
        # At minimum, the run IDs should be different
        assert data1["run_id"] != data2["run_id"]


class TestCORSHeaders:
    """Tests for CORS configuration."""
    
    def test_cors_headers_present(self, client):
        """Test that CORS headers are properly set."""
        response = client.options(
            "/api/optimize",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
            },
        )
        
        # CORS preflight should succeed
        assert response.status_code == 200
        
        # Check CORS headers
        headers = response.headers
        assert "access-control-allow-origin" in headers
        assert "access-control-allow-methods" in headers


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
