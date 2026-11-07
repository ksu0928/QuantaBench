/**
 * React Query hooks for optimization API
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../api-client';
import {
  OptimizationRequest,
  OptimizationResponse,
  QuantaBenchError,
} from '../types';

/**
 * Hook for running optimization
 */
export function useOptimization() {
  const queryClient = useQueryClient();

  return useMutation<OptimizationResponse, QuantaBenchError, OptimizationRequest>({
    mutationFn: (request) => api.optimize(request),
    onSuccess: (data) => {
      // Cache the result for later retrieval
      queryClient.setQueryData(['run', data.run_id], data);
    },
  });
}

/**
 * Hook for fetching a specific run
 */
export function useRun(runId: string | null) {
  return useQuery<OptimizationResponse, QuantaBenchError>({
    queryKey: ['run', runId],
    queryFn: () => api.getRun(runId!),
    enabled: !!runId,
    staleTime: Infinity, // Results never become stale
  });
}

/**
 * Hook for health check
 */
export function useHealth() {
  return useQuery({
    queryKey: ['health'],
    queryFn: () => api.health(),
    refetchInterval: 30000, // Refetch every 30 seconds
    retry: 1,
  });
}

/**
 * Hook for available problems
 */
export function useProblems() {
  return useQuery({
    queryKey: ['problems'],
    queryFn: () => api.getProblems(),
    staleTime: Infinity, // Problems don't change
  });
}
