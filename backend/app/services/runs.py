"""Run registry for tracking optimization runs.

This module maintains a registry of optimization runs with their status,
results, and metadata. It provides progress tracking and result retrieval.
"""

import uuid
from datetime import datetime
from typing import Dict, List, Optional

from ..schemas import OptimizationResponse, RunStatus


class RunRegistry:
    """In-memory registry of optimization runs.
    
    Note: For production, this should be backed by a database.
    For the competition demo, in-memory is sufficient.
    """

    def __init__(self):
        """Initialize run registry."""
        self._runs: Dict[str, OptimizationResponse] = {}
        self._status: Dict[str, RunStatus] = {}

    def create_run(
        self,
        problem_type: str,
        problem_params: Dict,
        solvers: List[str],
    ) -> str:
        """Create a new run entry.
        
        Args:
            problem_type: Type of problem
            problem_params: Problem parameters
            solvers: List of solvers to run
            
        Returns:
            Run ID
        """
        run_id = str(uuid.uuid4())

        # Create initial response
        response = OptimizationResponse(
            run_id=run_id,
            status=RunStatus.PENDING,
            problem_type=problem_type,
            problem_params=problem_params,
            results={},
            metrics=None,
            created_at=datetime.now(),
            completed_at=None,
            error=None,
            cache_hit=False,
        )

        self._runs[run_id] = response
        self._status[run_id] = RunStatus.PENDING

        return run_id

    def update_status(self, run_id: str, status: RunStatus) -> None:
        """Update run status.
        
        Args:
            run_id: Run identifier
            status: New status
        """
        if run_id not in self._runs:
            raise ValueError(f"Run {run_id} not found")

        self._status[run_id] = status
        self._runs[run_id].status = status

        if status == RunStatus.COMPLETED:
            self._runs[run_id].completed_at = datetime.now()

    def update_results(
        self,
        run_id: str,
        results: Dict,
        metrics: Optional[Dict] = None,
    ) -> None:
        """Update run with results.
        
        Args:
            run_id: Run identifier
            results: Solver results
            metrics: Metrics
        """
        if run_id not in self._runs:
            raise ValueError(f"Run {run_id} not found")

        self._runs[run_id].results = results

        if metrics is not None:
            self._runs[run_id].metrics = metrics

    def set_error(self, run_id: str, error: str) -> None:
        """Mark run as failed with error.
        
        Args:
            run_id: Run identifier
            error: Error message
        """
        if run_id not in self._runs:
            raise ValueError(f"Run {run_id} not found")

        self._runs[run_id].status = RunStatus.FAILED
        self._runs[run_id].error = error
        self._runs[run_id].completed_at = datetime.now()
        self._status[run_id] = RunStatus.FAILED

    def set_cached(self, run_id: str) -> None:
        """Mark run as using cached result.
        
        Args:
            run_id: Run identifier
        """
        if run_id not in self._runs:
            raise ValueError(f"Run {run_id} not found")

        self._runs[run_id].status = RunStatus.CACHED
        self._runs[run_id].cache_hit = True
        self._runs[run_id].completed_at = datetime.now()
        self._status[run_id] = RunStatus.CACHED

    def get_run(self, run_id: str) -> Optional[OptimizationResponse]:
        """Get run by ID.
        
        Args:
            run_id: Run identifier
            
        Returns:
            OptimizationResponse or None
        """
        return self._runs.get(run_id)

    def get_status(self, run_id: str) -> Optional[RunStatus]:
        """Get run status.
        
        Args:
            run_id: Run identifier
            
        Returns:
            RunStatus or None
        """
        return self._status.get(run_id)

    def list_runs(
        self,
        limit: int = 100,
        status_filter: Optional[RunStatus] = None,
    ) -> List[OptimizationResponse]:
        """List recent runs.
        
        Args:
            limit: Maximum number of runs to return
            status_filter: Filter by status (optional)
            
        Returns:
            List of runs, newest first
        """
        runs = list(self._runs.values())

        # Filter by status if requested
        if status_filter is not None:
            runs = [r for r in runs if r.status == status_filter]

        # Sort by creation time (newest first)
        runs.sort(key=lambda r: r.created_at, reverse=True)

        return runs[:limit]

    def delete_run(self, run_id: str) -> bool:
        """Delete a run.
        
        Args:
            run_id: Run identifier
            
        Returns:
            True if deleted
        """
        if run_id in self._runs:
            del self._runs[run_id]
            del self._status[run_id]
            return True
        return False

    def clear_all(self) -> int:
        """Clear all runs.
        
        Returns:
            Number of runs cleared
        """
        count = len(self._runs)
        self._runs.clear()
        self._status.clear()
        return count

    def get_stats(self) -> Dict:
        """Get registry statistics.
        
        Returns:
            Dict with stats
        """
        status_counts = {}
        for status in RunStatus:
            status_counts[status.value] = sum(
                1 for s in self._status.values() if s == status
            )

        return {
            "total_runs": len(self._runs),
            "status_counts": status_counts,
        }


# Global registry instance
_registry_instance: Optional[RunRegistry] = None


def get_registry() -> RunRegistry:
    """Get global run registry instance.
    
    Returns:
        RunRegistry singleton
    """
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = RunRegistry()
    return _registry_instance
