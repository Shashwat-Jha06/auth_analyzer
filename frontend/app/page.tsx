'use client'

import { useState } from 'react'
import { Search, Sparkles, Code2, Shield, Zap, Brain } from 'lucide-react'
import { useRouter } from 'next/navigation'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'


export default function Home() {
  const [url, setUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [aiMode, setAiMode] = useState(true)
  const router = useRouter()

  const handleAnalyze = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!url) {
      setError('Please enter a URL')
      return
    }

    setLoading(true)
    setError('')

    try {
      const response = await fetch(`${API_URL}/api/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url, mode: 'deep', ai_mode: aiMode }),
      })

      if (!response.ok) throw new Error('Failed to start analysis')

      const data = await response.json()
      router.push(`/results/${data.job_id}`)
    } catch (err) {
      setError('Failed to start analysis. Please try again.')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      {/* Header */}
      <header className="border-b border-gray-800 bg-gray-950/80 backdrop-blur-sm sticky top-0 z-10">
        <div className="container mx-auto px-6 py-4 flex items-center gap-3">
          <Shield className="w-7 h-7 text-blue-400" />
          <h1 className="text-xl font-bold text-white">Auth Analyzer</h1>
        </div>
      </header>

      <main className="container mx-auto px-6 py-14 max-w-4xl">
        {/* Hero */}
        <div className="text-center mb-12">
          <h2 className="text-5xl font-bold mb-4 bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
            Authentication Component Analyzer
          </h2>
          <p className="text-lg text-gray-400 max-w-2xl mx-auto">
            Scan any website and extract all authentication components — login forms, OAuth buttons,
            SSO, passkeys, and more. Powered by Browserless cloud browsing.
          </p>
        </div>

        {/* URL Input */}
        <div className="bg-gray-900 rounded-2xl border border-gray-800 p-8 mb-10 shadow-xl">
          <form onSubmit={handleAnalyze} className="space-y-5">
            <div>
              <label htmlFor="url" className="block text-sm font-medium text-gray-300 mb-2">
                Website URL
              </label>
              <div className="flex gap-3">
                <input
                  id="url"
                  type="url"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  placeholder="https://example.com/login"
                  className="flex-1 px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none text-white placeholder-gray-500"
                  disabled={loading}
                />
                <button
                  type="submit"
                  disabled={loading}
                  className="px-8 py-3 bg-blue-600 hover:bg-blue-500 text-white rounded-lg font-medium disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2 whitespace-nowrap"
                >
                  {loading ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      Analyzing...
                    </>
                  ) : (
                    <>
                      <Search className="w-4 h-4" />
                      Analyze
                    </>
                  )}
                </button>
              </div>
              {error && <p className="mt-2 text-red-400 text-sm">{error}</p>}
            </div>

            {/* AI Mode Toggle */}
            <div className="flex items-center justify-between bg-gray-800 rounded-xl px-5 py-4 border border-gray-700">
              <div className="flex items-center gap-3">
                <Brain className={`w-5 h-5 ${aiMode ? 'text-purple-400' : 'text-gray-500'}`} />
                <div>
                  <p className="font-medium text-sm text-white">
                    {aiMode ? 'AI Enhanced Mode' : 'Standard Mode'}
                  </p>
                  <p className="text-xs text-gray-400 mt-0.5">
                    {aiMode
                      ? 'Groq (Llama 3.3 70B) explains each component — why it\'s auth-related, category & provider'
                      : 'Fast programmatic extraction — no AI calls, results in ~10s'}
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setAiMode(!aiMode)}
                className={`relative inline-flex h-7 w-12 items-center rounded-full transition-colors focus:outline-none ${
                  aiMode ? 'bg-purple-600' : 'bg-gray-600'
                }`}
              >
                <span
                  className={`inline-block h-5 w-5 transform rounded-full bg-white shadow transition-transform ${
                    aiMode ? 'translate-x-6' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>
          </form>
        </div>

        {/* Quick Examples — 5 sites, single row */}
        <div className="mb-10">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">URLs to try</p>
          <div className="grid grid-cols-5 gap-2">
            {[
              { name: 'GitLab',     url: 'https://gitlab.com/users/sign_in',    label: 'OAuth · SSO · Email' },
              { name: 'GitHub',     url: 'https://github.com/login',             label: 'OAuth · Passkey · SSO' },
              { name: 'WordPress',  url: 'https://wordpress.com/log-in',         label: 'Email · OAuth' },
              { name: 'Notion',     url: 'https://www.notion.so/login',          label: 'Email · Google · SSO' },
              { name: 'Shopify',    url: 'https://accounts.shopify.com/lookup',  label: 'Email · Social' },
            ].map(({ name, url: exUrl, label }) => (
              <button
                key={name}
                onClick={() => setUrl(exUrl)}
                className="text-left bg-gray-900 border border-gray-800 hover:border-blue-600 rounded-xl px-3 py-3 transition-colors group"
              >
                <p className="font-semibold text-white text-sm mb-1 group-hover:text-blue-400 transition-colors">{name}</p>
                <p className="text-sm text-gray-400 font-mono truncate mb-1">{exUrl}</p>
                <p className="text-xs text-gray-600">{label}</p>
              </button>
            ))}
          </div>
        </div>

        {/* Feature pills */}
        <div className="grid grid-cols-3 gap-4">
          {[
            { icon: Zap,      label: 'Cloud Browser',  desc: 'Full JS rendering via Browserless',      color: 'text-yellow-400' },
            { icon: Code2,    label: 'Deep Extraction', desc: 'Forms, OAuth, SSO, passkeys & more',     color: 'text-green-400' },
            { icon: Sparkles, label: 'AI Analysis',     desc: 'Per-component AI filtering & evidence',  color: 'text-purple-400' },
          ].map(({ icon: Icon, label, desc, color }) => (
            <div key={label} className="bg-gray-900 border border-gray-800 rounded-xl p-4">
              <Icon className={`w-5 h-5 ${color} mb-2.5`} />
              <p className="font-semibold text-white text-sm mb-1">{label}</p>
              <p className="text-xs text-gray-500">{desc}</p>
            </div>
          ))}
        </div>
      </main>

      <footer className="border-t border-gray-800 mt-20">
        <div className="container mx-auto px-6 py-6 text-center text-gray-600 text-sm">
          Built with Next.js · FastAPI · Browserless · Groq
        </div>
      </footer>
    </div>
  )
}
