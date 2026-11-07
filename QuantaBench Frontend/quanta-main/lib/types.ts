/**
 * TypeScript types for QuantaBench API
 * Matches backend Pydantic schemas
 */

// ============================================================================
// Request Types
// ============================================================================

export interface OptimizationRequest {
  problem_type: 'portfolio' | 'maxcut';
  problem_params: PortfolioProblemParams | MaxCutProblemParams;
  qaoa_params: QAOAParams;
  quantum_backend?: 'aer_simulator' | 'classiq' | 'qbraid';
  seed?: number;
}

export interface PortfolioProblemParams {
  returns_file: string;
  n_assets: number;
  budget: number;
  risk_aversion?: number;
}

export interface MaxCutProblemParams {
  adjacency_matrix: number[][];
}

export interface QAOAParams {
  p: number;
  shots: number;
}

// ============================================================================
// Response Types
// ============================================================================

export interface OptimizationResponse {
  run_id: string;
  problem_type: string;
  problem_params: PortfolioProblemParams | MaxCutProblemParams;
  quantum_result: SolverResult;
  classical_results: SolverResult[];
  best_classical_result: SolverResult;
  metrics: BenchmarkMetrics;
  execution_time_seconds: number;
  cache_hit: boolean;
}

export interface SolverResult {
  solver_name: string;
  solution: string;
  objective_value: number;
  is_feasible: boolean;
  constraint_violations: Record<string, number>;
  execution_time_seconds: number;
  backend_used?: string;
  additional_info?: Record<string, any>;
}

export interface BenchmarkMetrics {
  approximation_ratio: number | null;
  probability_of_optimal: number | null;
  honest_assessment: string;
  optimal_objective: number | null;
  quantum_vs_optimal_gap: number | null;
  feasibility_rate: number;
  sharpe_ratio?: number;
}

export interface HealthResponse {
  status: 'healthy' | 'degraded' | 'unhealthy';
  version: string;
  timestamp: string;
  backends_available: {
    aer_simulator: boolean;
    classiq: boolean;
    qbraid: boolean;
  };
  cache_enabled: boolean;
}

export interface ProblemInfo {
  id: string;
  name: string;
  description: string;
  parameters: Record<string, ParameterInfo>;
}

export interface ParameterInfo {
  type: string;
  description: string;
  required: boolean;
  default?: any;
  constraints?: string;
}

export interface ProblemsResponse {
  problems: ProblemInfo[];
}

// ============================================================================
// UI State Types
// ============================================================================

export interface WorkbenchState {
  // Problem setup
  dataset: string;
  n_assets: number;
  budget: number;
  risk_aversion: number;
  penalty_lambda: number;
  shots: number;
  qaoa_depth: number;
  optimizer: string;
  restarts: number;
  backend: string;
  seed: string;
  deterministic: boolean;
  
  // Execution state
  isRunning: boolean;
  currentStep?: ExecutionStep;
  progress: number;
}

export type ExecutionStep = 
  | 'build_qubo'
  | 'synthesize'
  | 'execute'
  | 'decode'
  | 'classical';

export interface Asset {
  ticker: string;
  name: string;
  weight: string;
  return: string;
  risk: string;
  selected: boolean;
}

export interface SolverComparison {
  name: string;
  type: 'Quantum' | 'Exact classical' | 'Heuristic';
  objective: string;
  sharpe: string;
  ratio: string;
  runtime: string;
  color: 'quantum' | 'navy' | 'classical';
  icon: string;
  isFeasible: boolean;
}

// ============================================================================
// Error Types
// ============================================================================

export interface APIError {
  detail: string;
  status: number;
  timestamp?: string;
}

export class QuantaBenchError extends Error {
  constructor(
    message: string,
    public status?: number,
    public details?: any
  ) {
    super(message);
    this.name = 'QuantaBenchError';
  }
}
