import { useState, useEffect, useRef } from 'react'
import { GraduationCap, ChevronLeft, RotateCcw, Trash2, Sparkles, CheckCircle, XCircle, Clock, BookOpen, Filter } from 'lucide-react'
import { generateExam, listExams, getExam, deleteExam, listDocuments } from '../services/api'
import Topbar from '../components/Topbar'
import clsx from 'clsx'

const DIFFICULTY_COLORS = {
  basico:     'bg-success/10 text-success',
  intermedio: 'bg-warning/10 text-warning',
  avanzado:   'bg-danger/10 text-danger',
}

const TOPICS = [
  'Trastorno Depresivo Mayor',
  'Trastorno Bipolar I y II',
  'Esquizofrenia y otros trastornos psicóticos',
  'Trastornos de Ansiedad',
  'Psicofarmacología: antidepresivos',
  'Psicofarmacología: antipsicóticos',
  'Trastornos de personalidad',
  'Trastornos del neurodesarrollo',
  'Trastornos relacionados con sustancias',
  'Emergencias psiquiátricas',
]

export default function Exam({ onMenuOpen }) {
  const [exams,      setExams]      = useState([])
  const [activeExam, setActiveExam] = useState(null)
  const [current,    setCurrent]    = useState(0)
  const [selected,   setSelected]   = useState(null)
  const [answered,   setAnswered]   = useState({})
  const [showResult, setShowResult] = useState(false)
  const [topic,      setTopic]      = useState('')
  const [count,      setCount]      = useState(10)
  const [loading,    setLoading]    = useState(false)
  const [view,       setView]       = useState('menu')
  const [timer,      setTimer]      = useState(0)
  const [timerActive, setTimerActive] = useState(false)
  const [docs,       setDocs]       = useState([])
  const [selDoc,     setSelDoc]     = useState('')
  const [pageFrom,   setPageFrom]   = useState('')
  const [pageTo,     setPageTo]     = useState('')
  const [showFilter, setShowFilter] = useState(false)
  const countRef = useRef(10)

  const updateCount = (val) => {
    setCount(val)
    countRef.current = val
  }

  useEffect(() => {
    listExams().then(r => setExams(r.data.exams || [])).catch(() => {})
    listDocuments().then(r => setDocs(r.data.documents || r.data || [])).catch(() => {})
  }, [])

  useEffect(() => {
    if (!timerActive) return
    const id = setInterval(() => setTimer(t => t + 1), 1000)
    return () => clearInterval(id)
  }, [timerActive])

  const fmtTime = s => `${Math.floor(s/60).toString().padStart(2,'0')}:${(s%60).toString().padStart(2,'0')}`

  const generate = async (t) => {
    const text = t || topic
    if (!text.trim()) return
    setLoading(true)
    try {
      const docIds = selDoc ? [selDoc] : null
      const pFrom = pageFrom ? parseInt(pageFrom) : null
      const pTo = pageTo ? parseInt(pageTo) : null
      const r = await generateExam(text, countRef.current, docIds, pFrom, pTo)
      setActiveExam(r.data)
      setCurrent(0)
      setSelected(null)
      setAnswered({})
      setShowResult(false)
      setTimer(0)
      setTimerActive(true)
      setView('exam')
      setExams(e => [{ id: r.data.id, topic: r.data.topic, total: r.data.total }, ...e])
    } catch (e) {
      alert('Error: ' + (e.response?.data?.detail || e.message))
    } finally {
      setLoading(false)
    }
  }

  const openExam = async (id) => {
    setLoading(true)
    try {
      const r = await getExam(id)
      setActiveExam(r.data)
      setCurrent(0)
      setSelected(null)
      setAnswered({})
      setShowResult(false)
      setTimer(0)
      setTimerActive(true)
      setView('exam')
    } catch (e) {
      alert('Error: ' + e.message)
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (id) => {
    if (!confirm('¿Eliminar este examen?')) return
    await deleteExam(id).catch(() => {})
    setExams(e => e.filter(x => x.id !== id))
  }

  const answer = (optionIdx) => {
    if (answered[current] !== undefined) return
    setSelected(optionIdx)
    setAnswered(a => ({ ...a, [current]: optionIdx }))
  }

  const nextQ = () => {
    if (current < activeExam.questions.length - 1) {
      setCurrent(c => c + 1)
      setSelected(answered[current + 1] ?? null)
    }
  }

  const prevQ = () => {
    if (current > 0) {
      setCurrent(c => c - 1)
      setSelected(answered[current - 1] ?? null)
    }
  }

  const finish = () => {
    setTimerActive(false)
    setShowResult(true)
  }

  const q = activeExam?.questions?.[current]
  const total = activeExam?.questions?.length || 0
  const answeredCount = Object.keys(answered).length

  const calcScore = () => {
    if (!activeExam) return { correct: 0, total: 0 }
    let correct = 0
    activeExam.questions.forEach((q, i) => {
      if (answered[i] === q.correct) correct++
    })
    return { correct, total: activeExam.questions.length }
  }

  // ── Result view ──────────────────────────────────────────
  if (view === 'exam' && activeExam && showResult) {
    const { correct, total } = calcScore()
    const pct = Math.round((correct / total) * 100)
    return (
      <div className="flex-1 flex flex-col overflow-hidden">
        <Topbar title="Resultado" subtitle={activeExam.topic} onMenuOpen={onMenuOpen}>
          <button onClick={() => setView('menu')} className="btn-secondary text-xs md:text-sm flex items-center gap-1.5">
            <ChevronLeft size={14} />
            <span className="hidden sm:inline">Volver</span>
          </button>
        </Topbar>
        <div className="flex-1 overflow-y-auto px-4 md:px-8 py-6 md:py-8">
          <div className="max-w-2xl mx-auto">
            <div className={clsx(
              'card text-center py-8 mb-6 border-2',
              pct >= 70 ? 'bg-success/5 border-success/20' : pct >= 50 ? 'bg-warning/5 border-warning/20' : 'bg-danger/5 border-danger/20'
            )}>
              <p className={clsx('text-4xl md:text-5xl font-bold mb-2',
                pct >= 70 ? 'text-success' : pct >= 50 ? 'text-warning' : 'text-danger'
              )}>{pct}%</p>
              <p className="text-base md:text-lg text-textMain font-medium">{correct} de {total} correctas</p>
              <p className="text-xs md:text-sm text-textSub mt-1">Tiempo: {fmtTime(timer)}</p>
              <p className="text-xs md:text-sm text-textSub mt-3 font-medium">
                {pct >= 90 ? 'Excelente!' : pct >= 70 ? 'Buen trabajo!' : pct >= 50 ? 'Puedes mejorar' : 'Necesitas repasar'}
              </p>
            </div>

            <h3 className="font-semibold text-textMain mb-4 text-sm md:text-base">Revisión de respuestas</h3>
            <div className="space-y-3 md:space-y-4">
              {activeExam.questions.map((q, i) => {
                const userAns = answered[i]
                const isCorrect = userAns === q.correct
                return (
                  <div key={i} className={clsx('card !p-4 border-l-4', isCorrect ? 'border-l-success' : 'border-l-danger')}>
                    <div className="flex items-start gap-2 mb-2">
                      {isCorrect
                        ? <CheckCircle size={16} className="text-success mt-0.5 shrink-0" />
                        : <XCircle size={16} className="text-danger mt-0.5 shrink-0" />}
                      <p className="text-xs md:text-sm font-medium text-textMain">{i + 1}. {q.question}</p>
                    </div>
                    <div className="ml-6 space-y-1">
                      {q.options.map((opt, j) => (
                        <div key={j} className={clsx('text-xs md:text-sm px-2 py-1 rounded-lg',
                          j === q.correct ? 'bg-success/10 text-success font-medium' :
                          j === userAns && j !== q.correct ? 'bg-danger/10 text-danger line-through' :
                          'text-textSub')}>
                          {String.fromCharCode(65 + j)}) {opt}
                        </div>
                      ))}
                    </div>
                    <p className="ml-6 mt-2 text-[11px] md:text-xs text-textSub bg-bg rounded-lg px-3 py-2">
                      {q.explanation}
                    </p>
                  </div>
                )
              })}
            </div>

            <div className="flex gap-3 justify-center mt-6">
              <button onClick={() => { setCurrent(0); setSelected(null); setAnswered({}); setShowResult(false); setTimer(0); setTimerActive(true) }}
                className="btn-secondary text-sm flex items-center gap-2">
                <RotateCcw size={14} /> Repetir
              </button>
              <button onClick={() => setView('menu')} className="btn-primary text-sm">Nuevo examen</button>
            </div>
          </div>
        </div>
      </div>
    )
  }

  // ── Exam active view ──────────────────────────────────────
  if (view === 'exam' && activeExam) {
    return (
      <div className="flex-1 flex flex-col overflow-hidden">
        <Topbar title="Examen" subtitle={activeExam.topic} onMenuOpen={onMenuOpen}>
          <div className="flex items-center gap-2 md:gap-3">
            <span className="flex items-center gap-1 text-xs md:text-sm text-textSub">
              <Clock size={13} />
              {fmtTime(timer)}
            </span>
            <button onClick={() => setView('menu')} className="btn-secondary text-xs flex items-center gap-1">
              <ChevronLeft size={13} />
              <span className="hidden sm:inline">Salir</span>
            </button>
          </div>
        </Topbar>

        <div className="flex-1 overflow-y-auto px-4 md:px-8 py-5 md:py-8">
          <div className="max-w-2xl mx-auto">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs md:text-sm text-textSub">Pregunta {current + 1} de {total}</span>
              <span className="text-xs md:text-sm text-textSub">{answeredCount}/{total}</span>
            </div>
            <div className="h-1.5 bg-bg rounded-pill mb-5 overflow-hidden">
              <div className="h-full bg-primary rounded-pill transition-all duration-300"
                style={{ width: `${(answeredCount / total) * 100}%` }} />
            </div>

            {q && (
              <div className="card !p-4 md:!p-6 mb-5">
                <div className="flex items-start justify-between mb-3">
                  <p className="text-sm md:text-base font-medium text-textMain pr-3">{q.question}</p>
                  <span className={clsx(
                    'text-[10px] px-2 py-0.5 rounded-pill font-medium shrink-0',
                    DIFFICULTY_COLORS[q.difficulty] || DIFFICULTY_COLORS.basico
                  )}>
                    {q.difficulty}
                  </span>
                </div>

                <div className="space-y-2">
                  {q.options.map((opt, j) => {
                    const isAnswered = answered[current] !== undefined
                    const isSelected = selected === j
                    const isCorrect = j === q.correct
                    return (
                      <button key={j}
                        onClick={() => answer(j)}
                        disabled={isAnswered}
                        className={clsx(
                          'w-full text-left px-3 md:px-4 py-2.5 md:py-3 rounded-xl border-2 text-xs md:text-sm transition-all',
                          isAnswered && isCorrect
                            ? 'border-success bg-success/10 text-success font-medium'
                            : isAnswered && isSelected && !isCorrect
                            ? 'border-danger bg-danger/10 text-danger'
                            : isSelected
                            ? 'border-primary bg-primary/5 text-primary'
                            : 'border-border hover:border-primary/30 hover:bg-bg text-textMain'
                        )}>
                        <span className="font-medium mr-1.5">{String.fromCharCode(65 + j)})</span>
                        {opt}
                      </button>
                    )
                  })}
                </div>

                {answered[current] !== undefined && (
                  <div className="mt-3 pt-3 border-t border-border">
                    <p className="text-xs md:text-sm text-textSub">
                      <span className="font-medium text-textMain">Explicación: </span>
                      {q.explanation}
                    </p>
                  </div>
                )}
              </div>
            )}

            <div className="flex items-center justify-between">
              <button onClick={prevQ} disabled={current === 0}
                className="btn-ghost px-3 py-2 rounded-xl text-xs disabled:opacity-30">
                Anterior
              </button>
              {answeredCount === total ? (
                <button onClick={finish} className="btn-primary px-6 text-sm">Ver resultados</button>
              ) : (
                <span className="text-[11px] text-textSub">{total - answeredCount} pendientes</span>
              )}
              <button onClick={nextQ} disabled={current >= total - 1}
                className="btn-ghost px-3 py-2 rounded-xl text-xs disabled:opacity-30">
                Siguiente
              </button>
            </div>

            <div className="flex flex-wrap gap-1.5 justify-center mt-5">
              {Array.from({ length: total }, (_, i) => (
                <button key={i}
                  onClick={() => { setCurrent(i); setSelected(answered[i] ?? null) }}
                  className={clsx(
                    'w-7 h-7 rounded-lg text-[10px] md:text-xs font-medium transition-all',
                    i === current ? 'bg-primary text-white' :
                    answered[i] !== undefined
                      ? answered[i] === activeExam.questions[i].correct
                        ? 'bg-success/15 text-success'
                        : 'bg-danger/15 text-danger'
                      : 'bg-bg text-textSub hover:bg-primary/10'
                  )}>
                  {i + 1}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    )
  }

  // ── Menu view ──────────────────────────────────────────────
  return (
    <div className="flex-1 overflow-y-auto">
      <Topbar title="Modo Examen" subtitle="Evalúa tu conocimiento con preguntas de IA" onMenuOpen={onMenuOpen} />

      <div className="px-4 md:px-8 py-6 md:py-8 max-w-3xl space-y-6">

        <div className="card !p-4 md:!p-6 space-y-4">
          <h2 className="font-semibold text-textMain flex items-center gap-2 text-sm md:text-base">
            <Sparkles size={18} className="text-primary" />
            Generar nuevo examen
          </h2>
          <div className="flex flex-col sm:flex-row gap-2 md:gap-3">
            <input
              value={topic}
              onChange={e => setTopic(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && generate()}
              placeholder="Ej: Farmacología de antipsicóticos..."
              className="input flex-1 py-2.5 text-sm"
            />
            <div className="flex gap-2">
              <select value={count} onChange={e => updateCount(Number(e.target.value))}
                className="input w-20 text-sm text-center">
                {[5, 10, 15, 20].map(n => <option key={n} value={n}>{n}</option>)}
              </select>
              <button onClick={() => generate()} disabled={loading || !topic.trim()} className="btn-primary px-5 flex-1 sm:flex-none">
                {loading ? (
                  <div className="w-5 h-5 rounded-full border-2 border-white border-t-transparent animate-spin" />
                ) : 'Generar'}
              </button>
            </div>
          </div>

          <div>
            <button
              onClick={() => setShowFilter(f => !f)}
              className="flex items-center gap-1.5 text-xs text-primary font-medium hover:underline mb-2"
            >
              <Filter size={13} />
              {showFilter ? 'Ocultar filtros' : 'Filtrar por libro y páginas'}
            </button>
            {showFilter && (
              <div className="bg-bg rounded-xl p-3 md:p-4 space-y-3 mb-3 border border-border">
                <div>
                  <label className="text-[11px] text-textSub font-medium mb-1 block">Libro (opcional)</label>
                  <select
                    value={selDoc}
                    onChange={e => setSelDoc(e.target.value)}
                    className="input w-full py-2 text-sm"
                  >
                    <option value="">Todos los libros</option>
                    {docs.map(d => (
                      <option key={d.id} value={d.id}>{d.filename}</option>
                    ))}
                  </select>
                </div>
                <div className="flex gap-3">
                  <div className="flex-1">
                    <label className="text-[11px] text-textSub font-medium mb-1 block">Desde página</label>
                    <input
                      type="number"
                      min="1"
                      value={pageFrom}
                      onChange={e => setPageFrom(e.target.value)}
                      placeholder="Ej: 50"
                      className="input w-full py-2 text-sm"
                    />
                  </div>
                  <div className="flex-1">
                    <label className="text-[11px] text-textSub font-medium mb-1 block">Hasta página</label>
                    <input
                      type="number"
                      min="1"
                      value={pageTo}
                      onChange={e => setPageTo(e.target.value)}
                      placeholder="Ej: 120"
                      className="input w-full py-2 text-sm"
                    />
                  </div>
                </div>
                {(selDoc || pageFrom || pageTo) && (
                  <button
                    onClick={() => { setSelDoc(''); setPageFrom(''); setPageTo('') }}
                    className="text-[11px] text-danger hover:underline"
                  >
                    Limpiar filtros
                  </button>
                )}
              </div>
            )}
          </div>

          <div>
            <p className="text-xs text-textSub font-medium mb-2">Temas sugeridos</p>
            <div className="flex flex-wrap gap-1.5 md:gap-2">
              {TOPICS.map(t => (
                <button key={t}
                  onClick={() => { setTopic(t); generate(t) }}
                  disabled={loading}
                  className="text-[11px] md:text-xs px-2.5 py-1.5 bg-white border border-border rounded-pill
                             hover:border-primary/40 hover:text-primary hover:bg-primary/5 transition-colors
                             disabled:opacity-50">
                  {t}
                </button>
              ))}
            </div>
          </div>
        </div>

        {exams.length > 0 && (
          <div>
            <h2 className="font-semibold text-textMain mb-3 flex items-center gap-2 text-sm md:text-base">
              <GraduationCap size={18} className="text-sage" />
              Exámenes guardados
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {exams.map(e => (
                <div key={e.id}
                  className="card !p-4 hover:shadow-float transition-shadow cursor-pointer group"
                  onClick={() => openExam(e.id)}>
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="font-semibold text-sm text-textMain group-hover:text-primary transition-colors">
                        {e.topic}
                      </p>
                      <p className="text-xs text-textSub mt-1">{e.total} preguntas</p>
                    </div>
                    <button
                      onClick={ev => { ev.stopPropagation(); handleDelete(e.id) }}
                      className="p-1.5 rounded-lg hover:bg-danger/10 text-textSub/30 hover:text-danger transition-colors">
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {loading && (
          <div className="card py-10 flex flex-col items-center gap-3">
            <div className="w-8 h-8 rounded-full border-2 border-primary border-t-transparent animate-spin" />
            <p className="text-sm text-textSub">Generando examen con IA...</p>
          </div>
        )}

        {!loading && exams.length === 0 && (
          <div className="flex flex-col items-center py-10 text-center">
            <div className="w-14 h-14 rounded-2xl bg-bg flex items-center justify-center mb-4">
              <GraduationCap size={24} className="text-textSub/40" />
            </div>
            <p className="font-medium text-textMain text-sm">Sin exámenes aún</p>
            <p className="text-xs text-textSub mt-1">Genera tu primer examen seleccionando un tema.</p>
          </div>
        )}
      </div>
    </div>
  )
}
