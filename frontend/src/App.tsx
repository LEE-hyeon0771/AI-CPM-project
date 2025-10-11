import React, { useState } from 'react'
import Tables from './components/Tables'

interface ChatResponse {
  ideal_schedule: any
  delay_table: any
  cost_summary: {
    indirect_cost: number
    ld: number
    total: number
  }
  citations: Array<{
    document: string
    page: number
    snippet: string
    score?: number
  }>
  ui: {
    tables: Array<{
      title: string
      headers: string[]
      rows: any[][]
    }>
    cards: Array<{
      title: string
      value: string
      subtitle?: string
    }>
  }
}

function App() {
  const [message, setMessage] = useState('')
  const [wbsText, setWbsText] = useState('')
  const [response, setResponse] = useState<ChatResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!message.trim()) return

    setLoading(true)
    setError('')

    try {
      const res = await fetch('http://localhost:8000/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: message,
          wbs_text: wbsText || undefined
        })
      })

      if (!res.ok) {
        throw new Error(`HTTP error! status: ${res.status}`)
      }

      const data = await res.json()
      setResponse(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
    } finally {
      setLoading(false)
    }
  }

  const setupContract = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/setup/contract', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          contract_amount: 20000000000,
          ld_rate: 0.0005,
          indirect_cost_per_day: 3000000,
          start_date: '2025-09-15',
          calendar_policy: '5d'
        })
      })

      if (!res.ok) {
        throw new Error(`HTTP error! status: ${res.status}`)
      }

      const data = await res.json()
      console.log('Contract setup:', data)
    } catch (err) {
      console.error('Contract setup error:', err)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="container mx-auto px-4 py-8">
        <header className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">
            Smart Construction Scheduling & Economic Analysis
          </h1>
          <p className="text-gray-600">
            AI-powered multi-agent system for construction project management
          </p>
        </header>

        <div className="max-w-4xl mx-auto">
          {/* Contract Setup */}
          <div className="bg-white rounded-lg shadow-md p-6 mb-6">
            <h2 className="text-xl font-semibold mb-4">Contract Setup</h2>
            <button
              onClick={setupContract}
              className="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded-md transition-colors"
            >
              Setup Sample Contract
            </button>
          </div>

          {/* Chat Interface */}
          <div className="bg-white rounded-lg shadow-md p-6 mb-6">
            <h2 className="text-xl font-semibold mb-4">Project Analysis</h2>
            
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label htmlFor="message" className="block text-sm font-medium text-gray-700 mb-2">
                  Message
                </label>
                <input
                  type="text"
                  id="message"
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  placeholder="예: 비 예보 반영해서 다시 짜줘"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label htmlFor="wbs" className="block text-sm font-medium text-gray-700 mb-2">
                  WBS (Work Breakdown Structure)
                </label>
                <textarea
                  id="wbs"
                  value={wbsText}
                  onChange={(e) => setWbsText(e.target.value)}
                  placeholder="A: 토공 5일, 선행 없음, 유형 EARTHWORK&#10;B: 콘크리트 3일, 선행 A(FS), 유형 CONCRETE"
                  rows={4}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <button
                type="submit"
                disabled={loading || !message.trim()}
                className="w-full bg-green-500 hover:bg-green-600 disabled:bg-gray-400 text-white px-4 py-2 rounded-md transition-colors"
              >
                {loading ? 'Analyzing...' : 'Run Analysis'}
              </button>
            </form>

            {error && (
              <div className="mt-4 p-4 bg-red-100 border border-red-400 text-red-700 rounded-md">
                Error: {error}
              </div>
            )}
          </div>

          {/* Results */}
          {response && (
            <div className="space-y-6">
              {/* Citations */}
              {response.citations && response.citations.length > 0 && (
                <div className="bg-white rounded-lg shadow-md p-6">
                  <h3 className="text-lg font-semibold mb-4">근거 (Citations)</h3>
                  <div className="space-y-3">
                    {response.citations.map((citation, index) => (
                      <div key={index} className="border-l-4 border-blue-500 pl-4 py-2">
                        <div className="font-medium text-sm text-gray-600">
                          {citation.document} - 페이지 {citation.page}
                          {citation.score && (
                            <span className="ml-2 text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">
                              Score: {citation.score.toFixed(2)}
                            </span>
                          )}
                        </div>
                        <div className="text-sm text-gray-800 mt-1">
                          {citation.snippet}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* UI Components */}
              <Tables tables={response.ui.tables} cards={response.ui.cards} />

              {/* Cost Summary */}
              {response.cost_summary && (
                <div className="bg-white rounded-lg shadow-md p-6">
                  <h3 className="text-lg font-semibold mb-4">비용 분석</h3>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="text-center p-4 bg-blue-50 rounded-lg">
                      <div className="text-2xl font-bold text-blue-600">
                        {response.cost_summary.total.toLocaleString()}원
                      </div>
                      <div className="text-sm text-gray-600">총 추가 비용</div>
                    </div>
                    <div className="text-center p-4 bg-green-50 rounded-lg">
                      <div className="text-2xl font-bold text-green-600">
                        {response.cost_summary.indirect_cost.toLocaleString()}원
                      </div>
                      <div className="text-sm text-gray-600">간접비</div>
                    </div>
                    <div className="text-center p-4 bg-red-50 rounded-lg">
                      <div className="text-2xl font-bold text-red-600">
                        {response.cost_summary.ld.toLocaleString()}원
                      </div>
                      <div className="text-sm text-gray-600">지연손해금</div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default App
