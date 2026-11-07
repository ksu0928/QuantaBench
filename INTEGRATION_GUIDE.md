# QuantaBench Frontend-Backend Integration Guide

This guide explains how the QuantaBench frontend and backend are integrated for a complete full-stack quantum optimization workbench.

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (Next.js 14)                    │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  React Components (app/page.tsx)                      │  │
│  │  - Interactive UI with parameter controls             │  │
│  │  - Real-time results display                          │  │
│  │  - Loading states and error handling                  │  │
│  └─────────────────────┬─────────────────────────────────┘  │
│                        │                                     │
│  ┌─────────────────────▼─────────────────────────────────┐  │
│  │  React Query Hooks (lib/hooks/use-optimization.ts)   │  │
│  │  - State management                                   │  │
│  │  - Caching and refetching                            │  │
│  │  - Background updates                                 │  │
│  └─────────────────────┬─────────────────────────────────┘  │
│                        │                                     │
│  ┌─────────────────────▼─────────────────────────────────┐  │
│  │  API Client (lib/api-client.ts)                      │  │
│  │  - Axios HTTP client                                  │  │
│  │  - Request/response transformation                    │  │
│  │  - Error handling and retries                         │  │
│  └─────────────────────┬─────────────────────────────────┘  │
└────────────────────────┼─────────────────────────────────────┘
                         │
                         │ HTTP REST API
                         │ Content-Type: application/json
                         │
┌────────────────────────▼─────────────────────────────────────┐
│                   Backend (FastAPI)                          │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  REST API Endpoints (app/main.py)                     │  │
│  │  - POST /api/optimize                                 │  │
│  │  - GET  /api/runs/{run_id}                           │  │
│  │  - GET  /api/health                                   │  │
│  │  - GET  /api/problems                                 │  │
│  └─────────────────────┬─────────────────────────────────┘  │
│                        │                                     │
│  ┌─────────────────────▼─────────────────────────────────┐  │
│  │  Optimization Pipeline (app/services/pipeline.py)     │  │
│  │  - QAOA quantum solver                                │  │
│  │  - Classical solvers (brute force, annealing, greedy)│  │
│  │  - Metrics computation                                │  │
│  │  - Result caching                                     │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## 📡 API Communication

### Request Flow

1. **User Action** → User clicks "Run Benchmark" button
2. **State Update** → React sets `isPending` state
3. **API Call** → React Query hook calls `api.optimize(request)`
4. **HTTP Request** → Axios sends POST to `/api/optimize`
5. **Backend Processing** → FastAPI executes optimization pipeline
6. **HTTP Response** → Backend returns JSON result
7. **State Update** → React Query updates cache and triggers re-render
8. **UI Update** → Results displayed to user

### Data Types

TypeScript types in `lib/types.ts` match Python Pydantic schemas in `backend/app/schemas.py`:

```typescript
// Frontend
interface OptimizationRequest {
  problem_type: 'portfolio' | 'maxcut';
  problem_params: PortfolioProblemParams;
  qaoa_params: QAOAParams;
  quantum_backend?: string;
  seed?: number;
}

// Backend (Pydantic)
class OptimizationRequest(BaseModel):
    problem_type: ProblemType
    problem_params: Union[PortfolioProblemParams, MaxCutProblemParams]
    qaoa_params: QAOAParams
    quantum_backend: Optional[str] = "aer_simulator"
    seed: Optional[int] = None
```

---

## 🔄 State Management

### React Query Configuration

```typescript
// lib/providers/query-provider.tsx
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,  // Don't refetch on tab switch
      retry: 1,                      // Retry failed requests once
      staleTime: 5 * 60 * 1000,     // Cache for 5 minutes
    },
  },
})
```

### Hooks Usage

```typescript
// In component
const { mutate, isPending, data, error } = useOptimization()

// Trigger optimization
mutate(request, {
  onSuccess: (data) => {
    console.log('Optimization complete:', data.run_id)
  },
  onError: (error) => {
    console.error('Optimization failed:', error.message)
  },
})
```

---

## 🎨 UI Components

### Loading States

**Progress Tracking:**
```typescript
const [currentStep, setCurrentStep] = useState<ExecutionStep | null>(null)

useEffect(() => {
  if (isPending) {
    const steps: ExecutionStep[] = [
      'build_qubo',
      'synthesize', 
      'execute',
      'decode',
      'classical'
    ]
    // Update step every 1.5 seconds
  }
}, [isPending])
```

**Visual Feedback:**
- Spinner animation during execution
- Step-by-step progress modal
- Estimated time for each step
- Smooth transitions

### Error Handling

**Error Banner:**
```tsx
{isError && error && (
  <div className="error-banner">
    <AlertCircle />
    <div>
      <strong>Error running optimization</strong>
      <p>{error.message}</p>
    </div>
    <button onClick={retry}>Retry</button>
  </div>
)}
```

**Error Types:**
- Network errors (backend offline)
- Validation errors (invalid parameters)
- Backend errors (optimization failed)
- Timeout errors (request too long)

### Real-time Updates

**KPI Cards:**
```typescript
useEffect(() => {
  if (optimizationResult) {
    setKpiData({
      approximationRatio: metrics.approximation_ratio || 0,
      probabilityOptimal: metrics.probability_of_optimal || 0,
      feasibilityRate: metrics.feasibility_rate,
      qubits: n,
      circuitDepth: quantum_result.additional_info?.circuit_depth || 42,
    })
  }
}, [optimizationResult])
```

---

## 🗄️ Run History

### localStorage Implementation

**Storage Format:**
```typescript
interface StoredRun {
  run_id: string
  timestamp: number
  problem_type: string
  n_assets: number
  budget: number
  cached?: boolean
}
```

**Usage:**
```typescript
const { addRun } = useRunHistory()

// After optimization completes
addRun(optimizationResult)
```

**Features:**
- Stores last 20 runs
- Persists across browser sessions
- Click to view past results
- Delete individual runs
- Clear all history

---

## 🐳 Deployment

### Docker Compose

**Full Stack Deployment:**
```yaml
services:
  backend:
    build: ./backend
    ports: ["8000:8000"]
    environment:
      - CLASSIQ_CLIENT_ID=${CLASSIQ_CLIENT_ID}
      - QBRAID_API_KEY=${QBRAID_API_KEY}
  
  frontend:
    build: ./QuantaBench Frontend/quanta-main
    ports: ["3000:3000"]
    environment:
      - NEXT_PUBLIC_API_URL=http://backend:8000
    depends_on:
      - backend
```

**Commands:**
```bash
# Start full stack
docker-compose up --build

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Development Setup

**Backend:**
```bash
cd backend
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd "QuantaBench Frontend/quanta-main"
pnpm install
pnpm dev
```

**Access:**
- Frontend: http://localhost:3000
- Backend: http://localhost:8000
- API Docs: http://localhost:8000/docs

---

## 🧪 Testing

### Backend Tests

```bash
cd backend

# Unit tests
pytest tests/unit/

# Integration tests
pytest tests/integration/

# With coverage
pytest --cov=app tests/
```

### Frontend Tests

```bash
cd "QuantaBench Frontend/quanta-main"

# E2E tests (requires backend running)
pnpm test:e2e

# Watch mode
pnpm test:watch

# Type checking
pnpm type-check
```

### E2E Test Coverage

- ✅ Health check endpoint
- ✅ Problems listing
- ✅ Full optimization workflow
- ✅ Run retrieval by ID
- ✅ Cache behavior
- ✅ Different problem sizes (N=5,8,10)
- ✅ Different QAOA depths (p=1,2,3)
- ✅ Error handling
- ✅ Honest benchmarking

---

## 🔧 Configuration

### Environment Variables

**Backend (.env):**
```env
CLASSIQ_CLIENT_ID=your_client_id
CLASSIQ_CLIENT_SECRET=your_secret
QBRAID_API_KEY=your_api_key
ENABLE_CLASSIQ=true
ENABLE_QBRAID=true
CACHE_ENABLED=true
```

**Frontend (.env.local):**
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_DEBUG=false
```

### CORS Configuration

**Backend (app/main.py):**
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Frontend (next.config.mjs):**
```javascript
async rewrites() {
  return [
    {
      source: '/api/:path*',
      destination: 'http://localhost:8000/api/:path*',
    },
  ]
}
```

---

## 🚀 Performance Optimization

### Frontend

**Code Splitting:**
- Next.js automatic code splitting
- Dynamic imports for large components
- Route-based code splitting

**Caching:**
- React Query caches API responses
- localStorage for run history
- Service worker for offline support (future)

**Optimization:**
- Image optimization with Next.js
- CSS minification
- Tree shaking unused code

### Backend

**Caching:**
- Disk-based result cache (168 hour TTL)
- Hash-based cache keys
- Instant response for cached requests (<100ms)

**Performance:**
- Async/await for non-blocking I/O
- Connection pooling
- Parallel classical solver execution

---

## 📊 Monitoring

### Backend Health Check

```typescript
const { data: healthData } = useHealth()

// Poll every 30 seconds
useQuery({
  queryKey: ['health'],
  queryFn: () => api.health(),
  refetchInterval: 30000,
})
```

**Health Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "backends_available": {
    "aer_simulator": true,
    "classiq": false,
    "qbraid": false
  },
  "cache_enabled": true
}
```

### Frontend Status Pills

```tsx
<Pill tone={healthData?.backends_available.classiq ? 'success' : 'neutral'}>
  Classiq {healthData?.backends_available.classiq ? 'connected' : 'offline'}
</Pill>
```

---

## 🐛 Debugging

### Enable Debug Logging

**Frontend:**
```env
NEXT_PUBLIC_DEBUG=true
```

**Backend:**
```env
LOG_LEVEL=DEBUG
```

### Common Issues

**1. CORS Errors**
- Check backend CORS configuration
- Verify frontend API URL
- Ensure backend is running

**2. Connection Refused**
- Backend not started: `uvicorn app.main:app`
- Wrong port: Check NEXT_PUBLIC_API_URL
- Firewall blocking: Allow port 8000

**3. Type Errors**
- Run type check: `pnpm type-check`
- Update types in `lib/types.ts`
- Match backend schemas

**4. Cache Issues**
- Clear React Query cache: Browser refresh
- Clear backend cache: Delete `backend/cache/`
- Disable cache: `CACHE_ENABLED=false`

---

## 📈 Metrics & Analytics

### Request Tracking

```typescript
// API client logs all requests in debug mode
if (process.env.NEXT_PUBLIC_DEBUG === 'true') {
  console.log('[API Request]', method, url)
}
```

### Performance Metrics

- Time to first optimization
- Cache hit rate
- Average optimization time
- Error rate by endpoint

---

## 🔐 Security

### API Security

- No hardcoded secrets (use environment variables)
- HTTPS in production
- CORS restricted to known origins
- Request validation (Pydantic schemas)

### Frontend Security

- XSS protection (React escapes by default)
- CSRF protection (SameSite cookies)
- Secure environment variables (NEXT_PUBLIC_ prefix)
- Content Security Policy (CSP) headers

---

## 🎯 Best Practices

### Frontend

1. **Use TypeScript** - Type safety prevents runtime errors
2. **Handle Loading States** - Always show feedback during async operations
3. **Error Boundaries** - Catch and display errors gracefully
4. **Accessibility** - Use semantic HTML and ARIA labels
5. **Performance** - Optimize images, lazy load components

### Backend

1. **Input Validation** - Validate all inputs with Pydantic
2. **Error Handling** - Return meaningful error messages
3. **Logging** - Log all important operations
4. **Testing** - Maintain >90% test coverage
5. **Documentation** - Keep API docs up to date

---

## 📚 Additional Resources

- **Backend README**: `backend/README.md`
- **Competition Summary**: `backend/COMPETITION_SUMMARY.md`
- **API Documentation**: http://localhost:8000/docs
- **Frontend Components**: `QuantaBench Frontend/quanta-main/app/`
- **API Client**: `QuantaBench Frontend/quanta-main/lib/api-client.ts`

---

## 🤝 Contributing

1. Follow TypeScript strict mode
2. Write tests for new features
3. Update this guide for integration changes
4. Use conventional commits
5. Run type-check before committing

---

**Built with ❤️ for transparent quantum computing**
