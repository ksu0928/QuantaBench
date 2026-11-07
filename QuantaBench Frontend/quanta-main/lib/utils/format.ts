/**
 * Formatting utilities for display
 */

import { SolverResult, SolverComparison } from '../types';

/**
 * Format objective value for display
 */
export function formatObjective(value: number): string {
  return value.toFixed(4);
}

/**
 * Format percentage
 */
export function formatPercentage(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

/**
 * Format runtime in seconds
 */
export function formatRuntime(seconds: number): string {
  if (seconds < 1) {
    return `${(seconds * 1000).toFixed(0)}ms`;
  } else if (seconds < 60) {
    return `${seconds.toFixed(2)}s`;
  } else {
    const minutes = Math.floor(seconds / 60);
    const secs = (seconds % 60).toFixed(1);
    return `${minutes}m ${secs}s`;
  }
}

/**
 * Format approximation ratio
 */
export function formatRatio(ratio: number | null): string {
  if (ratio === null) return 'N/A';
  return ratio.toFixed(3);
}

/**
 * Get delta text for metrics
 */
export function getDeltaText(
  current: number,
  previous: number | null,
  isPercentage = false
): string {
  if (previous === null) return '';
  
  const delta = current - previous;
  const sign = delta > 0 ? '+' : '';
  
  if (isPercentage) {
    return `${sign}${(delta * 100).toFixed(1)}%`;
  } else {
    return `${sign}${(delta * 100).toFixed(1)}%`;
  }
}

/**
 * Convert solver result to display format
 */
export function solverResultToComparison(
  result: SolverResult,
  optimalObjective: number | null,
  sharpeRatio?: number
): SolverComparison {
  // Determine solver type
  let type: 'Quantum' | 'Exact classical' | 'Heuristic';
  let color: 'quantum' | 'navy' | 'classical';
  let icon: string;

  if (result.solver_name.toLowerCase().includes('qaoa')) {
    type = 'Quantum';
    color = 'quantum';
    icon = '✦';
  } else if (result.solver_name.toLowerCase().includes('brute')) {
    type = 'Exact classical';
    color = 'navy';
    icon = '◎';
  } else if (result.solver_name.toLowerCase().includes('annealing')) {
    type = 'Heuristic';
    color = 'classical';
    icon = '◆';
  } else {
    type = 'Heuristic';
    color = 'classical';
    icon = '●';
  }

  // Calculate approximation ratio
  let ratio = 'N/A';
  if (optimalObjective !== null && optimalObjective !== 0) {
    const approxRatio = result.objective_value / optimalObjective;
    ratio = approxRatio.toFixed(3);
  }

  return {
    name: formatSolverName(result.solver_name),
    type,
    objective: formatObjective(result.objective_value),
    sharpe: sharpeRatio ? sharpeRatio.toFixed(2) : 'N/A',
    ratio,
    runtime: formatRuntime(result.execution_time_seconds),
    color,
    icon,
    isFeasible: result.is_feasible,
  };
}

/**
 * Format solver name for display
 */
export function formatSolverName(name: string): string {
  // Convert snake_case to Title Case
  return name
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

/**
 * Parse bitstring to asset indices
 */
export function bitstringToIndices(bitstring: string): number[] {
  return bitstring
    .split('')
    .map((bit, idx) => (bit === '1' ? idx : -1))
    .filter((idx) => idx !== -1);
}

/**
 * Calculate portfolio weight for each asset
 */
export function calculateWeights(
  selectedIndices: number[],
  expectedReturns?: number[]
): string[] {
  const n = selectedIndices.length;
  
  if (!expectedReturns) {
    // Equal weight
    const weight = (100 / n).toFixed(1);
    return selectedIndices.map(() => `${weight}%`);
  }
  
  // Weight by expected return (simple heuristic)
  const selectedReturns = selectedIndices.map((i) => expectedReturns[i]);
  const totalReturn = selectedReturns.reduce((sum, r) => sum + r, 0);
  
  return selectedReturns.map((r) => {
    const weight = (r / totalReturn) * 100;
    return `${weight.toFixed(1)}%`;
  });
}

/**
 * Get color class for metric delta
 */
export function getDeltaColorClass(delta: number): string {
  if (delta > 0) return 'delta up';
  if (delta < 0) return 'delta down';
  return 'delta';
}

/**
 * Extract measurement histogram from solver result
 */
export function extractHistogram(
  result: SolverResult,
  topN = 10
): Array<{ bitstring: string; probability: number; isFeasible: boolean }> {
  // Check if additional_info contains counts
  const counts = result.additional_info?.counts as Record<string, number> | undefined;
  
  if (!counts) {
    // Return single entry with the solution
    return [
      {
        bitstring: result.solution,
        probability: 1.0,
        isFeasible: result.is_feasible,
      },
    ];
  }
  
  // Convert counts to probabilities
  const totalShots = Object.values(counts).reduce((sum, count) => sum + count, 0);
  const entries = Object.entries(counts).map(([bitstring, count]) => ({
    bitstring,
    probability: count / totalShots,
    isFeasible: true, // TODO: Check feasibility if needed
  }));
  
  // Sort by probability and take top N
  entries.sort((a, b) => b.probability - a.probability);
  return entries.slice(0, topN);
}
