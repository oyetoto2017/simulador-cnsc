import hashlib
import json
import random
import re
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import pymupdf as fitz
import streamlit as st
from google import genai

# ==========================================
# CONFIGURACIÓN DE PÁGINA Y ESTILOS
# ==========================================
st.set_page_config(
    page_title="Simulador de Concursos Públicos | CNSC",
    page_icon="⚖️",
    layout="centered",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
    .documento-word { background:#fff; border:1px solid #dadce0; border-radius:10px; padding:20px;
        max-width:850px; margin:10px auto; line-height:1.5; font-family:sans-serif; color: #202124;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
    .titulo-encabezado { color:#1a73e8; font-size:18px; font-weight:700; border-bottom:2px solid #1a73e8;
        padding-bottom:8px; margin-bottom:15px; }
    .resumen-cargo { background:#e6f4ea; border:1px solid #34a853; border-radius:8px; padding:15px;
        margin-bottom:15px; font-size:14px; color: #137333; }
    .alerta-sin-manual { background:#fef7e0; border-left:5px solid #f9ab00; padding:12px;
        margin-bottom:15px; font-size:14px; color:#b06000; }
    .pregunta-enunciado { background:#f8f9fa; border-left:4px solid #1a73e8; padding:14px; font-size:15px;
        font-weight:600; margin-bottom:15px; border-radius: 4px; }
    .opcion-item { background:#fff; border:1px solid #e0e0e0; padding:10px 14px; margin-bottom:8px;
        border-radius:6px; font-size:14px; }
    .caja-correcta { background:#e6f4ea; border-left:5px solid #34a853; padding:15px; margin-bottom:15px; border-radius:6px;}
    .caja-incorrecta { background:#fce8e6; border-left:5px solid #ea4335; padding:15px; margin-bottom:15px; border-radius:6px;}
    .badge { background:#e8f0fe; padding:4px 10px; border-radius:12px; font-size:12px; margin-right:5px; color:#1a73e8; font-weight: 500;}
</style>
""",
    unsafe_allow_html=True,
)

# ==========================================
# ESTRUCTURAS DE DATOS Y ESTADO
# ==========================================


@dataclass
class Pagina:
  doc: str
  pag: int
  texto: str


@dataclass
class Perfil:
  detectado: bool = False
  cargo: str = "General"
  proposito: str = "Selecciona manual"
  competencias: List[str] = field(
      default_factory=lambda: ["Funciones del cargo"]
  )
  competencias_funcionales: List[str] = field(default_factory=list)
  competencias_comportamentales: List[str] = field(default_factory=list)


if "paginas" not in st.session_state:
  st.session_state.paginas = []
if "manuales" not in st.session_state:
  st.session_state.manuales = {}
if "texto_manual" not in st.session_state:
  st.session_state.texto_manual = ""
if "perfil" not in st.session_state:
  st.session_state.perfil = Perfil()
if "puntaje" not in st.session_state:
  st.session_state.puntaje = 0
if "total" not in st.session_state:
  st.session_state.total = 0
if "generadas" not in st.session_state:
  st.session_state.generadas = set()
if "respondidas" not in st.session_state:
  st.session_state.respondidas = set()
if "paginas_usadas" not in st.session_state:
  st.session_state.paginas_usadas = set()
if "modo_examen_activo" not in st.session_state:
  st.session_state.modo_examen_activo = False
if "examen_preguntas" not in st.session_state:
  st.session_state.examen_preguntas = []
if "examen_idx" not in st.session_state:
  st.session_state.examen_idx = 0
if "examen_respuestas" not in st.session_state:
  st.session_state.examen_respuestas = []
if "examen_inicio" not in st.session_state:
  st.session_state.examen_inicio = 0.0

MODELOS_CANDIDATOS = ["gemini-2.5-flash", "gemini-2.5-pro"]


def obtener_cliente(api_key: str):
  if not api_key:
    return None
  try:
    return genai.Client(api_key=api_key)
  except Exception:
    return None


def generar_contenido(client, prompt: str) -> Optional[str]:
  if not client:
    return None
  for modelo in MODELOS_CANDIDATOS:
    for intento in range(2):
      try:
        resp = client.models.generate_content(model=modelo, contents=prompt)
        if resp and resp.text:
          return resp.text
      except Exception as e:
        msg = str(e).lower()
        if "429" in msg or "resource_exhausted" in msg or "quota" in msg:
          st.warning(f"⚠️ Cuota agotada temporalmente para {modelo}.")
          return None
        if intento == 0:
          time.sleep(1.5)
          continue
        break
  return None


# ==========================================
# PROCESAMIENTO DE DOCUMENTOS
# ==========================================


def extraer_pdf_bytes(nombre: str, contenido_bytes: bytes) -> Tuple[str, List[Pagina]]:
  paginas = []
  texto_completo = ""
  try:
    doc = fitz.open(stream=contenido_bytes, filetype="pdf")
    for i in range(len(doc)):
      txt = doc[i].get_text("text").strip()
      if txt:
        paginas.append(Pagina(nombre, i + 1, txt))
        texto_completo += "\n" + txt
    doc.close()
    return texto_completo, paginas
  except Exception as e:
    st.error(f"Error procesando PDF {nombre}: {e}")
    return "", []


# ==========================================
# PERFILADO DE MANUALES
# ==========================================


def perfilar_manual(client, nombre: str):
  if not client or nombre not in st.session_state.manuales:
    return

  st.session_state.perfil = Perfil()
  st.session_state.texto_manual = ""
  st.session_state.generadas = set()
  st.session_state.respondidas = set()
  st.session_state.paginas_usadas = set()

  texto = st.session_state.manuales[nombre]
  fragmentos = [texto[i : i + 6000] for i in range(0, len(texto), 6000)]
  texto_analisis = "\n---FRAGMENTO---\n".join(fragmentos[:5])[:30000]

  prompt = f"""
    Eres un experto en análisis de manuales de funciones para concursos públicos colombianos (CNSC, DIAN, Contraloría).

    TEXTO DEL MANUAL DE FUNCIONES:
    {texto_analisis}

    INSTRUCCIONES:
    Analiza este texto y extrae en formato JSON estricto:
    1. El cargo EXACTO (ej: "Gestor I", "Profesional Universitario", "Técnico Administrativo")
    2. El propósito principal del empleo
    3. Competencias FUNCIONALES clave (4-6)
    4. Competencias COMPORTAMENTALES clave (2-4)

    DEVUELVE EXACTAMENTE ESTE JSON (sin bloques de código markdown adicionales, solo el JSON):
    {{
      "cargo": "Denominación exacta del cargo",
      "proposito": "Propósito principal en una frase clara",
      "competencias_funcionales": ["func1", "func2", "func3"],
      "competencias_comportamentales": ["comp1", "comp2"]
    }}
    """

  raw = generar_contenido(client, prompt)
  if not raw:
    return

  try:
    limpio = re.sub(r"```(?:json)?", "", raw.strip())
    limpio = re.sub(r"```", "", limpio).strip()
    data = json.loads(limpio)

    cargo = data.get("cargo", "").strip()
    proposito = data.get("proposito", "").strip()
    comp_func = data.get("competencias_funcionales", [])
    comp_comp = data.get("competencias_comportamentales", [])

    if not cargo:
      return

    st.session_state.perfil.detectado = True
    st.session_state.perfil.cargo = cargo
    st.session_state.perfil.proposito = proposito or "Verificación misional"
    st.session_state.perfil.competencias_funcionales = comp_func
    st.session_state.perfil.competencias_comportamentales = comp_comp
    todas = comp_func + comp_comp
    if todas:
      st.session_state.perfil.competencias = [
          "Evaluación mixta (Todas)",
          "Escribir tema propio...",
      ] + todas
    else:
      st.session_state.perfil.competencias = [
          "Evaluación mixta (Todas)",
          "Escribir tema propio...",
      ]
    st.session_state.texto_manual = texto
  except Exception:
    pass


# ==========================================
# SELECCIÓN Y GENERACIÓN ACADÉMICA
# ==========================================


def paginas_relevantes(tema: str, n: int = 6) -> List[Pagina]:
  if not st.session_state.paginas:
    return []

  candidatas = st.session_state.paginas
  selected_manual = st.session_state.get("selected_manual")
  if st.session_state.texto_manual and selected_manual in st.session_state.manuales:
    candidatas = [p for p in st.session_state.paginas if p.doc == selected_manual]
    if not candidatas:
      candidatas = st.session_state.paginas

  usadas = st.session_state.paginas_usadas
  disponibles = [p for p in candidatas if (p.doc, p.pag) not in usadas]
  if not disponibles:
    disponibles = candidatas
    usadas.clear()

  palabras = [w.lower() for w in re.findall(r"\w+", tema) if len(w) > 3]
  if not palabras:
    seleccion = random.sample(disponibles, min(n, len(disponibles)))
    for p in seleccion:
      usadas.add((p.doc, p.pag))
    return seleccion

  puntuadas = []
  for p in disponibles:
    texto_lower = p.texto.lower()
    score = sum(texto_lower.count(w) for w in palabras)
    puntuadas.append((score, p))

  puntuadas.sort(key=lambda x: x[0], reverse=True)
  top = [p for _, p in puntuadas[: n * 2]]
  seleccion = top[:n] if len(top) <= n else random.sample(top, n)
  for p in seleccion:
    usadas.add((p.doc, p.pag))
  return seleccion


def validar_pregunta(data: dict) -> Tuple[bool, str]:
  if not isinstance(data, dict):
    return False, "Formato no válido"
  pregunta = data.get("pregunta") or data.get("enunciado")
  if not pregunta or len(pregunta.strip()) < 15:
    return False, "Pregunta muy corta"
  opciones = data.get("opciones")
  if not isinstance(opciones, dict) or not all(k in opciones for k in ["A", "B", "C", "D"]):
    return False, "Opciones incompletas"
  if data.get("correcta") not in ["A", "B", "C", "D"]:
    return False, "Respuesta correcta inválida"
  if not data.get("explicacion"):
    return False, "Falta explicación"
  if not data.get("fragmento_soporte"):
    return False, "Falta fragmento de soporte"
  return True, "OK"


def generar_pregunta(client, tema: str, dificultad: str) -> Optional[dict]:
  muestra = paginas_relevantes(tema, 6)
  docs = "\n".join([f"[{p.doc} - Pág. {p.pag}]: {p.texto[:400]}" for p in muestra])[:5000]
  manual = st.session_state.texto_manual[:5000] if st.session_state.texto_manual else "Sin manual"
  perfil = st.session_state.perfil

  prompt = f"""Actúa como un diseñador experto de pruebas de competencias para concursos públicos en Colombia (CNSC, DIAN).

CARGO: {perfil.cargo}
PROPÓSITO: {perfil.proposito}
COMPETENCIA: {tema}
DIFICULTAD: {dificultad}

MANUAL DE FUNCIONES:
{manual}

DOCUMENTOS DE APOYO:
{docs}

CREA UN CASO PRÁCTICO SITUACIONAL. 
REGLAS ESTRICTAS:
- 4 opciones (A, B, C, D).
- Una única respuesta correcta basada estrictamente en los documentos adjuntos.
- Incluye el fragmento literal exacto del texto de apoyo que justifica la respuesta.

DEVUELVE ÚNICAMENTE JSON VÁLIDO (sin markdown):
{{"pregunta":"...","opciones":{{"A":"...","B":"...","C":"...","D":"..."}},"correcta":"A","explicacion":"...","fuente":"nombre del documento","pagina":1,"fragmento_soporte":"texto literal de apoyo"}}"""

  raw = generar_contenido(client, prompt)
  if not raw:
    return None

  try:
    limpio = re.sub(r"```(?:json)?", "", raw.strip())
    limpio = re.sub(r"```", "", limpio).strip()
    m = re.search(r"\{.*\}", limpio, re.DOTALL)
    if m:
      limpio = m.group(0)
    data = json.loads(limpio)
    ok, _ = validar_pregunta(data)
    if not ok:
      return None

    # Validación anti-alucinación de fragmento
    fragmento = data.get("fragmento_soporte", "")
    fuente = data.get("fuente", "")
    pagina_real = next((p for p in muestra if p.doc.lower() in fuente.lower() or fuente.lower() in p.doc.lower()), None)
    if not pagina_real and muestra:
      pagina_real = muestra[0]

    if pagina_real:
      data["fuente"] = pagina_real.doc
      data["pagina"] = pagina_real.pag
      if fragmento.lower() not in pagina_real.texto.lower():
        # Verificación flexible por palabras clave
        palabras_frag = set(fragmento.lower().split())
        palabras_pag = set(pagina_real.texto.lower().split())
        if len(palabras_frag & palabras_pag) / max(len(palabras_frag), 1) < 0.6:
          data["fragmento_soporte"] = pagina_real.texto[:300]  # Fallback seguro

    data["_id"] = str(hashlib.md5(data["pregunta"].encode()).hexdigest())
    return data
  except Exception:
    return None


# ==========================================
# INTERFAZ DE USUARIO (SIDEBAR Y VISTAS)
# ==========================================

st.sidebar.title("⚖️ Panel de Control")

# Credencial API Key
api_key_input = st.sidebar.text_input(
    "GEMINI_API_KEY", type="password", help="Ingresa tu clave de API de Google Gemini."
)
client = obtener_cliente(api_key_input)

st.sidebar.markdown("---")
st.sidebar.subheader("📂 Carga Documental")
archivos_subidos = st.sidebar.file_uploader(
    "Sube Manuales (PDF) y Normativa", type=["pdf", "txt"], accept_multiple_files=True
)

if archivos_subidos:
  for archivo in archivos_subidos:
    if archivo.name not in st.session_state.manuales:
      bytes_data = archivo.read()
      if archivo.name.endswith(".pdf"):
        texto, pags = extraer_pdf_bytes(archivo.name, bytes_data)
        if pags:
          st.session_state.paginas.extend(pags)
          if any(k in archivo.name.lower() for k in ["manual", "funciones", "ficha", "empleo", "perfil", "opec"]):
            st.session_state.manuales[archivo.name] = texto
      elif archivo.name.endswith(".txt"):
        texto = bytes_data.decode("utf-8", errors="ignore")
        st.session_state.paginas.append(Pagina(archivo.name, 1, texto))
        if any(k in archivo.name.lower() for k in ["manual", "funciones", "ficha", "empleo", "perfil", "opec"]):
          st.session_state.manuales[archivo.name] = texto

# Selector de Manual Activo
if st.session_state.manuales:
  lista_manuales = list(st.session_state.manuales.keys())
  selected_manual = st.sidebar.selectbox("Manual de Funciones Activo", lista_manuales, key="selected_manual")
  if st.sidebar.button("🔍 Perfilar Manual"):
    if client:
      with st.spinner("Analizando manual con IA..."):
        perfilar_manual(client, selected_manual)
      st.success("¡Perfilado completado!")
    else:
      st.error("Ingresa una API Key válida.")

st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ Configuración de Pruebas")
tema_opciones = st.session_state.perfil.competencias
tema_seleccionado = st.sidebar.selectbox("Competencia / Tema", tema_opciones)
if tema_seleccionado == "Escribir tema propio...":
  tema_seleccionado = st.sidebar.text_input("Especifica el tema:")

dificultad = st.sidebar.select_slider("Dificultad", options=["Media", "Alta", "Muy alta"], value="Alta")
num_preguntas_examen = st.sidebar.selectbox("Preguntas para Examen Múltiple", [3, 5, 10, 20], index=1)

# ==========================================
# CUERPO PRINCIPAL
# ==========================================

st.markdown(
    """
    <div style="text-align:center; padding: 10px 0;">
        <h2>Simulador de Concursos Públicos de Méritos</h2>
        <p style="color: #5f6368;">Plataforma interactiva de entrenamiento basada en normativas y manuales oficiales (CNSC, DIAN, Contraloría).</p>
    </div>
""",
    unsafe_allow_html=True,
)

if not client:
  st.warning("⚠️ Por favor, ingresa tu **GEMINI_API_KEY** en la barra lateral para comenzar.")
elif not st.session_state.paginas:
  st.info("💡 Sube tus documentos PDF (manuales de funciones o normativas) mediante el cargador en la barra lateral.")
else:
  # Resumen de Perfil
  perfil = st.session_state.perfil
  if perfil.detectado:
    st.markdown(
        f"""
        <div class="resumen-cargo">
            <b>✅ PERFIL ACTIVO:</b> {perfil.cargo}<br>
            <b>📌 Propósito:</b> {perfil.proposito}
        </div>
        """,
        unsafe_allow_html=True,
    )

  col1, col2 = st.columns(2)
  with col1:
    btn_practica = st.button("🎯 Modo Práctica Individual", use_container_width=True)
  with col2:
    btn_examen_inicio = st.button("📝 Iniciar Examen Múltiple", use_container_width=True)

  # Manejo de Modo Examen Múltiple
  if btn_examen_inicio:
    with st.spinner("Generando batería de preguntas para el examen..."):
      preguntas = []
      vistos = set()
      for _ in range(num_preguntas_examen * 2):
        if len(preguntas) >= num_preguntas_examen:
          break
        q = generar_pregunta(client, tema_seleccionado, dificultad)
        if q and q["_id"] not in vistos:
          vistos.add(q["_id"])
          preguntas.append(q)
      if preguntas:
        st.session_state.modo_examen_activo = True
        st.session_state.examen_preguntas = preguntas
        st.session_state.examen_idx = 0
        st.session_state.examen_respuestas = []
        st.session_state.examen_inicio = time.time()
        st.rerun()
      else:
        st.error("No se pudieron generar suficientes preguntas. Intenta con otro manual o tema.")

  # Lógica del Examen Múltiple
  if st.session_state.modo_examen_activo:
    preguntas = st.session_state.examen_preguntas
    idx = st.session_state.examen_idx

    if idx < len(preguntas):
      q = preguntas[idx]
      st.markdown(
          f"""
            <div class="documento-word">
                <div class="titulo-encabezado">📝 EXAMEN OFICIAL - Pregunta {idx + 1} de {len(preguntas)}</div>
                <span class="badge">{tema_seleccionado}</span>
                <div class="pregunta-enunciado">{q['pregunta']}</div>
            </div>
            """,
          unsafe_allow_html=True,
      )

      opcion_elegida = st.radio(
          "Selecciona tu respuesta:",
          options=["A", "B", "C", "D"],
          format_func=lambda x: f"{x}) {q['opciones'][x]}",
          key=f"radio_ex_{idx}",
      )

      if st.button("Confirmar y Siguiente ➡️", key=f"btn_ex_{idx}"):
        es_ok = (opcion_elegida == q["correcta"])
        st.session_state.examen_respuestas.append({"ok": es_ok})
        st.session_state.total += 1
        if es_ok:
          st.session_state.puntaje += 1
        st.session_state.examen_idx += 1
        st.rerun()
    else:
      # Finalizar examen
      respuestas = st.session_state.examen_respuestas
      correctas = sum(1 for r in respuestas if r["ok"])
      total = len(respuestas)
      tiempo_g = time.time() - st.session_state.examen_inicio
      pct = (correctas / total * 100) if total > 0 else 0
      dictamen = "APROBADO 🎉" if pct >= 60 else "REPROBADO ❌"

      st.markdown(
          f"""
            <div class="documento-word" style="text-align: center;">
                <div class="titulo-encabezado">📊 REPORTE FINAL DE EXAMEN</div>
                <h3>Dictamen: {dictamen}</h3>
                <p><b>Aciertos:</b> {correctas} / {total} ({pct:.1f}%)</p>
                <p><b>Tiempo empleado:</b> {tiempo_g:.0f} segundos</p>
            </div>
            """,
          unsafe_allow_html=True,
      )
      if st.button("🔄 Finalizar y Volver al Menú"):
        st.session_state.modo_examen_activo = False
        st.rerun()

  else:
    # Modo Práctica Individual por defecto
    if btn_practica or "pregunta_actual" not in st.session_state:
      with st.spinner("Generando caso práctico riguroso..."):
        q = generar_pregunta(client, tema_seleccionado, dificultad)
        if q:
          st.session_state.pregunta_actual = q
          st.session_state.respondido_actual = False
        else:
          st.error("Error al generar la pregunta. Verifica tu API Key o documentos.")
          st.stop()

    if "pregunta_actual" in st.session_state:
      q = st.session_state.pregunta_actual
      st.markdown(
          f"""
            <div class="documento-word">
                <div class="titulo-encabezado">🎯 CASO PRÁCTICO SITUACIONAL</div>
                <span class="badge">📚 {tema_seleccionado}</span>
                <span class="badge" style="background:#fef7e0; color:#b06000;">🎯 {dificultad}</span>
                <div class="pregunta-enunciado">{q['pregunta']}</div>
            </div>
            """,
          unsafe_allow_html=True,
      )

      opcion = st.radio(
          "Opciones de respuesta:",
          options=["A", "B", "C", "D"],
          format_func=lambda x: f"{x}) {q['opciones'][x]}",
          key="radio_practica",
      )

      if not st.session_state.respondido_actual:
        if st.button("Evaluar Respuesta"):
          st.session_state.respondido_actual = True
          st.session_state.total += 1
          if opcion == q["correcta"]:
            st.session_state.puntaje += 1
          st.rerun()
      else:
        correcta = q["correcta"]
        es_acierto = (opcion == correcta)
        if es_acierto:
          caja = '<div class="caja-correcta"><h3 style="color:#137333;">🎉 ¡Respuesta Correcta!</h3></div>'
        else:
          caja = f'<div class="caja-incorrecta"><h3 style="color:#c5221f;">❌ Respuesta Errada</h3><p><b>La opción correcta era:</b> {correcta}) {q["opciones"][correcta]}</p></div>'

        st.markdown(
            f"""
            <div class="documento-word">
                {caja}
                <div style="background:#f8f9fa;padding:12px;border-radius:6px;margin-top:10px;">
                    <b>📚 Fundamento Normativo / Manual:</b>
                    <p style="margin-top:5px;">{q['explicacion']}</p>
                    <hr style="border:0; border-top:1px solid #ddd; margin:8px 0;">
                    <small><b>Fuente:</b> {q.get('fuente', 'N/A')} (Pág. {q.get('pagina', 1)})</small><br>
                    <small style="color: #666;"><i>Fragmento de soporte: "{q.get('fragmento_soporte', '')[:180]}..."</i></small>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.button("➡️ Siguiente Pregunta"):
          del st.session_state.pregunta_actual
          st.session_state.respondido_actual = False
          st.rerun()

  # Métricas globales en pie de página
  st.markdown("---")
  st.markdown(
      f"<p style='text-align: center; color: #70757a; font-size: 13px;'>📊 Estadísticas de Sesión — Aciertos: <b>{st.session_state.puntaje} / {st.session_state.total}</b></p>",
      unsafe_allow_html=True,
  )
