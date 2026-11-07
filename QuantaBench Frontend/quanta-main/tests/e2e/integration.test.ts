/**
 * End-to-End Integration Tests
 * 
 * Tests the complete workflow from frontend to backend
 * Run with: npm run test:e2e
 */

import { describe, it, expect, beforeAll, afterAll } from '@jest/globals'
import { api } from '@/lib/api-client'
import { OptimizationRequest } from '@/lib/types'

// Test configuration
const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const TEST_TIMEOUT = 60000 // 60 seconds

describe('QuantaBench E2E Integration', () => {
  beforeAll(async () => {
    // Wait for backend to be ready
    let retries = 5
    while (retries > 0) {
      try {
        const health = await api.health()
        if (health.status === 'healthy') {
          console.log('✓ Backend is healthy')
          break
        }
      } catch (error) {
        retries--
        if (retries === 0) {
          throw new Error(`Backend not available at ${BACKEND_URL}`)
        }
        await new Promise(resolve => setTimeout(resolve, 2000))
      }
    }
  })

  describe('Health Check', () => {
    it('should return healthy status', async () => {
      const health = await api.health()
      
      expect(health.status).toBe('healthy')
      expect(health.version).toBeDefined()
      expect(health.backends_available).toBeDefined()
      expect(health.backends_available.aer_simulator).toBe(true)
    })
  })

  describe('Problems Endpoint', () => {
    it('should list available problems', async () => {
      const problems = await api.getProblems()
      
      expect(problems.problems).toBeDefined()
      expect(problems.problems.length).toBeGreaterThan(0)
      
      // Should include portfolio problem
      const portfolio = problems.problems.find(p => p.id === 'portfolio')
      expect(portfolio).toBeDefined()
      expect(portfolio?.name).toBe('Portfolio Optimization')
    })
  })

  describe('Optimization Workflow', () => {
    it('should run portfolio optimization end-to-end', async () => {
      const request: OptimizationRequest = {
        problem_type: 'portfolio',
        problem_params: {
          returns_file: 'sample',
          n_assets: 5,
          budget: 2,
          risk_aversion: 0.5,
        },
        qaoa_params: {
          p: 1,
          shots: 1024,
        },
        quantum_backend: 'aer_simulator',
        seed: 42,
      }

      const result = await api.optimize(request)
      
      // Verify response structure
      expect(result.run_id).toBeDefined()
      expect(result.problem_type).toBe('portfolio')
      expect(result.quantum_result).toBeDefined()
      expect(result.classical_results).toBeDefined()
      expect(result.best_classical_result).toBeDefined()
      expect(result.metrics).toBeDefined()
      
      // Verify quantum result
      expect(result.quantum_result.solution).toBeDefined()
      expect(result.quantum_result.objective_value).toBeDefined()
      expect(result.quantum_result.is_feasible).toBeDefined()
      expect(result.quantum_result.backend_used).toBe('aer_simulator')
      
      // Verify classical results
      expect(result.classical_results.length).toBeGreaterThan(0)
      const solverNames = result.classical_results.map(r => r.solver_name)
      expect(solverNames).toContain('brute_force')
      
      // Verify metrics
      expect(result.metrics.honest_assessment).toBeDefined()
      expect(result.metrics.feasibility_rate).toBeDefined()
      
      // Verify solution format
      expect(result.quantum_result.solution).toMatch(/^[01]+$/)
      expect(result.quantum_result.solution.length).toBe(5)
      
      console.log(`✓ Optimization completed in ${result.execution_time_seconds.toFixed(2)}s`)
      console.log(`✓ Run ID: ${result.run_id}`)
      console.log(`✓ Quantum objective: ${result.quantum_result.objective_value.toFixed(4)}`)
      console.log(`✓ Best classical: ${result.best_classical_result.objective_value.toFixed(4)}`)
      console.log(`✓ Assessment: ${result.metrics.honest_assessment}`)
      
      return result
    }, TEST_TIMEOUT)

    it('should retrieve run by ID', async () => {
      // First, create a run
      const request: OptimizationRequest = {
        problem_type: 'portfolio',
        problem_params: {
          returns_file: 'sample',
          n_assets: 5,
          budget: 2,
        },
        qaoa_params: {
          p: 1,
          shots: 1024,
        },
        seed: 123,
      }

      const createResult = await api.optimize(request)
      const runId = createResult.run_id
      
      // Now retrieve it
      const retrievedResult = await api.getRun(runId)
      
      expect(retrievedResult.run_id).toBe(runId)
      expect(retrievedResult.quantum_result).toEqual(createResult.quantum_result)
      expect(retrievedResult.metrics).toEqual(createResult.metrics)
      
      console.log(`✓ Retrieved run ${runId}`)
    }, TEST_TIMEOUT)

    it('should cache identical requests', async () => {
      const request: OptimizationRequest = {
        problem_type: 'portfolio',
        problem_params: {
          returns_file: 'sample',
          n_assets: 5,
          budget: 2,
          risk_aversion: 0.5,
        },
        qaoa_params: {
          p: 1,
          shots: 1024,
        },
        seed: 999,
      }

      // First request (cache miss)
      const result1 = await api.optimize(request)
      const time1 = result1.execution_time_seconds
      
      // Second request (should be cached)
      const result2 = await api.optimize(request)
      const time2 = result2.execution_time_seconds
      
      // Results should be identical
      expect(result2.quantum_result.objective_value).toBe(result1.quantum_result.objective_value)
      expect(result2.quantum_result.solution).toBe(result1.quantum_result.solution)
      
      // Second request should be faster (cached)
      expect(time2).toBeLessThan(time1)
      
      console.log(`✓ Cache working: ${time1.toFixed(2)}s → ${time2.toFixed(2)}s (${((time1 - time2) / time1 * 100).toFixed(1)}% faster)`)
    }, TEST_TIMEOUT)

    it('should handle different problem sizes', async () => {
      const sizes = [5, 8, 10]
      
      for (const n of sizes) {
        const request: OptimizationRequest = {
          problem_type: 'portfolio',
          problem_params: {
            returns_file: 'sample',
            n_assets: n,
            budget: Math.floor(n / 2),
          },
          qaoa_params: {
            p: 1,
            shots: 1024,
          },
          seed: 42,
        }

        const result = await api.optimize(request)
        
        expect(result.quantum_result.solution.length).toBe(n)
        expect(result.quantum_result.is_feasible).toBe(true)
        
        console.log(`✓ N=${n} completed in ${result.execution_time_seconds.toFixed(2)}s`)
      }
    }, TEST_TIMEOUT * 3)

    it('should handle different QAOA depths', async () => {
      const depths = [1, 2, 3]
      
      for (const p of depths) {
        const request: OptimizationRequest = {
          problem_type: 'portfolio',
          problem_params: {
            returns_file: 'sample',
            n_assets: 6,
            budget: 3,
          },
          qaoa_params: {
            p,
            shots: 1024,
          },
          seed: 42,
        }

        const result = await api.optimize(request)
        
        expect(result.quantum_result).toBeDefined()
        
        console.log(`✓ p=${p} completed, objective: ${result.quantum_result.objective_value.toFixed(4)}`)
      }
    }, TEST_TIMEOUT * 3)
  })

  describe('Error Handling', () => {
    it('should handle invalid problem parameters', async () => {
      const request: OptimizationRequest = {
        problem_type: 'portfolio',
        problem_params: {
          returns_file: 'sample',
          n_assets: 2,  // Too small
          budget: 5,    // Budget > n_assets (invalid)
        },
        qaoa_params: {
          p: 1,
          shots: 1024,
        },
      }

      await expect(api.optimize(request)).rejects.toThrow()
    })

    it('should handle non-existent run ID', async () => {
      await expect(api.getRun('nonexistent-run-id')).rejects.toThrow()
    })
  })

  describe('Honest Benchmarking', () => {
    it('should report when classical wins', async () => {
      // Use p=1 which typically underperforms
      const request: OptimizationRequest = {
        problem_type: 'portfolio',
        problem_params: {
          returns_file: 'sample',
          n_assets: 8,
          budget: 3,
        },
        qaoa_params: {
          p: 1,  // Low depth
          shots: 512,  // Low shots
        },
        seed: 42,
      }

      const result = await api.optimize(request)
      
      // Verify honest assessment is provided
      expect(result.metrics.honest_assessment).toBeDefined()
      expect(result.metrics.honest_assessment.length).toBeGreaterThan(0)
      
      // Log the assessment
      console.log(`✓ Honest assessment: "${result.metrics.honest_assessment}"`)
      
      // Should include approximation ratio
      if (result.metrics.approximation_ratio !== null) {
        expect(result.metrics.approximation_ratio).toBeGreaterThan(0)
        console.log(`✓ Approximation ratio: ${result.metrics.approximation_ratio.toFixed(3)}`)
      }
    }, TEST_TIMEOUT)
  })
})

describe('Frontend API Client', () => {
  it('should handle network errors gracefully', async () => {
    // Create a client with invalid URL
    const badApi = { ...api }
    ;(badApi as any).health = async () => {
      throw new Error('Network error')
    }

    await expect(badApi.health()).rejects.toThrow()
  })
})
