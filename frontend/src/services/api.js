import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 600_000,
})

// ── Documents ────────────────────────────────────────────────
export const uploadDocument = (file, onProgress) => {
  const fd = new FormData()
  fd.append('file', file)
  return api.post('/documents/upload', fd, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: e => onProgress && onProgress(Math.round(e.loaded * 100 / e.total)),
  })
}

export const listDocuments  = ()      => api.get('/documents/')
export const getDocument    = id      => api.get(`/documents/${id}`)
export const deleteDocument = id      => api.delete(`/documents/${id}`)
export const summarizeDoc   = id      => api.post(`/documents/${id}/summarize`)
export const searchInDoc    = (id, q) => api.get(`/documents/${id}/search`, { params: { q } })

// ── Chat ─────────────────────────────────────────────────────
export const sendMessage = (message, mode = 'general', sessionId = 'default', docIds = null) =>
  api.post('/chat/', { message, mode, session_id: sessionId, doc_ids: docIds })

export const semanticSearch = (query, docIds = null, topK = 5) =>
  api.post('/chat/search', { query, doc_ids: docIds, top_k: topK })

export const clearSession = sessionId => api.delete(`/chat/session/${sessionId}`)
export const getModes     = ()        => api.get('/chat/modes')

// ── Cases ────────────────────────────────────────────────────
export const createCase    = data    => api.post('/cases/', data)
export const listCases     = ()      => api.get('/cases/')
export const getCase       = id      => api.get(`/cases/${id}`)
export const updateCase    = (id, d) => api.put(`/cases/${id}`, d)
export const deleteCase    = id      => api.delete(`/cases/${id}`)
export const reanalyzeCase = id      => api.post(`/cases/${id}/analyze`)

// ── Flashcards & Exams ───────────────────────────────────────
export const generateFlashcards = (topic, count = 10, docIds = null) =>
  api.post('/flashcards/generate', { topic, count, doc_ids: docIds })

export const generateExam = (topic, count = 10, docIds = null, pageFrom = null, pageTo = null) => {
  const body = { topic, count, doc_ids: docIds }
  if (pageFrom !== null) body.page_from = pageFrom
  if (pageTo !== null) body.page_to = pageTo
  return api.post('/flashcards/exam/generate', body)
}

export const listDecks  = ()   => api.get('/flashcards/decks')
export const getDeck    = id   => api.get(`/flashcards/decks/${id}`)
export const deleteDeck = id   => api.delete(`/flashcards/decks/${id}`)

export const listExams  = ()   => api.get('/flashcards/exams')
export const getExam    = id   => api.get(`/flashcards/exams/${id}`)
export const deleteExam = id   => api.delete(`/flashcards/exams/${id}`)

// ── Clinical Tools ───────────────────────────────────────────
export const checkInteractions = (drugs, patientContext = null) =>
  api.post('/tools/interactions', { drugs, patient_context: patientContext })

export const interpretScale = (scaleName, totalScore, itemScores = [], patientContext = null) =>
  api.post('/tools/scales/interpret', {
    scale_name: scaleName, total_score: totalScore,
    item_scores: itemScores, patient_context: patientContext,
  })

// ── Comparator & Chapters ────────────────────────────────────
export const compareDsmCie   = disorder => api.post('/tools/compare', { disorder })
export const chapterSummary  = (docId, chapterQuery) =>
  api.post('/tools/chapter-summary', { doc_id: docId, chapter_query: chapterQuery })
export const getHistory      = () => api.get('/tools/history')
export const clearHistory    = () => api.delete('/tools/history')

// ── Health ───────────────────────────────────────────────────
export const healthCheck = () => api.get('/health')

export default api
