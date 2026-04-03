'use client'

import { useState } from 'react'
import { Copy, Check, Code2, Lock, Layers, AlertTriangle, Brain, Shield, Zap, ChevronDown, ChevronUp, XCircle, CheckCircle2 } from 'lucide-react'

interface AIAnalysis {
  accepted: boolean
  category: string
  provider?: string | null
  summary: string
  html_evidence: string[]
  rejection_reason?: string | null
}

interface AuthComponent {
  html_snippet: string
  component_type: string
  purpose: string
  selector?: string
  confidence: number
  ai_analysis?: AIAnalysis | null
}

interface AuthMethod {
  method_type: string
  provider?: string
  detected_by: string
}

interface TechStack {
  framework?: string
  auth_library?: string
  backend?: string
  confidence: number
  evidence: string[]
}

interface SecurityAnalysis {
  https_enabled: boolean
  password_requirements?: string
  two_factor_available: boolean
  security_notes: string[]
  score: number
}

interface AnalysisResult {
  url: string
  components_found: boolean
  components: AuthComponent[]
  auth_methods: AuthMethod[]
  detected_stack: TechStack
  security: SecurityAnalysis
  overall_confidence: number
  timestamp: string
}

interface ResultsDisplayProps {
  result: AnalysisResult
  onCopyHTML: (html: string) => void
}

const TYPE_BADGE: Record<string, string> = {
  login_form:           'bg-blue-900/50 text-blue-300 border-blue-700',
  signup_form:          'bg-indigo-900/50 text-indigo-300 border-indigo-700',
  password_input:       'bg-red-900/40 text-red-300 border-red-800',
  username_email_input: 'bg-orange-900/40 text-orange-300 border-orange-800',
  oauth_button:         'bg-purple-900/50 text-purple-300 border-purple-700',
  login_button:         'bg-green-900/40 text-green-300 border-green-800',
  signup_button:        'bg-teal-900/40 text-teal-300 border-teal-800',
  submit_button:        'bg-gray-800 text-gray-300 border-gray-700',
}

const TYPE_LABEL: Record<string, string> = {
  login_form:           'Login Form',
  signup_form:          'Sign-up Form',
  password_input:       'Password Input',
  username_email_input: 'Email / Username Input',
  oauth_button:         'OAuth Button',
  login_button:         'Login Button',
  signup_button:        'Sign-up Button',
  submit_button:        'Submit Button',
}

function ComponentCard({
  component, idx, onCopy, copied,
}: {
  component: AuthComponent
  idx: number
  onCopy: (h: string, i: number) => void
  copied: number | null
}) {
  const [expanded, setExpanded] = useState(false)
  const ai = component.ai_analysis
  const typeLabel = TYPE_LABEL[component.component_type] ?? component.component_type.replace(/_/g, ' ')
  const badgeColor = TYPE_BADGE[component.component_type] ?? 'bg-gray-800 text-gray-300 border-gray-700'

  // Show first 300 chars of snippet inline, full on expand
  const snippet = component.html_snippet
  const previewSnippet = snippet.length > 300 ? snippet.slice(0, 300) + '…' : snippet

  return (
    <div className="bg-gray-800 border border-gray-700 rounded-xl overflow-hidden">
      {/* Header row */}
      <div className="flex items-start justify-between gap-3 p-4">
        <div className="flex items-start gap-3 flex-1 min-w-0">
          <span className={`mt-0.5 px-2 py-0.5 rounded text-xs font-medium border whitespace-nowrap flex-shrink-0 ${badgeColor}`}>
            {typeLabel}
          </span>
          <div className="min-w-0">
            <p className="text-sm text-gray-200">{component.purpose}</p>
            {ai?.provider && (
              <span className="text-xs text-purple-400 mt-0.5 block">Provider: {ai.provider}</span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          <span className="text-xs text-gray-500">{(component.confidence * 100).toFixed(0)}%</span>
          <button
            onClick={() => onCopy(snippet, idx)}
            className="p-1.5 hover:bg-gray-700 rounded transition-colors"
            title="Copy HTML"
          >
            {copied === idx
              ? <Check className="w-3.5 h-3.5 text-green-400" />
              : <Copy className="w-3.5 h-3.5 text-gray-400" />}
          </button>
        </div>
      </div>

      {/* AI analysis block */}
      {ai && ai.accepted && (
        <div className="mx-4 mb-3 bg-purple-950/40 border border-purple-900/60 rounded-lg p-3">
          <div className="flex items-center gap-1.5 mb-2">
            <Brain className="w-3.5 h-3.5 text-purple-400" />
            <span className="text-xs font-semibold text-purple-300">{ai.category}</span>
          </div>
          {ai.summary && (
            <p className="text-xs text-gray-300 mb-2 leading-relaxed">{ai.summary}</p>
          )}
          {ai.html_evidence.length > 0 && (
            <ul className="space-y-1.5">
              {ai.html_evidence.map((point, pi) => (
                <li key={pi} className="flex gap-2 text-xs text-gray-400 leading-relaxed">
                  <span className="text-purple-500 font-bold flex-shrink-0 mt-0.5">{pi + 1}.</span>
                  <span>{point}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {/* HTML snippet — always visible, truncated, expand to full */}
      <div className="mx-4 mb-4">
        <div className="rounded-lg overflow-hidden border border-gray-700" style={{ background: '#0d1117' }}>
          <div className="flex items-center justify-between px-3 py-1.5 border-b border-gray-700" style={{ background: '#161b22' }}>
            <span className="text-xs text-gray-400 font-mono">HTML</span>
            <button
              onClick={() => setExpanded(!expanded)}
              className="flex items-center gap-1 text-xs text-gray-400 hover:text-gray-200 transition-colors"
            >
              {expanded ? <><ChevronUp className="w-3 h-3" /> Collapse</> : <><ChevronDown className="w-3 h-3" /> Expand</>}
            </button>
          </div>
          <pre className="text-xs font-mono p-3 overflow-x-auto leading-relaxed whitespace-pre-wrap break-all" style={{ color: '#e6edf3', background: '#0d1117' }}>
            <code>{expanded ? snippet : previewSnippet}</code>
          </pre>
        </div>
      </div>
    </div>
  )
}

function RejectedCard({ component, idx }: { component: AuthComponent; idx: number }) {
  const [expanded, setExpanded] = useState(false)
  const ai = component.ai_analysis!
  const typeLabel = TYPE_LABEL[component.component_type] ?? component.component_type.replace(/_/g, ' ')
  const snippet = component.html_snippet
  const previewSnippet = snippet.length > 200 ? snippet.slice(0, 200) + '…' : snippet

  return (
    <div className="bg-gray-900 border border-gray-700/60 rounded-xl overflow-hidden opacity-80">
      <div className="flex items-start justify-between gap-3 p-4">
        <div className="flex items-start gap-3 flex-1 min-w-0">
          <XCircle className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" />
          <div className="min-w-0">
            <p className="text-sm text-gray-400">{component.purpose}</p>
            <span className="text-xs text-gray-600">{typeLabel} · {(component.confidence * 100).toFixed(0)}% pattern confidence</span>
          </div>
        </div>
      </div>
      {ai.rejection_reason && (
        <div className="mx-4 mb-3 bg-red-950/30 border border-red-900/40 rounded-lg p-3">
          <div className="flex items-center gap-1.5 mb-1.5">
            <Brain className="w-3.5 h-3.5 text-red-400" />
            <span className="text-xs font-semibold text-red-400">Why rejected: {ai.category}</span>
          </div>
          <p className="text-xs text-gray-400 leading-relaxed">{ai.rejection_reason}</p>
        </div>
      )}
      <div className="mx-4 mb-4">
        <div className="rounded-lg overflow-hidden border border-gray-700" style={{ background: '#0d1117' }}>
          <div className="flex items-center justify-between px-3 py-1.5 border-b border-gray-700" style={{ background: '#161b22' }}>
            <span className="text-xs text-gray-500 font-mono">HTML</span>
            <button
              onClick={() => setExpanded(!expanded)}
              className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-300 transition-colors"
            >
              {expanded ? <><ChevronUp className="w-3 h-3" /> Collapse</> : <><ChevronDown className="w-3 h-3" /> Expand</>}
            </button>
          </div>
          <pre className="text-xs font-mono p-3 overflow-x-auto leading-relaxed whitespace-pre-wrap break-all" style={{ color: '#8b949e', background: '#0d1117' }}>
            <code>{expanded ? snippet : previewSnippet}</code>
          </pre>
        </div>
      </div>
    </div>
  )
}

export default function ResultsDisplay({ result, onCopyHTML }: ResultsDisplayProps) {
  const [activeTab, setActiveTab] = useState<'overview' | 'components' | 'stack' | 'security'>('components')
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null)

  const hasAI = result.components.some(c => c.ai_analysis != null)

  // Split into accepted and rejected when AI mode was used
  const accepted = hasAI
    ? result.components.filter(c => !c.ai_analysis || c.ai_analysis.accepted)
    : result.components
  const rejected = hasAI
    ? result.components.filter(c => c.ai_analysis && !c.ai_analysis.accepted)
    : []

  const handleCopy = (html: string, index: number) => {
    onCopyHTML(html)
    setCopiedIndex(index)
    setTimeout(() => setCopiedIndex(null), 2000)
  }

  const tabs = [
    { id: 'components' as const, label: `Components (${accepted.length})`, icon: Code2 },
    { id: 'overview'   as const, label: 'Overview',                        icon: Layers },
    { id: 'stack'      as const, label: 'Tech Stack',                      icon: Zap },
    { id: 'security'   as const, label: 'Security',                        icon: Lock },
  ]

  return (
    <div className="bg-gray-900 rounded-2xl border border-gray-800 shadow-xl overflow-hidden">
      {/* Header */}
      <div className="border-b border-gray-800 px-6 py-4 flex items-start justify-between">
        <div>
          <h2 className="text-lg font-bold text-white mb-0.5">Analysis Results</h2>
          <p className="text-xs text-gray-500 truncate max-w-xs">{result.url}</p>
        </div>
        <div className="flex flex-col items-end gap-1.5">
          <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${
            result.components_found ? 'bg-green-900/60 text-green-400' : 'bg-red-900/60 text-red-400'
          }`}>
            {result.components_found ? <CheckCircle2 className="w-3 h-3" /> : <AlertTriangle className="w-3 h-3" />}
            {accepted.length} component{accepted.length !== 1 ? 's' : ''} found
          </span>
          {hasAI && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-purple-900/50 text-purple-400 text-xs rounded-full">
              <Brain className="w-3 h-3" /> AI Enhanced · {rejected.length} filtered
            </span>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-800 flex overflow-x-auto">
        {tabs.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setActiveTab(id)}
            className={`flex items-center gap-2 px-5 py-3 border-b-2 transition-colors whitespace-nowrap text-sm ${
              activeTab === id
                ? 'border-blue-500 text-blue-400 font-medium'
                : 'border-transparent text-gray-500 hover:text-gray-300'
            }`}
          >
            <Icon className="w-3.5 h-3.5" />
            {label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="p-5 max-h-[700px] overflow-y-auto space-y-4">

        {/* ── Components ── */}
        {activeTab === 'components' && (
          <>
            {accepted.length === 0 ? (
              <p className="text-gray-500 text-center py-16 text-sm">No authentication components detected</p>
            ) : (
              <div className="space-y-3">
                {accepted.map((component, idx) => (
                  <ComponentCard
                    key={idx}
                    component={component}
                    idx={idx}
                    onCopy={handleCopy}
                    copied={copiedIndex}
                  />
                ))}
              </div>
            )}

            {/* AI Filtered / Rejected section — always expanded */}
            {rejected.length > 0 && (
              <div className="mt-6 border border-dashed border-gray-700 rounded-xl overflow-hidden">
                <div className="flex items-center gap-2.5 px-5 py-4 border-b border-gray-800">
                  <Brain className="w-4 h-4 text-red-400 flex-shrink-0" />
                  <div>
                    <p className="text-sm font-medium text-gray-300">
                      Additional Intelligent Filtering via AI
                    </p>
                    <p className="text-xs text-gray-500 mt-0.5">
                      {rejected.length} component{rejected.length !== 1 ? 's' : ''} detected by pattern matching but rejected by AI as likely false positives
                    </p>
                  </div>
                </div>
                <div className="px-4 pb-4 space-y-3 pt-4">
                  {rejected.map((component, idx) => (
                    <RejectedCard key={idx} component={component} idx={idx} />
                  ))}
                </div>
              </div>
            )}
          </>
        )}

        {/* ── Overview ── */}
        {activeTab === 'overview' && (
          <div className="space-y-5">
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-blue-900/20 border border-blue-900 rounded-xl p-4">
                <p className="text-xs text-blue-400 mb-1">Auth Components</p>
                <p className="text-3xl font-bold text-white">{accepted.length}</p>
                {rejected.length > 0 && (
                  <p className="text-xs text-gray-500 mt-1">{rejected.length} filtered by AI</p>
                )}
              </div>
              <div className="bg-purple-900/20 border border-purple-900 rounded-xl p-4">
                <p className="text-xs text-purple-400 mb-1">Auth Methods</p>
                <p className="text-3xl font-bold text-white">{result.auth_methods.length}</p>
              </div>
            </div>

            {result.auth_methods.length > 0 && (
              <div>
                <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Authentication Methods</h3>
                <div className="flex flex-wrap gap-2">
                  {result.auth_methods.map((method, idx) => (
                    <span key={idx} className="px-3 py-1.5 bg-gray-800 border border-gray-700 text-gray-200 rounded-lg text-xs">
                      {method.provider ? `${method.provider} — ${method.method_type.replace('_', ' ')}` : method.method_type.replace('_', ' ')}
                    </span>
                  ))}
                </div>
              </div>
            )}

            <div className="flex items-center gap-3 bg-gray-800 rounded-xl p-4">
              <Shield className={`w-5 h-5 flex-shrink-0 ${result.security.score >= 7 ? 'text-green-400' : result.security.score >= 5 ? 'text-yellow-400' : 'text-red-400'}`} />
              <div className="flex-1">
                <div className="flex justify-between mb-1.5">
                  <span className="text-xs text-gray-400">Security Score</span>
                  <span className="text-xs font-bold text-white">{result.security.score.toFixed(1)}/10</span>
                </div>
                <div className="w-full bg-gray-700 rounded-full h-1.5">
                  <div className={`h-1.5 rounded-full ${result.security.score >= 7 ? 'bg-green-500' : result.security.score >= 5 ? 'bg-yellow-500' : 'bg-red-500'}`}
                    style={{ width: `${(result.security.score / 10) * 100}%` }} />
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ── Tech Stack ── */}
        {activeTab === 'stack' && (
          <div className="space-y-3">
            <div className="bg-gray-800 rounded-xl divide-y divide-gray-700">
              {[
                { label: 'Frontend Framework',   value: result.detected_stack.framework },
                { label: 'Auth Library',          value: result.detected_stack.auth_library },
                { label: 'Backend Technology',    value: result.detected_stack.backend },
              ].map(({ label, value }) => (
                <div key={label} className="px-5 py-3.5 flex items-center justify-between">
                  <p className="text-xs text-gray-500">{label}</p>
                  <p className="text-sm font-medium text-white">{value ?? <span className="text-gray-600 font-normal">Not detected</span>}</p>
                </div>
              ))}
            </div>
            {result.detected_stack.evidence.length > 0 && (
              <div>
                <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Evidence</h4>
                <ul className="space-y-1.5">
                  {result.detected_stack.evidence.map((ev, idx) => (
                    <li key={idx} className="flex gap-2 text-xs text-gray-400 bg-gray-800 rounded-lg px-4 py-2.5">
                      <span className="text-blue-500">•</span><span>{ev}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {/* ── Security ── */}
        {activeTab === 'security' && (
          <div className="space-y-3">
            <div className="bg-gray-800 rounded-xl p-5">
              <div className="flex items-center justify-between mb-3">
                <p className="text-sm font-semibold text-gray-300">Security Score</p>
                <span className={`text-2xl font-bold ${result.security.score >= 7 ? 'text-green-400' : result.security.score >= 5 ? 'text-yellow-400' : 'text-red-400'}`}>
                  {result.security.score.toFixed(1)}<span className="text-gray-600 text-sm">/10</span>
                </span>
              </div>
              <div className="w-full bg-gray-700 rounded-full h-2">
                <div className={`h-2 rounded-full ${result.security.score >= 7 ? 'bg-green-500' : result.security.score >= 5 ? 'bg-yellow-500' : 'bg-red-500'}`}
                  style={{ width: `${(result.security.score / 10) * 100}%` }} />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className={`rounded-xl p-4 border ${result.security.https_enabled ? 'bg-green-900/20 border-green-900' : 'bg-red-900/20 border-red-900'}`}>
                <p className="text-xs text-gray-400 mb-1">HTTPS</p>
                <p className={`font-medium text-sm ${result.security.https_enabled ? 'text-green-400' : 'text-red-400'}`}>
                  {result.security.https_enabled ? '✓ Enabled' : '✗ Not enabled'}
                </p>
              </div>
              <div className={`rounded-xl p-4 border ${result.security.two_factor_available ? 'bg-green-900/20 border-green-900' : 'bg-gray-800 border-gray-700'}`}>
                <p className="text-xs text-gray-400 mb-1">2FA / MFA</p>
                <p className={`font-medium text-sm ${result.security.two_factor_available ? 'text-green-400' : 'text-gray-500'}`}>
                  {result.security.two_factor_available ? '✓ Available' : '— Not detected'}
                </p>
              </div>
            </div>
            {result.security.security_notes.length > 0 && (
              <ul className="space-y-2">
                {result.security.security_notes.map((note, idx) => (
                  <li key={idx} className="flex gap-2 text-xs text-gray-400 bg-gray-800 rounded-lg px-4 py-3">
                    <span className="text-blue-500 mt-0.5">•</span><span>{note}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
