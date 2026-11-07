"""Unit tests for caching and run registry."""

import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from app.schemas import RunStatus
from app.services.cache import ResultCache, build_cache_params
from app.services.runs import RunRegistry


class TestResultCache:
    """Test result caching."""

    @pytest.fixture
    def temp_cache_dir(self):
        """Create temporary cache directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def cache(self, temp_cache_dir):
        """Create cache instance."""
        return ResultCache(cache_dir=temp_cache_dir)

    def test_initialization(self, cache, temp_cache_dir):
        """Test cache initialization."""
        assert cache.cache_dir == temp_cache_dir
        assert cache.enabled is True
        assert cache.cache_dir.exists()

    def test_cache_key_generation(self, cache):
        """Test cache key generation is deterministic."""
        params1 = {"a": 1, "b": 2, "c": 3}
        params2 = {"c": 3, "b": 2, "a": 1}  # Different order

        key1 = cache._generate_cache_key(params1)
        key2 = cache._generate_cache_key(params2)

        # Should be same despite different order
        assert key1 == key2

    def test_cache_key_different_for_different_params(self, cache):
        """Test different params produce different keys."""
        params1 = {"a": 1, "b": 2}
        params2 = {"a": 1, "b": 3}

        key1 = cache._generate_cache_key(params1)
        key2 = cache._generate_cache_key(params2)

        assert key1 != key2

    def test_get_nonexistent(self, cache):
        """Test getting non-existent cache entry."""
        params = {"test": "value"}
        result = cache.get(params)

        assert result is None

    def test_set_and_get(self, cache):
        """Test setting and retrieving cache entry."""
        params = {"problem": "portfolio", "n": 5}
        result = {"solution": "1010", "objective": 123.45}

        # Set cache
        cache.set(params, result)

        # Get cache
        cached = cache.get(params)

        assert cached is not None
        assert cached["solution"] == "1010"
        assert cached["objective"] == 123.45
        assert cached["_cache_hit"] is True

    def test_cache_persistence(self, temp_cache_dir):
        """Test cache persists across instances."""
        params = {"test": "persistence"}
        result = {"value": 42}

        # Create cache, set value
        cache1 = ResultCache(cache_dir=temp_cache_dir)
        cache1.set(params, result)

        # Create new cache instance
        cache2 = ResultCache(cache_dir=temp_cache_dir)
        cached = cache2.get(params)

        assert cached is not None
        assert cached["value"] == 42

    def test_invalidate(self, cache):
        """Test cache invalidation."""
        params = {"test": "invalidate"}
        result = {"value": 100}

        # Set and verify cached
        cache.set(params, result)
        assert cache.get(params) is not None

        # Invalidate
        was_invalidated = cache.invalidate(params)
        assert was_invalidated is True

        # Should no longer be cached
        assert cache.get(params) is None

    def test_invalidate_nonexistent(self, cache):
        """Test invalidating non-existent entry."""
        params = {"nonexistent": True}
        was_invalidated = cache.invalidate(params)

        assert was_invalidated is False

    def test_clear_all(self, cache):
        """Test clearing all cache entries."""
        # Add multiple entries
        for i in range(5):
            cache.set({"index": i}, {"value": i})

        # Clear all
        count = cache.clear_all()

        assert count == 5

        # Verify all cleared
        for i in range(5):
            assert cache.get({"index": i}) is None

    def test_cache_stats(self, cache):
        """Test cache statistics."""
        # Add some entries
        for i in range(3):
            cache.set({"index": i}, {"value": i * 100})

        stats = cache.get_stats()

        assert stats["enabled"] is True
        assert stats["num_entries"] == 3
        assert stats["total_size_bytes"] > 0
        assert "cache_dir" in stats

    def test_disabled_cache(self, temp_cache_dir):
        """Test cache behavior when disabled."""
        cache = ResultCache(cache_dir=temp_cache_dir)
        cache.enabled = False

        params = {"test": "disabled"}
        result = {"value": 999}

        # Set should do nothing
        cache.set(params, result)

        # Get should return None
        assert cache.get(params) is None

        stats = cache.get_stats()
        assert stats["enabled"] is False


class TestBuildCacheParams:
    """Test cache parameter building."""

    def test_basic_params(self):
        """Test building basic cache params."""
        cache_params = build_cache_params(
            problem_type="portfolio",
            problem_params={"n": 5, "k": 3},
            solvers=["brute_force", "greedy"],
        )

        assert cache_params["problem_type"] == "portfolio"
        assert cache_params["problem_params"] == {"n": 5, "k": 3}
        assert cache_params["solvers"] == ["brute_force", "greedy"]

    def test_solvers_sorted(self):
        """Test that solvers are sorted for consistency."""
        cache_params = build_cache_params(
            problem_type="portfolio",
            problem_params={"n": 5},
            solvers=["greedy", "brute_force", "annealing"],
        )

        # Should be sorted
        assert cache_params["solvers"] == ["annealing", "brute_force", "greedy"]

    def test_with_qaoa_params(self):
        """Test including QAOA parameters."""
        cache_params = build_cache_params(
            problem_type="portfolio",
            problem_params={"n": 5},
            solvers=["quantum_qaoa"],
            qaoa_params={"p": 2, "backend": "aer", "shots": 1024},
        )

        assert "qaoa_params" in cache_params
        assert cache_params["qaoa_params"]["p"] == 2
        assert cache_params["qaoa_params"]["backend"] == "aer"
        # Shots should be excluded from cache key


class TestRunRegistry:
    """Test run registry."""

    @pytest.fixture
    def registry(self):
        """Create fresh registry."""
        return RunRegistry()

    def test_create_run(self, registry):
        """Test creating a run."""
        run_id = registry.create_run(
            problem_type="portfolio",
            problem_params={"n": 5},
            solvers=["brute_force"],
        )

        assert run_id is not None
        assert len(run_id) > 0

        # Should be retrievable
        run = registry.get_run(run_id)
        assert run is not None
        assert run.status == RunStatus.PENDING

    def test_update_status(self, registry):
        """Test updating run status."""
        run_id = registry.create_run(
            problem_type="portfolio",
            problem_params={"n": 5},
            solvers=["brute_force"],
        )

        # Update to running
        registry.update_status(run_id, RunStatus.RUNNING)
        assert registry.get_status(run_id) == RunStatus.RUNNING

        # Update to completed
        registry.update_status(run_id, RunStatus.COMPLETED)
        run = registry.get_run(run_id)
        assert run.status == RunStatus.COMPLETED
        assert run.completed_at is not None

    def test_update_results(self, registry):
        """Test updating run results."""
        run_id = registry.create_run(
            problem_type="portfolio",
            problem_params={"n": 5},
            solvers=["brute_force"],
        )

        results = {"brute_force": {"objective": 123.45}}
        metrics = {"approximation_ratio": 1.0}

        registry.update_results(run_id, results, metrics)

        run = registry.get_run(run_id)
        assert run.results == results
        assert run.metrics == metrics

    def test_set_error(self, registry):
        """Test marking run as failed."""
        run_id = registry.create_run(
            problem_type="portfolio",
            problem_params={"n": 5},
            solvers=["brute_force"],
        )

        error_msg = "Something went wrong"
        registry.set_error(run_id, error_msg)

        run = registry.get_run(run_id)
        assert run.status == RunStatus.FAILED
        assert run.error == error_msg
        assert run.completed_at is not None

    def test_set_cached(self, registry):
        """Test marking run as cached."""
        run_id = registry.create_run(
            problem_type="portfolio",
            problem_params={"n": 5},
            solvers=["brute_force"],
        )

        registry.set_cached(run_id)

        run = registry.get_run(run_id)
        assert run.status == RunStatus.CACHED
        assert run.cache_hit is True
        assert run.completed_at is not None

    def test_list_runs(self, registry):
        """Test listing runs."""
        # Create multiple runs
        run_ids = []
        for i in range(5):
            run_id = registry.create_run(
                problem_type="portfolio",
                problem_params={"n": i},
                solvers=["brute_force"],
            )
            run_ids.append(run_id)

        runs = registry.list_runs()

        assert len(runs) == 5
        # Should be newest first
        assert runs[0].run_id == run_ids[-1]

    def test_list_runs_with_limit(self, registry):
        """Test listing runs with limit."""
        for i in range(10):
            registry.create_run(
                problem_type="portfolio",
                problem_params={"n": i},
                solvers=["brute_force"],
            )

        runs = registry.list_runs(limit=3)

        assert len(runs) == 3

    def test_list_runs_with_status_filter(self, registry):
        """Test filtering runs by status."""
        # Create runs with different statuses
        run_id1 = registry.create_run("portfolio", {"n": 5}, ["brute_force"])
        run_id2 = registry.create_run("portfolio", {"n": 6}, ["brute_force"])
        run_id3 = registry.create_run("portfolio", {"n": 7}, ["brute_force"])

        registry.update_status(run_id1, RunStatus.COMPLETED)
        registry.update_status(run_id2, RunStatus.COMPLETED)
        registry.update_status(run_id3, RunStatus.FAILED)

        # Filter by completed
        completed_runs = registry.list_runs(status_filter=RunStatus.COMPLETED)
        assert len(completed_runs) == 2

        # Filter by failed
        failed_runs = registry.list_runs(status_filter=RunStatus.FAILED)
        assert len(failed_runs) == 1

    def test_delete_run(self, registry):
        """Test deleting a run."""
        run_id = registry.create_run(
            problem_type="portfolio",
            problem_params={"n": 5},
            solvers=["brute_force"],
        )

        # Delete
        was_deleted = registry.delete_run(run_id)
        assert was_deleted is True

        # Should no longer exist
        assert registry.get_run(run_id) is None

    def test_delete_nonexistent_run(self, registry):
        """Test deleting non-existent run."""
        was_deleted = registry.delete_run("nonexistent-id")
        assert was_deleted is False

    def test_clear_all(self, registry):
        """Test clearing all runs."""
        # Create multiple runs
        for i in range(5):
            registry.create_run(
                problem_type="portfolio",
                problem_params={"n": i},
                solvers=["brute_force"],
            )

        count = registry.clear_all()

        assert count == 5
        assert len(registry.list_runs()) == 0

    def test_get_stats(self, registry):
        """Test registry statistics."""
        # Create runs with different statuses
        run_id1 = registry.create_run("portfolio", {"n": 5}, ["brute_force"])
        run_id2 = registry.create_run("portfolio", {"n": 6}, ["brute_force"])
        run_id3 = registry.create_run("portfolio", {"n": 7}, ["brute_force"])

        registry.update_status(run_id1, RunStatus.COMPLETED)
        registry.update_status(run_id2, RunStatus.COMPLETED)
        # run_id3 stays PENDING

        stats = registry.get_stats()

        assert stats["total_runs"] == 3
        assert stats["status_counts"]["completed"] == 2
        assert stats["status_counts"]["pending"] == 1

    def test_update_nonexistent_raises_error(self, registry):
        """Test that updating non-existent run raises error."""
        with pytest.raises(ValueError, match="not found"):
            registry.update_status("nonexistent", RunStatus.COMPLETED)

        with pytest.raises(ValueError, match="not found"):
            registry.update_results("nonexistent", {})

        with pytest.raises(ValueError, match="not found"):
            registry.set_error("nonexistent", "error")


class TestIntegration:
    """Integration tests for cache and registry together."""

    @pytest.fixture
    def temp_cache_dir(self):
        """Create temporary cache directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_cache_and_registry_workflow(self, temp_cache_dir):
        """Test typical workflow using both cache and registry."""
        cache = ResultCache(cache_dir=temp_cache_dir)
        registry = RunRegistry()

        # Build cache params
        cache_params = build_cache_params(
            problem_type="portfolio",
            problem_params={"n": 5, "k": 3},
            solvers=["brute_force", "greedy"],
        )

        # Check cache (should be empty)
        cached_result = cache.get(cache_params)
        assert cached_result is None

        # Create run
        run_id = registry.create_run(
            problem_type="portfolio",
            problem_params={"n": 5, "k": 3},
            solvers=["brute_force", "greedy"],
        )

        # Simulate running optimization
        registry.update_status(run_id, RunStatus.RUNNING)

        results = {
            "brute_force": {"objective": 100.0},
            "greedy": {"objective": 105.0},
        }
        metrics = {"approximation_ratio": 1.0}

        registry.update_results(run_id, results, metrics)
        registry.update_status(run_id, RunStatus.COMPLETED)

        # Cache the results
        cache_data = {
            "results": results,
            "metrics": metrics,
            "run_id": run_id,
        }
        cache.set(cache_params, cache_data)

        # Second request with same params
        run_id2 = registry.create_run(
            problem_type="portfolio",
            problem_params={"n": 5, "k": 3},
            solvers=["brute_force", "greedy"],
        )

        # Check cache (should hit)
        cached_result = cache.get(cache_params)
        assert cached_result is not None
        assert cached_result["results"] == results

        # Mark as cached
        registry.update_results(run_id2, cached_result["results"], cached_result["metrics"])
        registry.set_cached(run_id2)

        run2 = registry.get_run(run_id2)
        assert run2.status == RunStatus.CACHED
        assert run2.cache_hit is True
