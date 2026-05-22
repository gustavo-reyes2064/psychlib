import anthropic, os, json
from typing import List, Dict, Any

CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-5")

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

SYSTEM_PROMPTS = {
    "general": """Eres un asistente académico especializado en psiquiatría.
Tienes acceso a una biblioteca personal de libros de psiquiatría.
Responde SIEMPRE en español, de forma clara, estructurada y académica.
Usa los fragmentos de los libros para fundamentar tus respuestas.
Cita siempre la fuente (libro y página) cuando uses información específica.
IMPORTANTE: Solo para uso educativo. No para diagnóstico clínico real.""",

    "diagnostico": """Eres un asistente de apoyo al estudio psiquiátrico.
Al analizar síntomas, proporciona diagnósticos DIFERENCIALES educativos basados en DSM-5.
Estructura tu respuesta: 1) Diagnósticos a considerar, 2) Criterios relevantes, 3) Diferencial.
SIEMPRE incluye el disclaimer: 'Solo uso educativo - no reemplaza evaluación clínica'.
Fundamenta con los textos de la biblioteca cuando estén disponibles.""",

    "dsm5": """Eres un experto en el DSM-5-TR y CIE-11.
Proporciona criterios diagnósticos precisos, códigos, especificadores y notas clínicas.
Organiza la información con criterios A, B, C, D claramente numerados.
Menciona diagnósticos diferenciales y comorbilidades frecuentes.
Usa los textos de la biblioteca como fuente principal.""",

    "farmacologia": """Eres un asistente especializado en psicofarmacología académica.
Proporciona información sobre mecanismos de acción, dosis orientativas, efectos adversos.
Organiza: 1) Mecanismo, 2) Indicaciones, 3) Dosis referencial, 4) Efectos adversos relevantes.
SIEMPRE aclarar que las dosis son referenciales y deben ser indicadas por médico.""",

    "caso": """Eres un tutor de psiquiatría que ayuda a analizar casos clínicos educativos.
Analiza el caso presentado estructurando: 1) Síntomas clave, 2) Hipótesis diagnósticas,
3) Criterios DSM-5 aplicables, 4) Diagnóstico diferencial, 5) Consideraciones de manejo.
Usa los libros de la biblioteca para fundamentar el análisis.""",

    "psicopatologia": """Eres un experto en psicopatología académica, especializado en la tradición de Karl Jaspers, Kurt Schneider, y la psicopatología descriptiva clásica.
Explica los fenómenos psicopatológicos con precisión conceptual: alteraciones de la percepción, el pensamiento, la afectividad, la voluntad, la conciencia y la personalidad.
Estructura tus respuestas: 1) Definición del fenómeno, 2) Clasificación, 3) Semiología (cómo se explora), 4) Significado clínico, 5) Diagnóstico diferencial semiológico.
Distingue claramente entre forma y contenido de los síntomas.
Fundamenta con los textos de la biblioteca cuando estén disponibles.
IMPORTANTE: Solo para uso educativo.""",
}


def build_context(sources: List[Dict[str, Any]]) -> str:
    if not sources:
        return ""
    ctx = "\n\n=== FRAGMENTOS DE TUS LIBROS ===\n"
    for s in sources:
        ctx += f"\n[{s['filename']} — Página {s['page']}]\n{s['text']}\n"
    ctx += "\n=== FIN DE FRAGMENTOS ===\n"
    return ctx


def chat(
    message: str,
    history: List[Dict[str, str]],
    sources: List[Dict[str, Any]],
    mode: str = "general",
) -> Dict[str, Any]:
    system = SYSTEM_PROMPTS.get(mode, SYSTEM_PROMPTS["general"])
    context = build_context(sources)

    messages = []
    for h in history[-10:]:   # últimos 10 mensajes
        messages.append({"role": h["role"], "content": h["content"]})

    user_msg = message
    if context:
        user_msg = f"{context}\n\nPregunta del usuario: {message}"

    messages.append({"role": "user", "content": user_msg})

    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=2048,
        system=system,
        messages=messages,
    )

    return {
        "answer":      response.content[0].text,
        "tokens_used": response.usage.input_tokens + response.usage.output_tokens,
    }


def summarize_document(chunks_text: str, filename: str) -> str:
    """Resume un documento completo."""
    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=1024,
        system="Eres un experto en psiquiatría. Resume documentos académicos de forma clara y estructurada en español.",
        messages=[{
            "role": "user",
            "content": f"Crea un resumen académico del siguiente documento de psiquiatría '{filename}':\n\n{chunks_text[:8000]}"
        }],
    )
    return response.content[0].text


def generate_flashcards(chunks_text: str, topic: str, count: int = 10) -> list:
    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=4096,
        system="Eres un profesor experto en psiquiatría. Genera tarjetas de estudio (flashcards) precisas y útiles para residentes de psiquiatría. Responde SOLO con JSON válido.",
        messages=[{
            "role": "user",
            "content": f"""Usando el siguiente material de referencia, genera exactamente {count} flashcards sobre: "{topic}"

Material de referencia:
{chunks_text[:10000]}

Responde ÚNICAMENTE con un JSON array. Cada elemento debe tener:
- "front": pregunta concisa (máximo 2 líneas)
- "back": respuesta clara y precisa (máximo 4 líneas)
- "difficulty": "basico", "intermedio" o "avanzado"

Ejemplo de formato:
[{{"front": "¿Cuáles son los criterios A del TDM según DSM-5?", "back": "Al menos 5 de 9 síntomas durante 2 semanas, incluyendo ánimo deprimido o anhedonia.", "difficulty": "basico"}}]

Genera exactamente {count} flashcards. Solo JSON, sin texto adicional."""
        }],
    )
    text = response.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    try:
        cards = json.loads(text)
        return cards[:count]
    except json.JSONDecodeError:
        return [{"front": "Error al generar flashcards", "back": text[:500], "difficulty": "basico"}]


def generate_exam(chunks_text: str, topic: str, count: int = 10) -> list:
    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=4096,
        system="Eres un profesor experto en psiquiatría. Genera preguntas de examen tipo selección múltiple para residentes. Responde SOLO con JSON válido.",
        messages=[{
            "role": "user",
            "content": f"""Usando el siguiente material, genera exactamente {count} preguntas de selección múltiple sobre: "{topic}"

Material de referencia:
{chunks_text[:10000]}

Responde ÚNICAMENTE con un JSON array. Cada elemento debe tener:
- "question": la pregunta
- "options": array de 4 opciones (strings)
- "correct": índice de la respuesta correcta (0-3)
- "explanation": explicación breve de por qué es correcta
- "difficulty": "basico", "intermedio" o "avanzado"

Genera preguntas variadas: definiciones, diagnóstico diferencial, farmacología, criterios DSM-5, manejo clínico.
Genera exactamente {count} preguntas. Solo JSON, sin texto adicional."""
        }],
    )
    text = response.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    try:
        questions = json.loads(text)
        return questions[:count]
    except json.JSONDecodeError:
        return [{"question": "Error al generar examen", "options": ["A","B","C","D"], "correct": 0, "explanation": text[:500], "difficulty": "basico"}]


def check_drug_interactions(drugs: list, chunks_text: str, patient_context: str = None) -> str:
    ctx = ""
    if chunks_text:
        ctx = f"\n\nReferencia de tus libros:\n{chunks_text[:8000]}"
    patient = ""
    if patient_context:
        patient = f"\nContexto del paciente: {patient_context}"

    drugs_str = ", ".join(drugs)
    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=2048,
        system="""Eres un farmacólogo clínico experto en psicofarmacología.
Analiza interacciones entre medicamentos psiquiátricos de forma educativa.
Responde en español, estructurado y claro.
SIEMPRE incluye: 'Solo uso educativo — consultar con farmacéutico clínico para decisiones reales.'""",
        messages=[{
            "role": "user",
            "content": f"""Analiza las posibles interacciones entre estos fármacos: {drugs_str}{patient}{ctx}

Estructura tu respuesta:
1. **Resumen de riesgo** (bajo/moderado/alto/contraindicado)
2. **Interacciones identificadas** (mecanismo, severidad, efecto clínico)
3. **Recomendaciones de monitoreo**
4. **Alternativas a considerar** (si aplica)"""
        }],
    )
    return response.content[0].text


def interpret_scale_result(
    scale_name: str, total_score: int, item_scores: list,
    chunks_text: str, patient_context: str = None
) -> str:
    ctx = ""
    if chunks_text:
        ctx = f"\n\nReferencia de tus libros:\n{chunks_text[:6000]}"
    patient = ""
    if patient_context:
        patient = f"\nContexto clínico: {patient_context}"

    items_str = ""
    if item_scores:
        items_str = f"\nPuntuaciones por ítem: {item_scores}"

    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=1024,
        system="""Eres un psiquiatra académico experto en escalas de evaluación psiquiátrica.
Interpreta resultados de escalas de forma educativa y precisa.
SIEMPRE incluye: 'Solo uso educativo — no reemplaza evaluación clínica profesional.'""",
        messages=[{
            "role": "user",
            "content": f"""Interpreta el siguiente resultado de la escala {scale_name}:
- Puntuación total: {total_score}{items_str}{patient}{ctx}

Incluye:
1. **Rango de severidad** según puntos de corte estándar
2. **Interpretación clínica** educativa
3. **Dominios afectados** (si aplica según ítems)
4. **Consideraciones** para seguimiento"""
        }],
    )
    return response.content[0].text


def compare_classifications(disorder: str, chunks_text: str) -> str:
    ctx = ""
    if chunks_text:
        ctx = f"\n\nReferencia de tus libros:\n{chunks_text[:10000]}"

    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=3000,
        system="""Eres un experto en clasificación psiquiátrica, especializado en DSM-5-TR y CIE-11.
Compara criterios diagnósticos entre ambos sistemas de forma precisa y educativa.
Responde en español con formato estructurado usando markdown.""",
        messages=[{
            "role": "user",
            "content": f"""Compara el diagnóstico de "{disorder}" entre DSM-5-TR y CIE-11:{ctx}

Estructura tu respuesta así:

## {disorder}

### DSM-5-TR
- **Código**:
- **Criterios principales**: (lista A, B, C...)
- **Especificadores**:
- **Duración requerida**:

### CIE-11
- **Código**:
- **Criterios principales**:
- **Calificadores**:
- **Duración requerida**:

### Diferencias clave
(tabla comparativa de las diferencias más importantes)

### Concordancia clínica
(cuándo coinciden y cuándo divergen en la práctica)

### Nota educativa
(implicaciones prácticas para el diagnóstico)"""
        }],
    )
    return response.content[0].text


def summarize_chapter(chunks_text: str, chapter_query: str, filename: str) -> str:
    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=2048,
        system="""Eres un profesor de psiquiatría. Resume capítulos de libros de forma clara,
estructurada y útil para el estudio. Incluye los conceptos clave, definiciones importantes
y puntos de alto rendimiento para exámenes. Responde en español.""",
        messages=[{
            "role": "user",
            "content": f"""Resume el siguiente contenido del capítulo/sección "{chapter_query}" del libro "{filename}":

{chunks_text[:12000]}

Estructura tu resumen:
1. **Conceptos clave** — ideas principales del capítulo
2. **Definiciones importantes** — términos que hay que saber
3. **Puntos de alto rendimiento** — lo más preguntado en exámenes
4. **Esquema resumen** — organización visual del contenido"""
        }],
    )
    return response.content[0].text


def analyze_case(case_data: Dict[str, Any], sources: List[Dict[str, Any]]) -> str:
    """Analiza un caso clínico con contexto RAG."""
    context = build_context(sources)
    case_text = f"""
Caso clínico:
- Edad: {case_data.get('age', 'N/D')} años, {case_data.get('gender', 'N/D')}
- Motivo de consulta: {case_data.get('chief_complaint', '')}
- Historia: {case_data.get('history', '')}
- Síntomas: {', '.join(case_data.get('symptoms', []))}
- Estado mental: {case_data.get('mental_status', 'No especificado')}
"""
    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=2048,
        system=SYSTEM_PROMPTS["caso"],
        messages=[{
            "role": "user",
            "content": f"{context}\n\nAnaliza el siguiente caso clínico educativo:\n{case_text}"
        }],
    )
    return response.content[0].text
