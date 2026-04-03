'use client'

import { useEffect, useState, useRef } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { ArrowLeft, Download, CheckCircle, XCircle, Shield, Loader2, Check } from 'lucide-react'
import ResultsDisplay from '@/components/ResultsDisplay'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface JobStatus {
  job_id: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  progress: number
  stage: string | null
  result: any | null
  error: string | null
}

interface ProgressStep {
  stage: string
  message: string
  done: boolean
  ts: number
}

export default function ResultsPage() {
  const params = useParams()
  const router = useRouter()
  const jobId  = params.jobId as string

  const [jobStatus, setJobStatus]   = useState<JobStatus | null>(null)
  const [steps, setSteps]           = useState<ProgressStep[]>([])
  const sseRef = useRef<EventSource | null>(null)

  // SSE — step-by-step live progress
  useEffect(() => {
    if (!jobId) return
    const es = new EventSource(`${API_URL}/api/stream/${jobId}`)
    sseRef.current = es

    es.onmessage = (e) => {
      try {
        const evt = JSON.parse(e.data)
        const stage   = evt.stage   ?? evt.event ?? 'info'
        const message = evt.data?.message ?? evt.event ?? ''
        if (!message) return
        setSteps(prev => {
          // Update existing stage or add new step
          const exists = prev.findIndex(s => s.stage === stage && !s.done)
          if (exists >= 0) {
            const copy = [...prev]
            copy[exists] = { ...copy[exists], message, ts: Date.now() }
            return copy
          }
          return [...prev, { stage, message, done: false, ts: Date.now() }]
        })
        if (evt.event === 'complete' || evt.event === 'error') {
          // Mark all steps done
          setSteps(prev => prev.map(s => ({ ...s, done: true })))
          es.close()
        }
      } catch {}
    }

    es.onerror = () => es.close()
    return () => es.close()
  }, [jobId])

  // Polling for job status
  useEffect(() => {
    if (!jobId) return
    const interval = setInterval(async () => {
      try {
        const res  = await fetch(`${API_URL}/api/status/${jobId}`)
        const data = await res.json()
        setJobStatus(data)
        if (data.status === 'completed' || data.status === 'failed') {
          clearInterval(interval)
          setSteps(prev => prev.map(s => ({ ...s, done: true })))
        }
      } catch (e) { console.error(e) }
    }, 2000)
    return () => clearInterval(interval)
  }, [jobId])

  const handleCopyHTML = (html: string) => navigator.clipboard.writeText(html)

  const handleDownloadJSON = () => {
    if (!jobStatus?.result) return
    const blob = new Blob([JSON.stringify(jobStatus.result, null, 2)], { type: 'application/json' })
    Object.assign(document.createElement('a'), {
      href: URL.createObjectURL(blob),
      download: `auth-analysis-${jobId}.json`,
    }).click()
  }

  const handleDownloadHTML = () => {
    if (!jobStatus?.result?.components) return
    const components = jobStatus.result.components as any[]
    const accepted = components.filter((c: any) => !c.ai_analysis || c.ai_analysis.accepted)
    const rejected = components.filter((c: any) => c.ai_analysis && !c.ai_analysis.accepted)

    const cardHtml = (c: any, isRejected = false) => `
  <div class="card ${isRejected ? 'rejected' : ''}">
    <div class="badge">${c.component_type.replace(/_/g,' ')}</div>
    <p class="purpose">${c.purpose} · ${(c.confidence*100).toFixed(0)}% pattern confidence</p>
    ${c.ai_analysis ? `<div class="ai-box ${isRejected ? 'rejected-box' : ''}">
      <div class="ai-label">${isRejected ? '✗ Rejected — ' : ''}${c.ai_analysis.category}${c.ai_analysis.provider ? ` · ${c.ai_analysis.provider}` : ''}</div>
      ${c.ai_analysis.summary ? `<div class="ai-summary">${c.ai_analysis.summary}</div>` : ''}
      ${c.ai_analysis.html_evidence?.length ? `<ol class="evidence">${c.ai_analysis.html_evidence.map((p: string) => `<li>${p}</li>`).join('')}</ol>` : ''}
      ${isRejected && c.ai_analysis.rejection_reason ? `<div class="rejection">${c.ai_analysis.rejection_reason}</div>` : ''}
    </div>` : ''}
    <pre><code>${c.html_snippet.replace(/</g,'&lt;').replace(/>/g,'&gt;')}</code></pre>
  </div>`

    const html = `<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Auth Components – ${jobStatus.result.url}</title>
<style>
  body{font-family:system-ui,sans-serif;background:#0f0f0f;color:#e5e5e5;padding:2rem;max-width:900px;margin:0 auto}
  h1{color:#60a5fa;margin-bottom:.25rem}h2{color:#9ca3af;font-size:1rem;margin:2rem 0 1rem}
  .meta{color:#6b7280;font-size:.875rem;margin-bottom:2rem}
  .card{background:#1f2937;border:1px solid #374151;border-radius:12px;padding:1.5rem;margin-bottom:1.25rem}
  .card.rejected{background:#111;border-color:#292929;opacity:.8}
  .badge{display:inline-block;background:#312e81;color:#a5b4fc;padding:.2rem .6rem;border-radius:6px;font-size:.7rem;margin-bottom:.5rem}
  .purpose{color:#9ca3af;font-size:.8rem;margin-bottom:.75rem}
  .ai-box{background:#1e1b4b;border:1px solid #4c1d95;border-radius:8px;padding:.75rem;margin-bottom:.75rem}
  .ai-box.rejected-box{background:#1a0a0a;border-color:#450a0a}
  .ai-label{color:#c084fc;font-size:.7rem;font-weight:700;margin-bottom:.3rem}
  .ai-box.rejected-box .ai-label{color:#f87171}
  .ai-summary{color:#d1d5db;font-size:.75rem;margin-bottom:.5rem}
  .evidence{color:#9ca3af;font-size:.75rem;padding-left:1.25rem;margin:.25rem 0}
  .evidence li{margin-bottom:.25rem}
  .rejection{color:#fca5a5;font-size:.75rem;margin-top:.4rem}
  pre{background:#111827;color:#f3f4f6;padding:1rem;border-radius:6px;overflow-x:auto;font-size:.7rem;white-space:pre-wrap;word-break:break-all;margin:0}
</style></head>
<body>
  <h1>Authentication Components</h1>
  <p class="meta">Source: ${jobStatus.result.url} · Extracted ${new Date().toLocaleString()}</p>
  <h2>✓ Confirmed Auth Components (${accepted.length})</h2>
  ${accepted.map((c: any) => cardHtml(c, false)).join('')}
  ${rejected.length ? `<h2>⚠ AI-Filtered (False Positives) — ${rejected.length}</h2>${rejected.map((c: any) => cardHtml(c, true)).join('')}` : ''}
</body></html>`

    const blob = new Blob([html], { type: 'text/html' })
    Object.assign(document.createElement('a'), {
      href: URL.createObjectURL(blob),
      download: `auth-components-${jobId}.html`,
    }).click()
  }

  const isDone = jobStatus?.status === 'completed' || jobStatus?.status === 'failed'

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      {/* Header */}
      <header className="border-b border-gray-800 bg-gray-950/80 backdrop-blur-sm sticky top-0 z-10">
        <div className="container mx-auto px-6 py-3.5 flex items-center justify-between">
          <button onClick={() => router.push('/')}
            className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors text-sm">
            <ArrowLeft className="w-4 h-4" /> Back
          </button>
          <div className="flex items-center gap-2">
            <Shield className="w-5 h-5 text-blue-400" />
            <span className="font-semibold text-white text-sm">Auth Analyzer</span>
          </div>
          {jobStatus?.result ? (
            <div className="flex gap-3">
              <button onClick={handleDownloadHTML}
                className="px-4 py-2.5 bg-gray-800 hover:bg-gray-700 text-gray-200 rounded-xl text-sm font-medium flex items-center gap-2 border border-gray-600 transition-colors">
                <Download className="w-4 h-4" />
                <span>Download</span>
                <span className="text-gray-400 font-normal">HTML</span>
              </button>
              <button onClick={handleDownloadJSON}
                className="px-4 py-2.5 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-sm font-medium flex items-center gap-2 transition-colors">
                <Download className="w-4 h-4" />
                <span>Download</span>
                <span className="text-blue-200 font-normal">JSON</span>
              </button>
            </div>
          ) : <div className="w-24" />}
        </div>
      </header>

      <main className="container mx-auto px-6 py-8 max-w-5xl">
        <div className="grid grid-cols-1 lg:grid-cols-[300px_1fr] gap-6">

          {/* Left — step-by-step progress */}
          <div className="lg:sticky lg:top-24 self-start">
            <div className="bg-gray-900 border border-gray-800 rounded-2xl p-5">
              <h3 className="text-sm font-semibold text-gray-300 mb-4">Analysis Progress</h3>

              {/* Status badge */}
              {jobStatus && (
                <div className={`flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-medium mb-4 ${
                  jobStatus.status === 'completed' ? 'bg-green-900/30 text-green-400 border border-green-900' :
                  jobStatus.status === 'failed'    ? 'bg-red-900/30 text-red-400 border border-red-900' :
                  'bg-blue-900/30 text-blue-400 border border-blue-900'
                }`}>
                  {jobStatus.status === 'completed' ? <CheckCircle className="w-3.5 h-3.5" /> :
                   jobStatus.status === 'failed'    ? <XCircle className="w-3.5 h-3.5" /> :
                   <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  {jobStatus.status === 'completed' ? 'Complete' :
                   jobStatus.status === 'failed'    ? 'Failed' : 'Processing...'}
                </div>
              )}

              {/* Progress bar */}
              {!isDone && jobStatus && (
                <div className="mb-4">
                  <div className="w-full bg-gray-800 rounded-full h-1">
                    <div className="bg-blue-500 h-1 rounded-full transition-all duration-700"
                      style={{ width: `${jobStatus.progress ?? 0}%` }} />
                  </div>
                </div>
              )}

              {/* Steps list */}
              <div className="space-y-2">
                {steps.length === 0 && !isDone && (
                  <p className="text-xs text-gray-600">Waiting for events...</p>
                )}
                {steps.map((step, i) => (
                  <div key={i} className="flex gap-2.5 items-start">
                    <div className={`flex-shrink-0 w-4 h-4 rounded-full flex items-center justify-center mt-0.5 ${
                      step.done ? 'bg-green-800' : 'bg-blue-900'
                    }`}>
                      {step.done
                        ? <Check className="w-2.5 h-2.5 text-green-400" />
                        : <div className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-pulse" />}
                    </div>
                    <p className="text-xs text-gray-400 leading-relaxed">{step.message}</p>
                  </div>
                ))}
                {isDone && steps.length > 0 && (
                  <div className="flex gap-2.5 items-center mt-1">
                    <div className="flex-shrink-0 w-4 h-4 rounded-full bg-green-800 flex items-center justify-center">
                      <Check className="w-2.5 h-2.5 text-green-400" />
                    </div>
                    <p className="text-xs text-green-400 font-medium">
                      {jobStatus?.status === 'failed' ? 'Analysis failed' : 'Analysis complete'}
                    </p>
                  </div>
                )}
              </div>

              {jobStatus?.status === 'failed' && jobStatus.error && (
                <div className="mt-4 bg-red-900/20 border border-red-900 rounded-lg p-3">
                  <p className="text-xs text-red-400">{jobStatus.error}</p>
                </div>
              )}
            </div>
          </div>

          {/* Right — results */}
          <div>
            {jobStatus?.result ? (
              <ResultsDisplay result={jobStatus.result} onCopyHTML={handleCopyHTML} />
            ) : (
              <div className="bg-gray-900 border border-gray-800 rounded-2xl p-16 text-center">
                <Loader2 className="w-8 h-8 text-blue-400 animate-spin mx-auto mb-3" />
                <p className="text-gray-500 text-sm">Waiting for results...</p>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  )
}
