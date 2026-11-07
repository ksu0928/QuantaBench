/**
 * API Client for QuantaBench Backend
 * 
 * Handles all HTTP communication with the FastAPI backend,
 * including error handling, request/response transformation,
 * and type safety.
 */

import axios, { AxiosInstance, AxiosError } from 'axios';
import {
  OptimizationRequest,
  OptimizationResponse,
  HealthResponse,
  ProblemsResponse,
  QuantaBenchError,
} from './types';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/**
 * Create configured axios instance
 */
function createAxiosInstance(): AxiosInstance {
  const instance = axios.create({
    baseURL: API_URL,
    timeout: 180000, // 3 minutes for optimization requests
    headers: {
      'Content-Type': 'application/json',
    },
  });

  // Request interceptor for logging (development only)
  if (process.env.NEXT_PUBLIC_DEBUG === 'true') {
    instance.interceptors.request.use(
      (config) => {
        console.log('[API Request]', config.method?.toUpperCase(), config.url);
        return config;
      },
      (error) => {
        console.error('[API Request Error]', error);
        return Promise.reject(error);
      }
    );
  }

  // Response interceptor for error handling
  instance.interceptors.response.use(
    (response) => response,
    (error: AxiosError) => {
      if (error.response) {
        // Server responded with error status
        const detail = (error.response.data as any)?.detail || 'Unknown error';
        throw new QuantaBenchError(
          detail,
          error.response.status,
          error.response.data
        );
      } else if (error.request) {
        // Request made but no response received
        throw new QuantaBenchError(
          'Backend server is not responding. Make sure the API is running at ' + API_URL,
          503
        );
      } else {
        // Error setting up request
        throw new QuantaBenchError(error.message);
      }
    }
  );

  return instance;
}

const axiosInstance = createAxiosInstance();

/**
 * API Client Class
 */
class QuantaBenchAPI {
  /**
   * Run optimization
   */
  async optimize(request: OptimizationRequest): Promise<OptimizationResponse> {
    const response = await axiosInstance.post<OptimizationResponse>(
      '/api/optimize',
      request
    );
    return response.data;
  }

  /**
   * Get optimization run by ID
   */
  async getRun(runId: string): Promise<OptimizationResponse> {
    const response = await axiosInstance.get<OptimizationResponse>(
      `/api/runs/${runId}`
    );
    return response.data;
  }

  /**
   * Health check
   */
  async health(): Promise<HealthResponse> {
    const response = await axiosInstance.get<HealthResponse>('/api/health');
    return response.data;
  }

  /**
   * List available problems
   */
  async getProblems(): Promise<ProblemsResponse> {
    const response = await axiosInstance.get<ProblemsResponse>('/api/problems');
    return response.data;
  }

  /**
   * Check if backend is available
   */
  async isAvailable(): Promise<boolean> {
    try {
      await this.health();
      return true;
    } catch {
      return false;
    }
  }
}

// Export singleton instance
export const api = new QuantaBenchAPI();

// Export for testing/mocking
export { QuantaBenchAPI };
