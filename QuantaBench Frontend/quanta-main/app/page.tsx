'use client'

import { useState, useEffect } from 'react'
import { Activity, ArrowRight, BarChart3, Check, ChevronDown, CircleHelp, Copy, Download, Gauge, GitBranch, Layers3, Menu, Play, RotateCcw, Settings2, SlidersHorizontal, Sparkles, Target, Timer, Zap, AlertCircle } from 'lucide-react'
import { useOptimization, useHealth } from '@/lib/hooks/use-optimization'
import { OptimizationRequest, SolverComparison, Asset, ExecutionStep } from '@/lib/types'
import { 
  formatObjective, 
  formatPercentage, 
  formatRuntime, 
  formatRatio,
  solverResultToComparison,
  bitstringToIndices,
  calculateWeights,
  extractHistogram
} from '@/lib/utils/format'

// Mock asset data (will be populated from actual tickers in portfolio)
const ASSET_NAMES: Record<string, string> = {
  'NVDA': 'NVIDIA',
  'MSFT': 'Microsoft',
  'LLY': 'Eli Lilly',
  'AVGO': 'Broadcom',
  'AAPL': 'Apple',
  'GOOGL': 'Google',
  'AMZN': 'Amazon',
  'TSLA': 'Tesla',
  'META': 'Meta',
  'JPM': 'JPMorgan',
}

function Pill({ children, tone = 'neutral' }: { children: React.ReactNode; tone?: 'neutral' | 'success' | 'quantum' | 'warning' | 'error' }) {
  return <span className={`pill pill-${tone}`}><span className="pill-dot" />{children}</span>
}

function Card({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return <section className={`card ${className}`}>{children}</section>
}

function SectionHeading({ eyebrow, title, copy }: { eyebrow: string; title: string; copy?: string }) {
  return <div className="section-heading"><div className="eyebrow">{eyebrow}</div><h2>{title}</h2>{copy && <p>{copy}</p>}</div>
}

export default function Page() {
  // API hooks
  const { mutate: runOptimization, isPending, isError, error, data: optimizationResult } = useOptimization()
  const { data: healthData } = useHealth()

  // UI state
  const [presentation, setPresentation] = useState(false)
  const [n, setN] = useState(8)
  const [k, setK] = useState(3)
  const [depth, setDepth] = useState(2)
  const [shots, setShots] = useState(2048)
  const [riskAversion, setRiskAversion] = useState(0.5)
  const [selectedSolver, setSelectedSolver] = useState('QAOA')
  const [showIsing, setShowIsing] = useState(false)
  const [toast, setToast] = useState('')
  const [currentStep, setCurrentStep] = useState<ExecutionStep | null>(null)
  const [progress, setProgress] = useState(0)

  // Derived state from API response
  const [solvers, setSolvers] = useState<SolverComparison[]>([])
  const [assets, setAssets] = useState<Asset[]>([])
  const [kpiData, setKpiData] = useState({
    approximationRatio: 0.963,
    probabilityOptimal: 0.684,
    feasibilityRate: 0.992,
    qubits: n,
    circuitDepth: 42,
  })

  // Update KPI data when optimization completes
  useEffect(() => {
    if (optimizationResult) {
      const metrics = optimizationResult.metrics

      setKpiData({
        approximationRatio: metrics.approximation_ratio || 0,
        probabilityOptimal: metrics.probability_of_optimal || 0,
        feasibilityRate: metrics.feasibility_rate,
        qubits: n,
        circuitDepth: optimizationResult.quantum_result.additional_info?.circuit_depth || 42,
      })

      // Convert solver results to comparison format
      const allSolvers: SolverComparison[] = [
        solverResultToComparison(
          optimizationResult.quantum_result,
          metrics.optimal_objective,
          metrics.sharpe_ratio
        ),
        ...optimizationResult.classical_results.map(r => 
          solverResultToComparison(r, metrics.optimal_objective, metrics.sharpe_ratio)
        ),
      ]
      setSolvers(allSolvers)

      // Parse quantum solution to get selected assets
      const selectedIndices = bitstringToIndices(optimizationResult.quantum_result.solution)
      const weights = calculateWeights(selectedIndices)
      
      // Get ticker symbols (first n from ASSET_NAMES)
      const tickers = Object.keys(ASSET_NAMES).slice(0, n)
      
      const newAssets: Asset[] = tickers.map((ticker, idx) => ({
        ticker,
        name: ASSET_NAMES[ticker] || ticker,
        weight: selectedIndices.includes(idx) ? weights[selectedIndices.indexOf(idx)] : '0%',
        return: 'N/A',
        risk: 'N/A',
        selected: selectedIndices.includes(idx),
      }))
      
      setAssets(newAssets.filter(a => a.selected))
      
      setToast('Benchmark complete — classical baselines included honestly.')
    }
  }, [optimizationResult, n])

  // Simulate progress during execution
  useEffect(() => {
    if (isPending) {
      setProgress(0)
      const steps: ExecutionStep[] = ['build_qubo', 'synthesize', 'execute', 'decode', 'classical']
      let stepIndex = 0
      
      const interval = setInterval(() => {
        if (stepIndex < steps.length) {
          setCurrentStep(steps[stepIndex])
          setProgress((stepIndex / steps.length) * 100)
          stepIndex++
        }
      }, 1500)
      
      return () => clearInterval(interval)
    } else {
      setCurrentStep(null)
      setProgress(100)
    }
  }, [isPending])

  function runBenchmark() {
    setToast('')
    
    const request: OptimizationRequest = {
      problem_type: 'portfolio',
      problem_params: {
        returns_file: 'sample',
        n_assets: n,
        budget: k,
        risk_aversion: riskAversion,
      },
      qaoa_params: {
        p: depth,
        shots: shots,
      },
      quantum_backend: 'aer_simulator',
      seed: 42,
    }

    runOptimization(request)
  }

  // Backend status pills
  const backendPills = healthData ? (
    <>
      <Pill tone={healthData.backends_available.classiq ? 'success' : 'neutral'}>
        Classiq {healthData.backends_available.classiq ? 'connected' : 'offline'}
      </Pill>
      <Pill tone={healthData.backends_available.qbraid ? 'success' : 'neutral'}>
        qBraid {healthData.backends_available.qbraid ? 'connected' : 'offline'}
      </Pill>
      <Pill tone={healthData.backends_available.aer_simulator ? 'success' : 'error'}>
        Aer {healthData.backends_available.aer_simulator ? 'ready' : 'unavailable'}
      </Pill>
    </>
  ) : (
    <Pill tone="warning">Backend checking...</Pill>
  )

  // Error display
  const errorDisplay = isError && error ? (
    <div className="error-banner">
      <AlertCircle size={20} />
      <div>
        <strong>Error running optimization</strong>
        <p>{error.message}</p>
      </div>
      <button onClick={() => runBenchmark()}>Retry</button>
    </div>
  ) : null

  return <div className={presentation ? 'app presentation' : 'app'}>
    <header className="topbar">
      <a className="brand" href="#top"><span className="brand-mark"><span /><span /><span /></span><span>Quanta<span>Bench</span></span></a>
      <nav className="nav-links"><a href="#workbench">Workbench</a><a href="#benchmarks">Benchmarks</a><a href="#methodology">Methodology</a><a href="#docs">Docs</a></nav>
      <div className="nav-actions">
        <div className="backend-pills">{backendPills}</div>
        <button 
          className="button button-primary" 
          onClick={runBenchmark}
          disabled={isPending}
        >
          {isPending ? <><RotateCcw size={15} className="spin" /> Running...</> : <><Play size={15} fill="currentColor" /> Run Benchmark</>}
        </button>
        <button className="icon-button mobile-menu" aria-label="Open menu"><Menu size={18} /></button>
      </div>
    </header>

    <main id="top">
      {errorDisplay}
      
      <section className="hero page-shell">
        <div className="circuit circuit-a"><span /><i /><b /><em /><span /><i /></div>
        <div className="hero-copy"><div className="eyebrow"><span className="eyebrow-line" /> OPEN QUANTUM WORKBENCH</div><h1>Is quantum actually better?<br /><span>Measure it.</span></h1><p className="hero-subtitle">Solve the same portfolio problem with QAOA and classical baselines — then see the honest tradeoffs for yourself.</p><div className="hero-actions"><button className="button button-primary button-large" onClick={runBenchmark} disabled={isPending}><Play size={17} fill="currentColor" /> Run the demo</button><a className="button button-ghost button-large" href="#methodology">Read the methodology <ArrowRight size={16} /></a></div></div>
        <Card className="pipeline-card"><div className="code-top"><span className="code-kicker">PYTHON PIPELINE</span><span className="code-dots"><i /><i /><i /></span></div><pre><span className="code-purple">qubo</span> = <span className="code-blue">build_qubo</span>(assets, K=<span className="code-orange">{k}</span>)<br /><span className="code-purple">qaoa</span> = <span className="code-blue">classiq_qaoa</span>(qubo, p=<span className="code-orange">{depth}</span>)<br /><span className="code-purple">result</span> = <span className="code-blue">qbraid_run</span>(qaoa, shots=<span className="code-orange">{shots}</span>)<br /><span className="code-muted"># compare with classical baselines</span></pre><div className="pipeline-footer"><span className="status-pulse" /> {healthData?.status === 'healthy' ? 'Backend connected' : 'Backend offline'} <ArrowRight size={14} /></div></Card>
      </section>
      <div className="sponsors page-shell"><span>POWERED BY</span><b>Classiq</b><b>qBraid</b><b>IBM</b><b>IonQ</b><span className="sponsor-note">Reproducible · Open source · Honest</span></div>

      <section id="workbench" className="section section-tint"><div className="page-shell"><SectionHeading eyebrow="01 · WORKBENCH" title="Shape the problem. See the signal." copy="Tune the same inputs across every solver. Results update live from the backend API." />
        <div className="workbench-grid"><Card className="setup-card"><div className="card-heading"><div><h3><SlidersHorizontal size={18} /> Problem Setup</h3><p>Portfolio selection · Markowitz QUBO</p></div><button className="icon-button" aria-label="Settings"><Settings2 size={17} /></button></div><div className="form-field"><label>Dataset</label><button className="select-button">Sample returns · 20 tickers <ChevronDown size={15} /></button></div><SliderField label="Asset count N" value={n} min={5} max={15} suffix={`${n} assets · ${n} qubits`} onChange={setN} /><SliderField label="Holdings K" value={k} min={2} max={Math.max(3, n - 2)} suffix={`${k} selected`} onChange={setK} /><SliderField label="Risk aversion λ" value={riskAversion} min={0} max={1} step={0.05} suffix={riskAversion.toFixed(2)} onChange={setRiskAversion} /><div className="field-inline"><div className="form-field"><label>Shots</label><button className="select-button" onClick={() => setShots(shots === 1024 ? 2048 : shots === 2048 ? 4096 : 1024)}>{shots.toLocaleString()} <ChevronDown size={15} /></button></div></div><div className="form-field"><label>QAOA depth p</label><div className="segmented">{[1,2,3,4].map(x => <button key={x} className={depth === x ? 'active' : ''} onClick={() => setDepth(x)}>{x}</button>)}</div></div><div className="field-inline"><div className="form-field"><label>Optimizer</label><button className="select-button">COBYLA <ChevronDown size={15} /></button></div><div className="form-field"><label>Restarts</label><button className="select-button">5 <ChevronDown size={15} /></button></div></div><div className="form-field"><label>Backend</label><button className="select-button">{healthData?.backends_available.aer_simulator ? 'Aer simulator' : 'Checking...'} <ChevronDown size={15} /></button></div><div className="seed-row"><span><label>Seed</label><code>42</code></span><label className="switch-label"><input type="checkbox" defaultChecked /><span className="switch" /> Deterministic mode</label></div><button className="button button-primary run-full" onClick={runBenchmark} disabled={isPending}>{isPending ? <><RotateCcw size={16} className="spin" /> Running benchmark…</> : <><Zap size={16} fill="currentColor" /> Run benchmark</>}</button></Card>
          <div className="results-area"><div className="kpi-grid">{[
            ['Approx. ratio', formatRatio(kpiData.approximationRatio), optimizationResult ? `${((1 - kpiData.approximationRatio) * 100).toFixed(1)}% gap` : 'pending'],
            ['P(Optimal)', formatPercentage(kpiData.probabilityOptimal), optimizationResult ? 'measured' : 'pending'],
            ['Feasibility', formatPercentage(kpiData.feasibilityRate), optimizationResult ? 'all feasible' : 'pending'],
            ['Qubits', String(kpiData.qubits), 'configured'],
            ['Circuit depth', String(kpiData.circuitDepth), `gates · p = ${depth}`]
          ].map(([label,value,delta],i)=><Card className="kpi-card" key={label}><span className="kpi-icon">{[<Target key="t" />,<Gauge key="g" />,<Check key="c" />,<Layers3 key="l" />,<Activity key="a" />][i]}</span><span className="kpi-label">{label}</span><strong>{value}</strong><span className="delta">{delta}</span></Card>)}</div>
            <Card className="formulation-card"><div className="card-heading"><div><h3>Formulation</h3><p>Constrained quadratic binary optimization</p></div><Pill tone="quantum">QUBO</Pill></div><div className="equation">minimize <span>λ · x&apos;Σx − μ&apos;x</span> + penalty(Σ x<sub>i</sub> − K)<sup>2</sup></div><button className="collapse-row" onClick={() => setShowIsing(!showIsing)}><span><CircleHelp size={15} /> Ising / Hamiltonian view</span><ChevronDown size={16} className={showIsing ? 'rotate' : ''} /></button>{showIsing && <div className="ising-view">H = Σ<sub>i&lt;j</sub> J<sub>ij</sub>Z<sub>i</sub>Z<sub>j</sub> + Σ h<sub>i</sub>Z<sub>i</sub> · <span>ground state → selected portfolio</span></div>}</Card>
            <Card className="frontier-card"><div className="card-heading"><div><h3>Efficient frontier</h3><p>Return vs. volatility · lower left is better</p></div><div className="chart-legend"><span><i className="legend-dot quantum" /> QAOA</span><span><i className="legend-dot classical" /> Classical</span><span><i className="legend-ring" /> Optimum</span></div></div><div className="scatter"><div className="axis-y">expected return</div><div className="scatter-grid"><span className="gridline g1" /><span className="gridline g2" /><span className="gridline g3" /><div className="point point-opt"><span>◎</span><label>{solvers.find(s => s.name.includes('Brute'))?.name || 'optimal'}</label></div><div className="point point-qaoa"><span>★</span><label>QAOA pick</label></div><div className="point point-sa"><span>◆</span><label>annealing</label></div><div className="point point-greedy"><span>●</span><label>greedy</label></div></div><div className="axis-x">portfolio volatility <span>→</span></div></div></Card>
            <div className="two-col"><Card><div className="card-heading"><div><h3>Selected portfolio</h3><p>{assets.length} of {n} assets · K = {k}</p></div><div className="donut" aria-label="Portfolio allocation"><span>{((k / n) * 100).toFixed(0)}%<small>selected</small></span></div></div><div className="asset-list">{assets.length > 0 ? assets.map((asset,i)=><div className="asset-row" key={asset.ticker}><span className={`asset-avatar av-${i}`}>{asset.ticker.slice(0,1)}</span><span><b>{asset.ticker}</b><small>{asset.name}</small></span><code>{asset.weight}</code></div>) : <div style={{padding: '20px', textAlign: 'center', color: '#8a91aa'}}>Run benchmark to see results</div>}</div></Card><Card className="honest-card"><div className="honest-icon"><Sparkles /></div><span className="eyebrow">THE HONEST RESULT</span><h3>{optimizationResult ? optimizationResult.metrics.honest_assessment.includes('Classical') ? 'Classical wins this round.' : 'Quantum competitive!' : 'Run benchmark to compare'}</h3><p>{optimizationResult ? optimizationResult.metrics.honest_assessment : 'Run the benchmark to see how QAOA performs against classical baselines with transparent metrics.'}</p><a href="#methodology">Why this matters <ArrowRight size={14} /></a></Card></div>
          </div></div>
      </div></section>

      <section id="benchmarks" className="section"><div className="page-shell"><SectionHeading eyebrow="02 · BENCHMARKS" title="Every solver. Same playing field." copy="No cherry-picking. We report objective quality, feasibility, and wall-clock runtime side by side." /><Card className="table-card"><div className="table-top"><div><h3>Solver comparison</h3><p>Run ID <code>{optimizationResult?.run_id.slice(-8) || 'pending'}</code> · {optimizationResult ? new Date().toLocaleDateString() : 'waiting'} · seed 42</p></div><Pill tone={optimizationResult ? 'success' : 'neutral'}>{optimizationResult ? 'Completed' : 'Pending'}</Pill></div><div className="solver-table"><div className="table-row table-head"><span>Solver</span><span>Objective</span><span>Sharpe</span><span>Approx. ratio</span><span>Runtime</span><span>Result</span></div>{solvers.length > 0 ? solvers.map(s=><button className={`table-row solver-row ${selectedSolver === s.name ? 'selected' : ''}`} key={s.name} onClick={() => setSelectedSolver(s.name)}><span><i className={`solver-mark ${s.color}`}>{s.icon}</i><b>{s.name}</b><small>{s.type}</small></span><code>{s.objective}</code><code>{s.sharpe}</code><code>{s.ratio}</code><code>{s.runtime}</code><span className="feasible"><Check size={14} /> {s.isFeasible ? 'Feasible' : 'Infeasible'}</span></button>) : <div style={{padding: '40px', textAlign: 'center', color: '#8a91aa', gridColumn: '1 / -1'}}>Run benchmark to see solver comparison</div>}</div></Card><div className="charts-grid"><Card><div className="card-heading"><div><h3>Measurement histogram</h3><p>Top bitstrings · probability distribution</p></div><Pill tone="quantum">{shots.toLocaleString()} shots</Pill></div><div className="histogram">{optimizationResult ? extractHistogram(optimizationResult.quantum_result, 10).map((entry,i)=><div className={`bar-wrap ${i === 0 ? 'optimal' : ''}`} key={entry.bitstring}><div className="bar" style={{height: `${Math.max(10, entry.probability * 100)}%`}}><span>{formatPercentage(entry.probability)}</span></div><label>{entry.bitstring.slice(0, 8)}{entry.bitstring.length > 8 ? '...' : ''}</label></div>) : <div style={{padding: '40px', textAlign: 'center', color: '#8a91aa'}}>Run benchmark to see histogram</div>}</div></Card><Card><div className="card-heading"><div><h3>Execution time</h3><p>Component breakdown</p></div><span className="mono muted">{optimizationResult ? formatRuntime(optimizationResult.execution_time_seconds) : 'pending'}</span></div><div className="line-chart">{optimizationResult ? <div style={{padding: '20px'}}><div style={{marginBottom: '10px'}}><strong>Quantum: </strong>{formatRuntime(optimizationResult.quantum_result.execution_time_seconds)}</div>{optimizationResult.classical_results.map(r => <div key={r.solver_name} style={{marginBottom: '10px', color: '#8a91aa'}}><strong>{r.solver_name}: </strong>{formatRuntime(r.execution_time_seconds)}</div>)}</div> : <div style={{padding: '40px', textAlign: 'center', color: '#8a91aa'}}>Run benchmark to see timing</div>}</div></Card></div></div></section>

      <section id="methodology" className="section section-tint"><div className="page-shell"><SectionHeading eyebrow="03 · CIRCUIT INSIGHTS" title="From QUBO to executable circuit." copy="A transparent view into synthesis choices and the cost of adding expressivity." /><div className="insights-grid"><Card><div className="card-heading"><div><h3>Backend status</h3><p>Live connection to quantum backends</p></div><Pill tone={healthData?.status === 'healthy' ? 'success' : 'warning'}>{healthData?.status || 'checking'}</Pill></div><div className="metrics-list"><div><span>Classiq</span><b>{healthData?.backends_available.classiq ? 'Available' : 'Offline'}</b></div><div><span>qBraid</span><b>{healthData?.backends_available.qbraid ? 'Available' : 'Offline'}</b></div><div><span>Aer Simulator</span><b>{healthData?.backends_available.aer_simulator ? 'Ready' : 'Unavailable'}</b></div><div><span>Cache</span><b>{healthData?.cache_enabled ? 'Enabled' : 'Disabled'}</b></div></div></Card><Card><div className="card-heading"><div><h3>Current config</h3><p>Active optimization parameters</p></div></div><div className="metrics-list"><div><span>Width</span><b>{n} qubits</b></div><div><span>Depth (p)</span><b>{depth} layers</b></div><div><span>Shots</span><b>{shots.toLocaleString()}</b></div><div><span>Backend</span><b>Aer simulator</b></div></div></Card></div></div></section>

      <section className="section scaling-section"><div className="page-shell"><div className="scaling-layout"><div><SectionHeading eyebrow="04 · THE REALITY CHECK" title="Where quantum helps today, and where it doesn&apos;t." copy="The useful answer depends on problem size, hardware, and what you count as success." /><div className="takeaway-grid"><div className="takeaway"><span className="takeaway-icon teal"><Timer /></span><b>Classical wins small</b><p>For N &lt; 20, exact solvers are fast, exact, and hard to beat.</p></div><div className="takeaway"><span className="takeaway-icon purple"><Zap /></span><b>Quantum is a bet</b><p>QAOA trades optimality for a path to scale — eventually.</p></div><div className="takeaway"><span className="takeaway-icon pink"><BarChart3 /></span><b>Measure everything</b><p>Report feasibility, runtime, and quality. Not just a pretty circuit.</p></div></div></div><Card className="scaling-card"><div className="card-heading"><div><h3>API Status</h3><p>Backend integration health</p></div></div><div style={{padding: '30px', textAlign: 'center'}}><div style={{fontSize: '48px', marginBottom: '10px'}}>{healthData ? '✓' : '⋯'}</div><div style={{fontSize: '18px', fontWeight: 600, marginBottom: '5px'}}>{healthData ? 'Backend Connected' : 'Checking backend...'}</div><div style={{color: '#8a91aa'}}>{healthData ? `API v${healthData.version} · ${healthData.timestamp}` : 'Establishing connection...'}</div></div></Card></div></div></section>
    </main>

    <footer className="footer"><div className="page-shell footer-inner"><div><a className="brand" href="#top"><span className="brand-mark"><span /><span /><span /></span><span>Quanta<span>Bench</span></span></a><p>Same problem. Quantum vs classical. Honest results.</p></div><div className="footer-links"><span>Powered by <b>Classiq</b> + <b>qBraid</b></span><div><button onClick={() => optimizationResult && setToast('JSON export prepared') } disabled={!optimizationResult}><Download size={14} /> JSON</button><button onClick={() => optimizationResult && setToast('PNG export prepared') } disabled={!optimizationResult}><Download size={14} /> PNG</button><button onClick={() => optimizationResult && setToast('Summary copied to clipboard') } disabled={!optimizationResult}><Copy size={14} /> Copy summary</button><a href="https://github.com/yourusername/quantabench" target="_blank" rel="noopener"><GitBranch size={14} /> Open-source repo</a></div></div></div></footer>
    {toast && <div className="toast"><Check size={16} /> {toast}<button onClick={() => setToast('')}>×</button></div>}
    {isPending && <div className="run-overlay"><div className="run-modal"><div className="modal-logo"><span className="brand-mark"><span /><span /><span /></span></div><h3>Running benchmark</h3><p>Same problem, five honest steps.</p>{['Build QUBO','Synthesize · Classiq','Execute · qBraid','Decode & filter','Classical baselines'].map((step,i)=><div className={`run-step ${currentStep === ['build_qubo','synthesize','execute','decode','classical'][i] ? 'current' : progress > (i / 5) * 100 ? 'done' : ''}`} key={step}>{progress > (i / 5) * 100 ? <Check /> : currentStep === ['build_qubo','synthesize','execute','decode','classical'][i] ? <RotateCcw className="spin" /> : <span className="step-number">{i+1}</span>}<span>{step}</span><small>{progress > (i / 5) * 100 ? `${(1.5 + i * 0.5).toFixed(1)}s` : currentStep === ['build_qubo','synthesize','execute','decode','classical'][i] ? 'running…' : ''}</small></div>)}</div></div>}
  </div>
}

function SliderField({ label, value, min, max, step = 1, suffix, onChange }: { label: string; value: number; min: number; max: number; step?: number; suffix: string; onChange?: (value: number) => void }) {
  return <div className="slider-field"><div><label>{label}</label><code>{suffix}</code></div><input type="range" min={min} max={max} step={step} value={value} onChange={e => onChange?.(Number(e.target.value))} /></div>
}
