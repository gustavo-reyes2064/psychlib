import { useState, useRef, useEffect } from 'react'
import { Send, RotateCcw, ChevronDown } from 'lucide-react'
import { sendMessage, clearSession } from '../services/api'
import ChatMessage from '../components/ChatMessage'
import Topbar from '../components/Topbar'
import clsx from 'clsx'

const MODES = [
  { id: 'general',      label: 'General'      },
  { id: 'diagnostico',  label: 'Diagnóstico'  },
  { id: 'dsm5',         label: 'DSM-5'        },
  { id: 'farmacologia', label: 'Farmacología' },
  { id: 'caso',         label: 'Caso Clínico' },
  { id: 'psicopatologia', label: 'Psicopatología' },
]

const SESSION = 'chat-main-' + Date.now()

export default function Chat({ onMenuOpen }) {
  const [messages,  setMessages]  = useState([])
  const [input,     setInput]     = useState('')
  const [mode,      setMode]      = useState('general')
  const [loading,   setLoading]   = useState(false)
  const [tokens,    setTokens]    = useState(0)
  const endRef    = useRef(null)
  const inputRef  = useRef(null)

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])

  const send = async () => {
    if (!input.trim() || loading) return
    const text = input.trim()
    setInput('')
    setMessages(m => [...m, { role: 'user', content: text }])
    setLoading(true)
    try {
      const r = await sendMessage(text, mode, SESSION)
      const { answer, sources, tokens_used } = r.data
      setMessages(m => [...m, { role: 'assistant', content: answer, sources }])
      setTokens(t => t + (tokens_used || 0))
    } catch (e) {
      setMessages(m => [...m, {
        role: 'assistant',
        content: `Error al conectar con el servidor: ${e.message}`
      }])
    } finally {
      setLoading(false)
      inputRef.current?.focus()
    }
  }

  const reset = async () => {
    if (!confirm('¿Limpiar conversación?')) return
    await clearSession(SESSION).catch(() => {})
    setMessages([])
    setTokens(0)
  }

  const onKey = e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() } }

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      <Topbar title="Chat IA" subtitle="Consulta tu biblioteca con IA" onMenuOpen={onMenuOpen}>
        <div className="relative">
          <select
            value={mode}
            onChange={e => setMode(e.target.value)}
            className="appearance-none input py-1.5 md:py-2 pr-7 text-xs md:text-sm w-28 md:w-44 cursor-pointer"
          >
            {MODES.map(m => <option key={m.id} value={m.id}>{m.label}</option>)}
          </select>
          <ChevronDown size={12} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-textSub pointer-events-none" />
        </div>
        <button onClick={reset} className="btn-ghost p-2 rounded-xl" title="Limpiar chat">
          <RotateCcw size={16} />
        </button>
      </Topbar>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-3 md:px-8 py-4 md:py-6">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center px-4">
            <div className="w-14 h-14 md:w-16 md:h-16 rounded-2xl bg-primary/10 flex items-center justify-center mb-4">
              <Send size={22} className="text-primary" />
            </div>
            <p className="font-semibold text-textMain text-sm md:text-base">Haz tu primera pregunta</p>
            <p className="text-xs md:text-sm text-textSub mt-1 max-w-sm">
              Pregunta sobre trastornos, criterios diagnósticos, fármacos o conceptos psiquiátricos.
            </p>
            <div className="flex flex-wrap gap-2 mt-5 md:mt-6 justify-center">
              {[
                '¿Criterios del trastorno bipolar I?',
                '¿Antipsicóticos típicos vs atípicos?',
                '¿Diferencia TDM y distimia?',
              ].map(q => (
                <button key={q} onClick={() => setInput(q)}
                  className="text-[11px] md:text-xs px-3 py-1.5 md:px-4 md:py-2 bg-white border border-border rounded-pill
                             hover:border-primary/40 hover:text-primary transition-colors">
                  {q}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <>
            {messages.map((m, i) => <ChatMessage key={i} msg={m} />)}
            {loading && (
              <div className="flex gap-3 mb-5">
                <div className="w-8 h-8 rounded-xl bg-sage/15 flex items-center justify-center">
                  <div className="w-3 h-3 rounded-full bg-sage animate-pulse" />
                </div>
                <div className="bg-white border border-border rounded-2xl rounded-tl-sm px-4 md:px-5 py-3 shadow-card">
                  <div className="flex gap-1.5">
                    <span className="w-2 h-2 rounded-full bg-sage/60 animate-bounce [animation-delay:0ms]" />
                    <span className="w-2 h-2 rounded-full bg-sage/60 animate-bounce [animation-delay:150ms]" />
                    <span className="w-2 h-2 rounded-full bg-sage/60 animate-bounce [animation-delay:300ms]" />
                  </div>
                </div>
              </div>
            )}
            <div ref={endRef} />
          </>
        )}
      </div>

      {/* Input bar */}
      <div className="border-t border-border bg-white px-3 md:px-8 py-3 md:py-4">
        {tokens > 0 && (
          <p className="text-[10px] md:text-[11px] text-textSub/60 mb-1.5">{tokens.toLocaleString()} tokens</p>
        )}
        <div className="flex gap-2 md:gap-3 items-end">
          <textarea
            ref={inputRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={onKey}
            rows={1}
            placeholder="Escribe tu pregunta..."
            className="input resize-none flex-1 py-2.5 md:py-3 text-sm min-h-[40px] max-h-[120px]"
            style={{ height: 'auto' }}
            onInput={e => { e.target.style.height = 'auto'; e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px' }}
          />
          <button
            onClick={send}
            disabled={!input.trim() || loading}
            className="btn-primary h-10 w-10 md:h-12 md:w-12 rounded-xl flex items-center justify-center p-0 shrink-0"
          >
            <Send size={16} />
          </button>
        </div>
      </div>
    </div>
  )
}
