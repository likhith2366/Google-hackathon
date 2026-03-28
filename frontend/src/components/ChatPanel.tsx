import { useEffect, useRef, useState, type FormEvent } from 'react'
import ReactMarkdown from 'react-markdown'

export type ChatMessage = {
  role: 'user' | 'advocate'
  text: string
}

interface Props {
  messages: ChatMessage[]
  onSend: (message: string) => void
  sending: boolean
}

export default function ChatPanel({ messages, onSend, sending }: Props) {
  const [input,     setInput]     = useState('')
  const bottomRef                 = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, sending])

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    const msg = input.trim()
    if (msg && !sending) {
      onSend(msg)
      setInput('')
    }
  }

  return (
    <div className="chat-panel">
      <div className="chat-header">
        <span className="chat-eyebrow">Tenant Advocate</span>
        <span className="chat-label">Ask anything</span>
      </div>

      <div className="chat-messages">
        {messages.length === 0 && (
          <p className="chat-empty">
            Ask about your rights, what violations mean, how to negotiate
            your lease, or anything else about this building.
          </p>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`chat-bubble ${msg.role === 'user' ? 'bubble-user' : 'bubble-advocate'}`}>
            {msg.role === 'advocate' && (
              <span className="bubble-label">Advocate</span>
            )}
            <div className="bubble-text">
              {msg.role === 'advocate'
                ? <ReactMarkdown>{msg.text}</ReactMarkdown>
                : msg.text
              }
            </div>
          </div>
        ))}

        {sending && (
          <div className="chat-bubble bubble-advocate">
            <span className="bubble-label">Advocate</span>
            <div className="typing-indicator">
              <span /><span /><span />
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <form className="chat-input-row" onSubmit={handleSubmit}>
        <input
          type="text"
          className="chat-input"
          placeholder="Ask a follow-up question…"
          value={input}
          onChange={e => setInput(e.target.value)}
          disabled={sending}
        />
        <button type="submit" className="chat-send-btn" disabled={sending || !input.trim()}>
          Send
        </button>
      </form>
    </div>
  )
}
