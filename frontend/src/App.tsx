import { useEffect, useRef, useState } from 'react'
import { analyze, chat, type AnalyzeResponse, type BuildingContext } from './api'
import SearchBar from './components/SearchBar'
import SummaryCard from './components/SummaryCard'
import ChatPanel, { type ChatMessage } from './components/ChatPanel'
import './App.css'

const LS_RESULT   = 'nyc_analyze_result'
const LS_MESSAGES = 'nyc_chat_messages'

const TICKER_STEPS = [
  'Querying HPD violations database…',
  'Fetching DOB complaint records…',
  'Scanning litigation history…',
  'Generating tenant advocate report…',
]

type AppState =
  | { phase: 'idle' }
  | { phase: 'loading' }
  | { phase: 'result'; data: AnalyzeResponse; messages: ChatMessage[] }
  | { phase: 'error'; message: string }

function loadSession(): { data: AnalyzeResponse; messages: ChatMessage[] } | null {
  try {
    const raw  = localStorage.getItem(LS_RESULT)
    const msgs = localStorage.getItem(LS_MESSAGES)
    if (!raw) return null
    return {
      data:     JSON.parse(raw) as AnalyzeResponse,
      messages: msgs ? (JSON.parse(msgs) as ChatMessage[]) : [],
    }
  } catch { return null }
}

function saveSession(data: AnalyzeResponse, messages: ChatMessage[]) {
  localStorage.setItem(LS_RESULT,   JSON.stringify(data))
  localStorage.setItem(LS_MESSAGES, JSON.stringify(messages))
}

function clearSession() {
  localStorage.removeItem(LS_RESULT)
  localStorage.removeItem(LS_MESSAGES)
}

export default function App() {
  const [state,       setState]       = useState<AppState>({ phase: 'idle' })
  const [sending,     setSending]     = useState(false)
  const [tickerIndex, setTickerIndex] = useState(0)
  const tickerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    const saved = loadSession()
    if (saved) setState({ phase: 'result', data: saved.data, messages: saved.messages })
  }, [])

  useEffect(() => {
    if (state.phase === 'loading') {
      setTickerIndex(0)
      tickerRef.current = setInterval(() => {
        setTickerIndex(i => (i + 1) % TICKER_STEPS.length)
      }, 2200)
    } else {
      if (tickerRef.current) clearInterval(tickerRef.current)
    }
    return () => { if (tickerRef.current) clearInterval(tickerRef.current) }
  }, [state.phase])

  async function handleSearch(query: string) {
    setState({ phase: 'loading' })
    try {
      const data     = await analyze(query)
      const messages: ChatMessage[] = []
      saveSession(data, messages)
      setState({ phase: 'result', data, messages })
    } catch (err) {
      setState({ phase: 'error', message: (err as Error).message })
    }
  }

  async function handleChat(message: string) {
    if (state.phase !== 'result') return
    const { data, messages } = state

    const updated: ChatMessage[] = [...messages, { role: 'user', text: message }]
    setState({ phase: 'result', data, messages: updated })
    saveSession(data, updated)
    setSending(true)

    const context: BuildingContext = {
      violations: data.violations,
      complaints: data.complaints,
      litigations: data.litigations,
      risk_profile: data.risk_profile,
    }

    try {
      const res = await chat(data.session_id, message, context)
      const withReply: ChatMessage[] = [...updated, { role: 'advocate', text: res.reply }]
      setState({ phase: 'result', data, messages: withReply })
      saveSession(data, withReply)
    } catch (err) {
      const withErr: ChatMessage[] = [
        ...updated,
        { role: 'advocate', text: `Sorry, something went wrong: ${(err as Error).message}` },
      ]
      setState({ phase: 'result', data, messages: withErr })
      saveSession(data, withErr)
    } finally {
      setSending(false)
    }
  }

  function handleReset() {
    clearSession()
    setState({ phase: 'idle' })
  }

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-inner">
          <div className="brand">
            <span className="brand-eyebrow">NYC Tenant Intelligence</span>
            <span className="brand-name">BeforeYouSign</span>
          </div>
          {state.phase === 'result' && (
            <button className="reset-btn" onClick={handleReset}>New Search</button>
          )}
        </div>
      </header>

      <main className="app-main">
        {(state.phase === 'idle' || state.phase === 'loading' || state.phase === 'error') && (
          <div className="hero-section">
            <p className="hero-dateline">NYC Open Data · HPD · DOB · Housing Court</p>
            <h1 className="hero-title">Know before<br />you sign.</h1>
            <div className="hero-rule" />
            <p className="hero-sub">
              Enter any NYC address to uncover violations, complaints,
              litigation history, and receive pro-tenant guidance.
            </p>
            <SearchBar onSubmit={handleSearch} loading={state.phase === 'loading'} />

            {state.phase === 'loading' && (
              <div className="loading-ticker">
                <span className="ticker-dot" />
                {TICKER_STEPS[tickerIndex]}
              </div>
            )}

            {state.phase === 'error' && (
              <div className="error-box">
                <strong>Error:</strong> {state.message}
                <button className="retry-btn" onClick={() => setState({ phase: 'idle' })}>
                  Try again
                </button>
              </div>
            )}
          </div>
        )}

        {state.phase === 'result' && (
          <div className="result-layout">
            <SummaryCard data={state.data} />
            <ChatPanel messages={state.messages} onSend={handleChat} sending={sending} />
          </div>
        )}
      </main>
    </div>
  )
}
