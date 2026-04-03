'use client'

import { useEffect, useState } from 'react'
import { Brain, Loader2, CheckCircle, AlertCircle } from 'lucide-react'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface ThoughtStage {
  event: string
  stage: string | null
  timestamp: string
  data: {
    message?: string
    response?: string
    full_response?: string
    error?: string
  }
}

interface ChainOfThoughtDisplayProps {
  jobId: string
}

export default function ChainOfThoughtDisplay({ jobId }: ChainOfThoughtDisplayProps) {
  const [stages, setStages] = useState<ThoughtStage[]>([])
  const [connected, setConnected] = useState(false)
  const [expandedStages, setExpandedStages] = useState<Set<number>>(new Set())

  useEffect(() => {
    if (!jobId) return

    // Connect to SSE stream
    const eventSource = new EventSource(`${API_URL}/api/stream/${jobId}`)

    eventSource.onopen = () => {
      setConnected(true)
      console.log('[SSE] Connected to stream')
    }

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        console.log('[SSE] Received event:', data)

        if (data.event === 'connected') {
          return
        }

        if (data.event === 'end') {
          eventSource.close()
          return
        }

        setStages((prev) => [...prev, data])
      } catch (error) {
        console.error('[SSE] Error parsing event:', error)
      }
    }

    eventSource.onerror = (error) => {
      console.error('[SSE] Error:', error)
      setConnected(false)
      eventSource.close()
    }

    return () => {
      eventSource.close()
    }
  }, [jobId])

  const toggleStage = (index: number) => {
    const newExpanded = new Set(expandedStages)
    if (newExpanded.has(index)) {
      newExpanded.delete(index)
    } else {
      newExpanded.add(index)
    }
    setExpandedStages(newExpanded)
  }

  const getStageIcon = (event: string) => {
    switch (event) {
      case 'stage_start':
      case 'llm_thinking':
        return <Loader2 className="w-5 h-5 animate-spin text-blue-500" />
      case 'llm_response':
      case 'stage_complete':
        return <CheckCircle className="w-5 h-5 text-green-500" />
      case 'error':
        return <AlertCircle className="w-5 h-5 text-red-500" />
      default:
        return <Brain className="w-5 h-5 text-gray-500" />
    }
  }

  const formatStageName = (stage: string | null) => {
    if (!stage) return 'Processing'
    return stage
      .split('_')
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ')
  }

  return (
    <div className="bg-white rounded-xl shadow-lg p-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <Brain className="w-6 h-6 text-purple-600" />
          <h2 className="text-xl font-bold text-gray-900">AI Chain of Thought</h2>
        </div>
        <div className="flex items-center gap-2">
          <div
            className={`w-2 h-2 rounded-full ${
              connected ? 'bg-green-500' : 'bg-gray-300'
            }`}
          />
          <span className="text-sm text-gray-500">
            {connected ? 'Live' : 'Disconnected'}
          </span>
        </div>
      </div>

      <div className="space-y-3 max-h-[600px] overflow-y-auto pr-2">
        {stages.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            <Loader2 className="w-8 h-8 animate-spin mx-auto mb-2" />
            <p>Waiting for analysis to start...</p>
          </div>
        ) : (
          stages.map((stage, index) => (
            <div
              key={index}
              className="bg-gray-50 rounded-lg p-4 border border-gray-200 hover:border-gray-300 transition-colors"
            >
              <div className="flex items-start gap-3">
                <div className="flex-shrink-0 mt-1">{getStageIcon(stage.event)}</div>

                <div className="flex-1 min-w-0">
                  <div className="mb-2">
                    <h3 className="font-medium text-gray-900">
                      {formatStageName(stage.stage)}
                    </h3>
                  </div>

                  {stage.data.message && (
                    <p className="text-sm text-gray-600 mb-2">{stage.data.message}</p>
                  )}

                  {stage.data.response && (
                    <div className="mt-2">
                      <button
                        onClick={() => toggleStage(index)}
                        className="text-sm text-blue-600 hover:text-blue-700 mb-2"
                      >
                        {expandedStages.has(index) ? '▼ Hide' : '▶ Show'} AI Response
                      </button>

                      {expandedStages.has(index) && (
                        <div className="bg-white border border-gray-200 rounded p-3 mt-2">
                          <pre className="text-xs whitespace-pre-wrap font-mono text-gray-700 overflow-x-auto">
                            {stage.data.full_response || stage.data.response}
                          </pre>
                        </div>
                      )}
                    </div>
                  )}

                  {stage.data.error && (
                    <div className="mt-2 p-3 bg-red-50 border border-red-200 rounded">
                      <p className="text-sm text-red-700">{stage.data.error}</p>
                    </div>
                  )}

                  {stage.event === 'progress' && (
                    <div className="text-sm text-blue-600 animate-pulse">
                      {stage.data.message}
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
