/**
 * Run History Component
 * Displays past optimization runs with ability to view details
 */

'use client'

import { useState } from 'react'
import { useRun } from '@/lib/hooks/use-optimization'
import { OptimizationResponse } from '@/lib/types'
import { formatRuntime, formatObjective, formatRatio } from '@/lib/utils/format'
import { Clock, CheckCircle, XCircle, ChevronRight, Trash2 } from 'lucide-react'

interface RunHistoryProps {
  onSelectRun?: (run: OptimizationResponse) => void
}

interface StoredRun {
  run_id: string
  timestamp: number
  problem_type: string
  n_assets: number
  budget: number
  cached?: boolean
}

export function RunHistory({ onSelectRun }: RunHistoryProps) {
  const [runHistory, setRunHistory] = useState<StoredRun[]>(() => {
    // Load from localStorage
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem('quantabench_run_history')
      return stored ? JSON.parse(stored) : []
    }
    return []
  })
  
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null)
  const { data: selectedRun, isLoading, isError } = useRun(selectedRunId)

  const handleSelectRun = (runId: string) => {
    setSelectedRunId(runId)
  }

  const handleDeleteRun = (runId: string, e: React.MouseEvent) => {
    e.stopPropagation()
    const updated = runHistory.filter(r => r.run_id !== runId)
    setRunHistory(updated)
    localStorage.setItem('quantabench_run_history', JSON.stringify(updated))
    if (selectedRunId === runId) {
      setSelectedRunId(null)
    }
  }

  const handleClearAll = () => {
    setRunHistory([])
    localStorage.removeItem('quantabench_run_history')
    setSelectedRunId(null)
  }

  // When a run is loaded and onSelectRun is provided, pass it up
  if (selectedRun && onSelectRun) {
    onSelectRun(selectedRun)
  }

  return (
    <div className="run-history">
      <div className="run-history-header">
        <div>
          <h3>Run History</h3>
          <p>{runHistory.length} previous runs</p>
        </div>
        {runHistory.length > 0 && (
          <button onClick={handleClearAll} className="clear-button">
            <Trash2 size={14} />
            Clear all
          </button>
        )}
      </div>

      <div className="run-list">
        {runHistory.length === 0 ? (
          <div className="empty-state">
            <Clock size={32} />
            <p>No runs yet</p>
            <small>Run a benchmark to see it here</small>
          </div>
        ) : (
          runHistory.map((run) => (
            <button
              key={run.run_id}
              className={`run-item ${selectedRunId === run.run_id ? 'selected' : ''}`}
              onClick={() => handleSelectRun(run.run_id)}
            >
              <div className="run-icon">
                <CheckCircle size={16} />
              </div>
              <div className="run-details">
                <div className="run-title">
                  {run.problem_type === 'portfolio' ? 'Portfolio' : 'Max-Cut'} · 
                  N={run.n_assets}, K={run.budget}
                </div>
                <div className="run-meta">
                  {new Date(run.timestamp).toLocaleString()} · 
                  <code>{run.run_id.slice(-8)}</code>
                  {run.cached && <span className="cached-badge">cached</span>}
                </div>
              </div>
              <button
                className="delete-button"
                onClick={(e) => handleDeleteRun(run.run_id, e)}
                aria-label="Delete run"
              >
                <Trash2 size={14} />
              </button>
              <ChevronRight size={16} className="chevron" />
            </button>
          ))
        )}
      </div>

      {selectedRunId && (
        <div className="run-details-panel">
          {isLoading && (
            <div className="loading-state">
              <div className="spinner" />
              <p>Loading run details...</p>
            </div>
          )}
          
          {isError && (
            <div className="error-state">
              <XCircle size={24} />
              <p>Failed to load run details</p>
              <button onClick={() => setSelectedRunId(null)}>Close</button>
            </div>
          )}
          
          {selectedRun && (
            <div className="run-summary">
              <div className="summary-header">
                <h4>Run Details</h4>
                <button onClick={() => setSelectedRunId(null)}>×</button>
              </div>
              
              <div className="summary-grid">
                <div className="summary-item">
                  <span>Run ID</span>
                  <code>{selectedRun.run_id}</code>
                </div>
                <div className="summary-item">
                  <span>Problem</span>
                  <strong>{selectedRun.problem_type}</strong>
                </div>
                <div className="summary-item">
                  <span>Quantum Objective</span>
                  <strong>{formatObjective(selectedRun.quantum_result.objective_value)}</strong>
                </div>
                <div className="summary-item">
                  <span>Best Classical</span>
                  <strong>{formatObjective(selectedRun.best_classical_result.objective_value)}</strong>
                </div>
                <div className="summary-item">
                  <span>Approx. Ratio</span>
                  <strong>{formatRatio(selectedRun.metrics.approximation_ratio)}</strong>
                </div>
                <div className="summary-item">
                  <span>Execution Time</span>
                  <strong>{formatRuntime(selectedRun.execution_time_seconds)}</strong>
                </div>
              </div>

              <div className="honest-assessment">
                <strong>Assessment:</strong>
                <p>{selectedRun.metrics.honest_assessment}</p>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

/**
 * Hook to manage run history in localStorage
 */
export function useRunHistory() {
  const addRun = (run: OptimizationResponse) => {
    if (typeof window === 'undefined') return

    const stored = localStorage.getItem('quantabench_run_history')
    const history: StoredRun[] = stored ? JSON.parse(stored) : []
    
    const newRun: StoredRun = {
      run_id: run.run_id,
      timestamp: Date.now(),
      problem_type: run.problem_type,
      n_assets: (run.problem_params as any).n_assets || 0,
      budget: (run.problem_params as any).budget || 0,
      cached: run.cache_hit,
    }
    
    // Add to beginning, keep last 20
    const updated = [newRun, ...history.filter(r => r.run_id !== run.run_id)].slice(0, 20)
    localStorage.setItem('quantabench_run_history', JSON.stringify(updated))
  }

  return { addRun }
}
