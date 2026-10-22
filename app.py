import datetime
import hashlib
import html
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
# CONFIGURACIÓN COMERCIAL Y DE PAGOS (OMAR)
# ==========================================
NUMERO_NEQUI_WHATSAPP = "3108137030"
WHATSAPP_INTL = f"57{NUMERO_NEQUI_WHATSAPP}"
URL_PSE_NEQUI = "https://recarga.nequi.com.co/"
CLAVE_MAESTRA_ADMIN = "OMAR2026"  # Clave privada para tu generador de licencias
LIMITE_PREGUNTAS_GRATIS = 2

# ==========================================
# CONFIGURACIÓN DE PÁGINA Y ESTILOS SAAS
# ==========================================
st.set_page_config(
    page_title="Mérito PRO | Simulador Inteligente de Concursos Públicos",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    .hero-box {
        background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 55%, #1d4ed8 100%);
        color: white;
        padding: 26px 32px;
        border-radius: 16px;
        margin-bottom: 20px;
        box-shadow: 0 10px 25px -5px rgba(29, 78, 216, 0.25);
    }
    .hero-tag {
        background: rgba(255, 255, 255, 0.16);
        color: #bae6fd;
        padding: 4px 12px;
        border-radius: 999px;
        font-size: 11.5px;
        font-weight: 700;
        text-transform: uppercase;
        display: inline-block;
        margin-bottom: 8px;
    }
    .hero-title { font-size: 26px; font-weight: 800; margin: 0 0 6px 0; color: #fff; }
    .hero-sub { font-size: 14.5px; color: #e2e8f0; margin: 0; line-height: 1.5; }

    .kpi-box {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 14px 18px;
        text-align: center;
        box-shadow: 0 1px 3px rgba(0,0,0,0.03);
    }
    .kpi-num { font-size: 22px; font-weight: 800; color: #0f172a; margin: 2px 0; }
    .kpi-label { font-size: 11px; font-weight: 700; color: #64748b; text-transform: uppercase; }

    .saas-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 14px;
        padding: 22px;
        margin-bottom: 16px;
        box-shadow: 0 4px 12px rgba(15, 23, 42, 0.03);
        color: #1e293b;
    }
    .eje-badge {
        background: #eff6ff;
        color: #1d4ed8;
        border: 1px solid #bfdbfe;
        padding: 4px 11px;
        border-radius: 999px;
        font-size: 12px;
        font-weight: 600;
        margin-right: 6px;
        display: inline-block;
    }
    .dif-badge {
        background: #fef3c7;
        color: #b45309;
        border: 1px solid #fde68a;
        padding: 4px 11px;
        border-radius: 999px;
        font-size: 12px;
        font-weight: 700;
        display: inline-block;
    }
    .enunciado-box {
        background: #f8fafc;
        border-left: 5px solid #2563eb;
        padding: 18px;
        font-size: 15.5px;
        font-weight: 600;
        color: #0f172a;
        border-radius: 0 10px 10px 0;
        margin: 14px 0;
        line-height: 1.6;
    }
    .feedback-ok {
        background: #f0fdf4;
        border: 1px solid #bbf7d0;
        border-left: 6px solid #16a34a;
        padding: 16px;
        border-radius: 10px;
        margin-top: 12px;
        color: #14532d;
    }
    .feedback-err {
        background: #fef2f2;
        border: 1px solid #fecaca;
        border-left: 6px solid #dc2626;
        padding: 16px;
        border-radius: 10px;
        margin-top: 12px;
        color: #7f1d1d;
    }
    .plan-card {
        background: #ffffff;
        border: 2px solid #e2e8f0;
        border-radius: 16px;
        padding: 22px;
        text-align: center;
        height: 100%;
        box-shadow: 0 4px 15px rgba(0,0,0,0.04);
    }
    .plan-card-popular {
        background: linear-gradient(180deg, #ffffff 0%, #eff6ff 100%);
        border: 2px solid #2563eb;
        border-radius: 16px;
        padding: 22px;
        text-align: center;
        height: 100%;
        box-shadow: 0 10px 25px rgba(37, 99, 235, 0.15);
    }
    .plan-price { font-size: 32px; font-weight: 800; color: #1d4ed8; margin: 8px 0; }
    .btn-pay {
        display: block;
        background: #16a34a;
        color: white !important;
        font-weight: 700;
        padding: 10px 16px;
        border-radius: 10px;
        text-decoration: none;
        margin-top: 12px;
        font-size: 14px;
    }
    .btn-pse {
        display: block;
        background: #1e40af;
        color: white !important;
        font-weight: 700;
        padding: 10px 16px;
        border-radius: 10px;
        text-decoration: none;
        margin-top: 8px;
        font-size: 13.5px;
    }
</style>
""",
    unsafe_allow_html=True,
)


@dataclass
class Pagina:
  doc: str
  pag: int
  texto: str


@dataclass
class PerfilManual:
  nombre_archivo: str
  entidad: str
  cargo: str
  codigo_grado: str
  nivel: str
  proposito: str
  funciones_esenciales: List[str] = field(default_factory=list)
  conocimientos_ejes: List[str] = field(default_factory=list)
  competencias_funcionales: List[str] = field(default_factory=list)
  competencias_comportamentales: List[str] = field(default_factory=list)
  requisitos: str = ""


# ==========================================
# INICIALIZACIÓN DE ESTADO (100% VACÍO / LIMPIO)
# ==========================================
if "perfiles" not in st.session_state:
  st.session_state.perfiles = {}
if "manuales_texto" not in st.session_state:
  st.session_state.manuales_texto = {}
if "paginas" not in st.session_state:
  st.session_state.paginas = []
if "puntaje" not in st.session_state:
  st.session_state.puntaje = 0
if "total" not in st.session_state:
  st.session_state.total = 0
if "usos_gratis" not in st.session_state:
  st.session_state.usos_gratis = 0
if "licencia_info" not in st.session_state:
  st.session_state.licencia_info = {"activa": False, "cedula": "", "vence": ""}
if "modo_examen" not in st.session_state:
  st.session_state.modo_examen = False
if "examen_qs" not in st.session_state:
  st.session_state.examen_qs = []
if "examen_idx" not in st.session_state:
  st.session_state.examen_idx = 0
if "examen_res" not in st.session_state:
  st.session_state.examen_res = []
if "examen_t0" not in st.session_state:
  st.session_state.examen_t0 = 0.0

MODELOS_GEMINI = ["gemini-2.5-flash", "gemini-2.5-pro"]

# ==========================================
# SISTEMA DE LICENCIAS TEMPORALES
# ==========================================


def generar_licencia_temporal(cedula: str, diasVigencia: int) -> str:
  fecha_vence = (
      datetime.date.today() + datetime.timedelta(days=diasVigencia)
  ).strftime("%Y%m%d")
  limpia = cedula.strip().lower()
  semilla = f"{limpia}|{fecha_vence}|{CLAVE_MAESTRA_ADMIN}"
  firma = hashlib.sha256(semilla.encode()).hexdigest().upper()[:8]
  return f"PRO-{fecha_vence}-{firma}"


def verificar_licencia_temporal(cedula: str, codigo: str) -> Tuple[bool, str]:
  cod = codigo.strip().upper()
  limpia = cedula.strip().lower()
  if not limpia or not cod.startswith("PRO-"):
    return False, "Formato de código o documento inválido."
  partes = cod.split("-")
  if len(partes) != 3:
    return False, "El código debe tener el formato PRO-AAAAMMDD-XXXXXXXX."
  _, fecha_str, firma_recibida = partes
  semilla = f"{limpia}|{fecha_str}|{CLAVE_MAESTRA_ADMIN}"
  firma_esperada = hashlib.sha256(semilla.encode()).hexdigest().upper()[:8]
  if firma_recibida != firma_esperada:
    return False, "El código no corresponde a este número de documento."
  try:
    fecha_vence = datetime.datetime.strptime(fecha_str, "%Y%m%d").date()
    if datetime.date.today() > fecha_vence:
      return False, f"Tu licencia venció el {fecha_vence.strftime('%d/%m/%Y')}."
    return True, fecha_vence.strftime("%d/%m/%Y")
  except Exception:
    return False, "Fecha de licencia corrupta."


# ==========================================
# FUNCIONES DE IA Y EXTRACCIÓN DE MANUALES
# ==========================================


def llamar_gemini(client, prompt: str) -> Optional[str]:
  if not client:
    return None
  for mod in MODELOS_GEMINI:
    for intento in range(2):
      try:
        r = client.models.generate_content(model=mod, contents=prompt)
        if r and r.text:
          return r.text
      except Exception as e:
        msg = str(e).lower()
        if "429" in msg or "quota" in msg or "resource_exhausted" in msg:
          st.warning("⚠️ Límite de velocidad superado. Espera unos segundos y reintenta.")
          return None
        if intento == 0:
          time.sleep(1.2)
          continue
        break
  return None


def extraer_pdf(nombre: str, datos: bytes) -> Tuple[str, List[Pagina]]:
  pags = []
  full_txt = ""
  try:
    doc = fitz.open(stream=datos, filetype="pdf")
    for i in range(len(doc)):
      t = doc[i].get_text("text").strip()
      if t:
        pags.append(Pagina(nombre, i + 1, t))
        full_txt += f"\n--- PÁGINA {i+1} ---\n" + t
    doc.close()
    return full_txt, pags
  except Exception as e:
    st.error(f"Error al leer {nombre}: {e}")
    return "", []


def analizar_manual_universal(client, nombre_archivo: str, texto: str) -> Optional[PerfilManual]:
  muestra = texto[:28000]
  prompt = f"""
  Eres un experto en análisis de Manuales Específicos de Funciones y Competencias Laborales de Colombia (CNSC, DIAN, Contraloría, Alcaldías, Gobernaciones, Entidades Nacionales).
  Analiza el siguiente Manual de Funciones y extrae su estructura con total fidelidad:
  {muestra}

  DEVUELVE ÚNICAMENTE JSON VÁLIDO (sin bloques markdown):
  {{
    "entidad": "Nombre de la entidad pública",
    "cargo": "Denominación exacta del empleo",
    "codigo_grado": "Código, Grado y Ficha si aparece",
    "nivel": "Nivel jerárquico y dependencia",
    "proposito": "Propósito principal del empleo",
    "funciones_esenciales": ["Función 1...", "Función 2...", "Función 3..."],
    "conocimientos_ejes": ["Eje temático o conocimiento básico 1...", "Conocimiento 2..."],
    "competencias_funcionales": ["Competencia funcional 1..."],
    "competencias_comportamentales": ["Competencia comportamental 1..."],
    "requisitos": "Requisitos de estudio y experiencia"
  }}
  """
  raw = llamar_gemini(client, prompt)
  if not raw:
    return None
  try:
    limpio = re.sub(r"```(?:json)?", "", raw.strip())
    limpio = re.sub(r"```", "", limpio).strip()
    m = re.search(r"\{.*\}", limpio, re.DOTALL)
    if m:
      limpio = m.group(0)
    d = json.loads(limpio)
    return PerfilManual(
        nombre_archivo=nombre_archivo,
        entidad=d.get("entidad", "Entidad Pública"),
        cargo=d.get("cargo", "Cargo Público"),
        codigo_grado=d.get("codigo_grado", "N/A"),
        nivel=d.get("nivel", "Carrera Administrativa"),
        proposito=d.get("proposito", "Cumplir las funciones del empleo."),
        funciones_esenciales=d.get("funciones_esenciales", []),
        conocimientos_ejes=d.get("conocimientos_ejes", []),
        competencias_funcionales=d.get("competencias_funcionales", []),
        competencias_comportamentales=d.get("competencias_comportamentales", []),
        requisitos=d.get("requisitos", "Según manual de funciones."),
    )
  except Exception:
    return None


def generar_pregunta_por_eje(
    client, perfil: PerfilManual, modalidad_eje: str, item_especifico: str, dificultad: str
) -> Optional[dict]:
  if modalidad_eje.startswith("🎲 Aleatoria Integral"):
    categorias = [
        ("FUNCIÓN ESENCIAL", perfil.funciones_esenciales),
        ("EJE TEMÁTICO", perfil.conocimientos_ejes),
        ("COMPETENCIA FUNCIONAL", perfil.competencias_funcionales),
        ("COMPETENCIA COMPORTAMENTAL", perfil.competencias_comportamentales),
    ]
    validas = [(n, l) for n, l in categorias if l]
    if not validas:
      foco_evaluacion = f"FUNCIÓN GENERAL: {perfil.proposito}"
    else:
      n_cat, l_items = random.choice(validas)
      foco_evaluacion = f"{n_cat}: {random.choice(l_items)}"
  elif modalidad_eje.startswith("📋 Solo Funciones"):
    foco_evaluacion = "FUNCIÓN ESENCIAL: " + (
        random.choice(perfil.funciones_esenciales) if perfil.funciones_esenciales else perfil.proposito
    )
  elif modalidad_eje.startswith("📘 Solo Ejes Temáticos"):
    comb = perfil.conocimientos_ejes + perfil.competencias_funcionales
    foco_evaluacion = "EJE TEMÁTICO: " + (random.choice(comb) if comb else perfil.proposito)
  elif modalidad_eje.startswith("🤝 Solo Competencias"):
    foco_evaluacion = "COMPETENCIA COMPORTAMENTAL: " + (
        random.choice(perfil.competencias_comportamentales)
        if perfil.competencias_comportamentales
        else "Integridad y Trabajo en equipo"
    )
  else:
    foco_evaluacion = f"ENFOQUE: {item_especifico}"

  texto_manual = st.session_state.manuales_texto.get(perfil.nombre_archivo, perfil.proposito)[:8000]

  prompt = f"""Actúa como experto constructor de pruebas escritas de Juicio Situacional para concursos públicos en Colombia (CNSC, DIAN, Contraloría).
ENTIDAD: {perfil.entidad}
CARGO: {perfil.cargo} ({perfil.codigo_grado})
PROPÓSITO: {perfil.proposito}
EJE A EVALUAR: {foco_evaluacion}
DIFICULTAD: {dificultad}

MANUAL DE REFERENCIA:
{texto_manual}

Crea un caso situacional realista con 4 opciones (A, B, C, D) donde solo una sea correcta y justificada.
DEVUELVE ÚNICAMENTE JSON VÁLIDO (sin markdown):
{{"eje_evaluado":"{foco_evaluacion[:90]}","pregunta":"...","opciones":{{"A":"...","B":"...","C":"...","D":"..."}},"correcta":"A","explicacion":"...","tip_estrategico":"...","fuente":"{perfil.nombre_archivo}","fragmento_soporte":"..."}}"""

  raw = llamar_gemini(client, prompt)
  if not raw:
    return None
  try:
    limpio = re.sub(r"```(?:json)?", "", raw.strip())
    limpio = re.sub(r"```", "", limpio).strip()
    m = re.search(r"\{.*\}", limpio, re.DOTALL)
    if m:
      limpio = m.group(0)
    data = json.loads(limpio)
    if not isinstance(data.get("opciones"), dict) or data.get("correcta") not in ["A", "B", "C", "D"]:
      return None
    data["_id"] = hashlib.md5(data["pregunta"].encode()).hexdigest()
    return data
  except Exception:
    return None


# ==========================================
# BARRA LATERAL (SIDEBAR)
# ==========================================
st.sidebar.markdown("## 🏛️ Mérito PRO Colombia")

lic = st.session_state.licencia_info
if lic["activa"]:
  st.sidebar.success(f"👑 **PLAN PRO ACTIVO**\n\nID: `{lic['cedula']}`\nVence: **{lic['vence']}**")
else:
  disp = max(0, LIMITE_PREGUNTAS_GRATIS - st.session_state.usos_gratis)
  st.sidebar.warning(f"🎁 **Modo Prueba Gratis:** Te quedan **{disp}** preguntas.")

st.sidebar.markdown("---")
st.sidebar.subheader("🔑 1. Tu Clave Gratuita de IA")
api_key_user = st.sidebar.text_input(
    "Pega tu GEMINI_API_KEY personal:",
    type="password",
    help="Cada usuario usa su propia clave de Google AI Studio.",
)
with st.sidebar.expander("❓ ¿Cómo obtener mi clave en 30 seg?"):
  st.markdown(
      """
      1. Entra gratis a [**Google AI Studio**](https://aistudio.google.com/apikey).
      2. Haz clic en **"Create API key"**.
      3. Copia el código y pégalo arriba.
      """
  )

client = genai.Client(api_key=api_key_user.strip()) if api_key_user.strip() else None

st.sidebar.markdown("---")
st.sidebar.subheader("📂 2. Sube tu Manual OPEC")
archivos_up = st.sidebar.file_uploader(
    "Carga el Manual de Funciones en PDF o TXT",
    type=["pdf", "txt"],
    accept_multiple_files=True,
)

if archivos_up:
  for arc in archivos_up:
    if arc.name not in st.session_state.manuales_texto:
      b_data = arc.read()
      if arc.name.lower().endswith(".pdf"):
        txt_doc, pags = extraer_pdf(arc.name, b_data)
      else:
        txt_doc = b_data.decode("utf-8", errors="ignore")
        pags = [Pagina(arc.name, 1, txt_doc)]

      if txt_doc.strip():
        st.session_state.manuales_texto[arc.name] = txt_doc
        st.session_state.paginas.extend(pags)
        if client:
          with st.spinner(f"Analizando {arc.name} con IA..."):
            nuevo_p = analizar_manual_universal(client, arc.name, txt_doc)
            if nuevo_p:
              st.session_state.perfiles[arc.name] = nuevo_p
              st.sidebar.success(f"✅ ¡Cargo detectado: {nuevo_p.cargo}!")
        else:
          st.sidebar.info(f"📄 {arc.name} cargado. Ingresa tu API Key para perfilarlo.")

nombres_manuales = list(st.session_state.perfiles.keys())

if not nombres_manuales:
  st.sidebar.warning("⚠️ Sube un Manual de Funciones (PDF) para comenzar.")
  perfil_activo = PerfilManual(
      nombre_archivo="ninguno",
      entidad="Esperando documento...",
      cargo="Sube tu Manual de Funciones",
      codigo_grado="N/A",
      nivel="Sin perfil activo",
      proposito="Por favor, usa el botón de carga superior para subir el manual o ficha OPEC del concurso al que te postulas.",
  )
else:
  manual_activo_key = st.sidebar.selectbox("Selecciona el Cargo:", nombres_manuales)
  perfil_activo = st.session_state.perfiles[manual_activo_key]

st.sidebar.markdown("---")
st.sidebar.subheader("🎯 3. Modo de Entrenamiento")
modalidad_eje = st.sidebar.selectbox(
    "¿Sobre qué quieres que te pregunte la IA?",
    [
        "🎲 Aleatoria Integral (Mezcla Funciones + Ejes + Comportamentales)",
        "📋 Solo Funciones Esenciales",
        "📘 Solo Ejes Temáticos",
        "🤝 Solo Competencias Comportamentales",
    ],
)

dificultad = st.sidebar.select_slider(
    "Nivel de Dificultad", options=["Básica", "Alta", "Muy Alta (Nivel CNSC)"], value="Alta"
)
cantidad_simulacro = st.sidebar.selectbox("Preguntas por Simulacro", [3, 5, 10, 20], index=1)

st.sidebar.markdown("---")
with st.sidebar.expander("🔐 Activar mi Código PRO"):
  ced_cli = st.text_input("Tu Cédula:", key="input_ced_cli")
  cod_cli = st.text_input("Código PRO:", key="input_cod_cli")
  if st.button("Activar Acceso 👑", use_container_width=True):
    ok_lic, msg_lic = verificar_licencia_temporal(ced_cli, cod_cli)
    if ok_lic:
      st.session_state.licencia_info = {"activa": True, "cedula": ced_cli.strip(), "vence": msg_lic}
      st.success("🎉 ¡Licencia activada!")
      time.sleep(1)
      st.rerun()
    else:
      st.error(msg_lic)

with st.sidebar.expander("🛠️ Panel Admin (Omar)"):
  pwd_admin = st.text_input("Contraseña Admin:", type="password")
  if pwd_admin == CLAVE_MAESTRA_ADMIN:
    ced_comprador = st.text_input("Cédula que pagó:")
    plan_dias = st.selectbox(
        "Plan:",
        [(7, "7 Días ($14.900)"), (30, "30 Días ($24.900)"), (180, "6 Meses ($39.900)")],
        format_func=lambda x: x[1],
    )
    if ced_comprador:
      token_gen = generar_licencia_temporal(ced_comprador, plan_dias[0])
      st.code(f"Cédula: {ced_comprador}\nCódigo: {token_gen}")

# ==========================================
# CABECERA PRINCIPAL Y KPIS
# ==========================================
st.markdown(
    f"""
<div class="hero-box">
    <div class="hero-tag">🇨🇴 ENTRENADOR OFICIAL DE MÉRITOS • {html.escape(perfil_activo.entidad.upper())}</div>
    <h1 class="hero-title">{html.escape(perfil_activo.cargo)} — {html.escape(perfil_activo.codigo_grado)}</h1>
    <p class="hero-sub"><b>Propósito del Cargo:</b> {html.escape(perfil_activo.proposito)}</p>
</div>
""",
    unsafe_allow_html=True,
)

precision_global = (
    (st.session_state.puntaje / st.session_state.total * 100)
    if st.session_state.total > 0
    else 0.0
)

k1, k2, k3, k4 = st.columns(4)
with k1:
  st.markdown(
      f'<div class="kpi-box"><div class="kpi-label">Casos Resueltos</div><div class="kpi-num">{st.session_state.total}</div></div>',
      unsafe_allow_html=True,
  )
with k2:
  st.markdown(
      f'<div class="kpi-box"><div class="kpi-label">Efectividad</div><div class="kpi-num" style="color:#2563eb;">{precision_global:.1f}%</div></div>',
      unsafe_allow_html=True,
  )
with k3:
  total_items = (
      len(perfil_activo.funciones_esenciales)
      + len(perfil_activo.conocimientos_ejes)
      + len(perfil_activo.competencias_funcionales)
      + len(perfil_activo.competencias_comportamentales)
  )
  st.markdown(
      f'<div class="kpi-box"><div class="kpi-label">Funciones y Ejes</div><div class="kpi-num">{total_items}</div></div>',
      unsafe_allow_html=True,
  )
with k4:
  est_txt = (
      f"PRO (Vence {lic['vence']})"
      if lic["activa"]
      else f"DEMO ({max(0, LIMITE_PREGUNTAS_GRATIS - st.session_state.usos_gratis)} disp.)"
  )
  st.markdown(
      f'<div class="kpi-box"><div class="kpi-label">Estado</div><div class="kpi-num" style="font-size:15px; color:#16a34a;">{est_txt}</div></div>',
      unsafe_allow_html=True,
  )

st.write("")

tab_sim, tab_ficha, tab_comp, tab_planes = st.tabs([
    "🎯 Simulador Inteligente",
    "📋 Radiografía del Manual",
    "🔄 Comparador de Manuales",
    "💎 Planes de Acceso (Nequi / PSE)",
])


def renderizar_planes_pago():
  st.markdown(
      """
      <div style="text-align:center; margin-bottom:18px;">
          <h3>🚀 Elige tu Plan de Entrenamiento</h3>
          <p style="color:#475569;">Sube el manual de funciones de tu concurso y entrena con casos situacionales ilimitados.</p>
      </div>
      """,
      unsafe_allow_html=True,
  )

  p1, p2, p3 = st.columns(3)
  with p1:
    wa_1 = f"https://wa.me/{WHATSAPP_INTL}?text=Hola,%20pagué%20el%20Pase%20Intensivo%20de%20$14.900%20(7%20días)%20a%20Nequi%20{NUMERO_NEQUI_WHATSAPP}.%20Mi%20cédula%20es:%20"
    st.markdown(
        f"""
        <div class="plan-card">
            <span class="eje-badge">⚡ COMPRA RÁPIDA</span>
            <h4 style="margin:10px 0 4px 0;">Pase Intensivo (7 Días)</h4>
            <div class="plan-price">$14.900 <small style="font-size:13px; color:#64748b;">COP</small></div>
            <hr>
            <div style="text-align:left; font-size:13.5px; line-height:1.7;">
                ✅ <b>7 días</b> de acceso ilimitado.<br>
                ✅ Sube tus manuales en PDF.<br>
                ✅ Preguntas por funciones y ejes.
            </div>
            <a href="{wa_1}" target="_blank" class="btn-pay">📲 Pagar $14.900 y Pedir Código</a>
            <a href="{URL_PSE_NEQUI}" target="_blank" class="btn-pse">🏦 Pagar por PSE a Nequi {NUMERO_NEQUI_WHATSAPP}</a>
        </div>
        """,
        unsafe_allow_html=True,
    )
  with p2:
    wa_2 = f"https://wa.me/{WHATSAPP_INTL}?text=Hola,%20pagué%20el%20Pase%20Mensual%20PRO%20de%20$24.900%20(30%20días)%20a%20Nequi%20{NUMERO_NEQUI_WHATSAPP}.%20Mi%20cédula%20es:%20"
    st.markdown(
        f"""
        <div class="plan-card-popular">
            <span class="dif-badge">⭐ RECOMENDADO</span>
            <h4 style="margin:10px 0 4px 0;">Pase Mensual PRO (30 Días)</h4>
            <div class="plan-price">$24.900 <small style="font-size:13px; color:#64748b;">COP</small></div>
            <hr>
            <div style="text-align:left; font-size:13.5px; line-height:1.7;">
                ✅ <b>30 días completos</b> de acceso.<br>
                ✅ Carga ilimitada de manuales y leyes.<br>
                ✅ Simulacros cronometrados.
            </div>
            <a href="{wa_2}" target="_blank" class="btn-pay">📲 Pagar $24.900 y Activar</a>
            <a href="{URL_PSE_NEQUI}" target="_blank" class="btn-pse">🏦 Pagar por PSE a Nequi {NUMERO_NEQUI_WHATSAPP}</a>
        </div>
        """,
        unsafe_allow_html=True,
    )
  with p3:
    wa_3 = f"https://wa.me/{WHATSAPP_INTL}?text=Hola,%20pagué%20el%20Pase%20Convocatoria%20de%20$39.900%20(6%20meses)%20a%20Nequi%20{NUMERO_NEQUI_WHATSAPP}.%20Mi%20cédula%20es:%20"
    st.markdown(
        f"""
        <div class="plan-card">
            <span class="eje-badge">👑 MÁXIMO AHORRO</span>
            <h4 style="margin:10px 0 4px 0;">Pase Convocatoria (6 Meses)</h4>
            <div class="plan-price">$39.900 <small style="font-size:13px; color:#64748b;">COP</small></div>
            <hr>
            <div style="text-align:left; font-size:13.5px; line-height:1.7;">
                ✅ <b>180 días</b> de acceso total.<br>
                ✅ Sirve para cualquier concurso CNSC.<br>
                ✅ Máximo ahorro semestral.
            </div>
            <a href="{wa_3}" target="_blank" class="btn-pay">📲 Pagar $39.900 y Pedir Código</a>
            <a href="{URL_PSE_NEQUI}" target="_blank" class="btn-pse">🏦 Pagar por PSE a Nequi {NUMERO_NEQUI_WHATSAPP}</a>
        </div>
        """,
        unsafe_allow_html=True,
    )

  st.info(
      f"💡 **Cómo pagar:** Transfiere a Nequi **`{NUMERO_NEQUI_WHATSAPP}`** (o por PSE en el botón azul) y envíanos el comprobante por WhatsApp."
  )


with tab_sim:
  if not client:
    st.info("👈 **Paso 1:** Pega tu clave **`GEMINI_API_KEY`** en la barra lateral izquierda para comenzar.")
  elif not nombres_manuales:
    st.warning("📂 **Paso 2:** Sube el Manual de Funciones o ficha OPEC en PDF mediante la barra lateral para generar preguntas de tu concurso.")
  else:
    bloqueado = not lic["activa"] and st.session_state.usos_gratis >= LIMITE_PREGUNTAS_GRATIS
    if bloqueado:
      st.error(
          f"🔒 Has completado tus {LIMITE_PREGUNTAS_GRATIS} preguntas gratis. ¡Elige tu plan desde $14.900 COP!"
      )
      renderizar_planes_pago()
    else:
      b1, b2 = st.columns(2)
      with b1:
        btn_una = st.button(
            "🎲 Generar Caso Práctico Aleatorio", type="primary", use_container_width=True
        )
      with b2:
        btn_lote = st.button(
            f"⏱️ Iniciar Simulacro ({cantidad_simulacro} Preguntas)", use_container_width=True
        )

      if btn_lote:
        if not lic["activa"]:
          st.warning("🔒 El simulacro múltiple es exclusivo para usuarios con Plan Activo.")
        else:
          with st.spinner("Construyendo simulacro..."):
            lote = []
            vistos = set()
            for _ in range(cantidad_simulacro * 2):
              if len(lote) >= cantidad_simulacro:
                break
              q_c = generar_pregunta_por_eje(
                  client, perfil_activo, modalidad_eje, "", dificultad
              )
              if q_c and q_c["_id"] not in vistos:
                vistos.add(q_c["_id"])
                lote.append(q_c)
            if lote:
              st.session_state.modo_examen = True
              st.session_state.examen_qs = lote
              st.session_state.examen_idx = 0
              st.session_state.examen_res = []
              st.session_state.examen_t0 = time.time()
              st.rerun()

      if st.session_state.modo_examen:
        qs = st.session_state.examen_qs
        idx = st.session_state.examen_idx
        if idx < len(qs):
          q = qs[idx]
          st.progress((idx + 1) / len(qs), text=f"Pregunta {idx + 1} de {len(qs)}")
          st.markdown(
              f"""
              <div class="saas-card">
                  <span class="eje-badge">🎯 {html.escape(q.get('eje_evaluado', ''))}</span>
                  <div class="enunciado-box">{html.escape(q['pregunta'])}</div>
              </div>
              """,
              unsafe_allow_html=True,
          )
          eleccion = st.radio(
              "Respuesta:", ["A", "B", "C", "D"], format_func=lambda x: f"{x}) {q['opciones'][x]}"
          )
          if st.button("Confirmar y Siguiente ➡️", type="primary"):
            acierto = eleccion == q["correcta"]
            st.session_state.examen_res.append({
                "q": q["pregunta"],
                "eje": q.get("eje_evaluado", ""),
                "elegida": eleccion,
                "correcta": q["correcta"],
                "ok": acierto,
                "exp": q.get("explicacion", ""),
            })
            st.session_state.total += 1
            if acierto:
              st.session_state.puntaje += 1
            st.session_state.examen_idx += 1
            st.rerun()
        else:
          res = st.session_state.examen_res
          ok_cnt = sum(1 for r in res if r["ok"])
          tot_cnt = len(res)
          pct = (ok_cnt / tot_cnt * 100) if tot_cnt else 0
          st.markdown(
              f"""
              <div class="saas-card" style="text-align:center;">
                  <h2>{'🏆 ¡APROBADO!' if pct >= 65 else '📚 SIGUE REPASANDO'}</h2>
                  <p>Aciertos: <b>{ok_cnt} de {tot_cnt} ({pct:.1f}%)</b></p>
              </div>
              """,
              unsafe_allow_html=True,
          )
          if st.button("🔄 Volver", type="primary"):
            st.session_state.modo_examen = False
            st.rerun()
      else:
        if btn_una or "q_actual" not in st.session_state:
          with st.spinner("Diseñando caso práctico..."):
            q_nueva = generar_pregunta_por_eje(client, perfil_activo, modalidad_eje, "", dificultad)
            if q_nueva:
              st.session_state.q_actual = q_nueva
              st.session_state.q_respondida = False
              if btn_una or st.session_state.usos_gratis == 0:
                st.session_state.usos_gratis += 1
            else:
              st.error("Error al generar la pregunta. Verifica tu API Key.")
              st.stop()

        if "q_actual" in st.session_state:
          q = st.session_state.q_actual
          st.markdown(
              f"""
              <div class="saas-card">
                  <span class="eje-badge">📌 {html.escape(q.get('eje_evaluado', ''))}</span>
                  <div class="enunciado-box">{html.escape(q['pregunta'])}</div>
              </div>
              """,
              unsafe_allow_html=True,
          )

          op_sel = st.radio(
              "Elige la opción correcta:",
              ["A", "B", "C", "D"],
              format_func=lambda x: f"{x}) {q['opciones'][x]}",
              key=f"prac_{q['_id']}",
          )

          if not st.session_state.q_respondida:
            if st.button("✅ Validar Respuesta", type="primary"):
              st.session_state.q_respondida = True
              st.session_state.total += 1
              if op_sel == q["correcta"]:
                st.session_state.puntaje += 1
              st.rerun()
          else:
            corr = q["correcta"]
            if op_sel == corr:
              st.markdown(
                  f'<div class="feedback-ok"><h4>🎉 ¡Correcto! Opción {corr}</h4><p>{html.escape(q["explicacion"])}</p></div>',
                  unsafe_allow_html=True,
              )
            else:
              st.markdown(
                  f'<div class="feedback-err"><h4>❌ Incorrecto (Elegiste {op_sel}, era la {corr})</h4><p>{html.escape(q["explicacion"])}</p></div>',
                  unsafe_allow_html=True,
              )

            if st.button("➡️ Siguiente Pregunta", type="primary"):
              del st.session_state.q_actual
              st.session_state.q_respondida = False
              st.rerun()

with tab_ficha:
  st.markdown(
      f"""
      <div class="saas-card">
          <h3>{html.escape(perfil_activo.cargo)} ({html.escape(perfil_activo.codigo_grado)})</h3>
          <p><b>Entidad:</b> {html.escape(perfil_activo.entidad)}</p>
          <p><b>Propósito:</b> {html.escape(perfil_activo.proposito)}</p>
      </div>
      """,
      unsafe_allow_html=True,
  )

with tab_comp:
  st.markdown("#### 🔄 Comparador de Manuales")
  if len(nombres_manuales) < 2:
    st.info("Sube al menos dos manuales diferentes en la barra lateral para poder compararlos.")
  else:
    c1, c2 = st.columns(2)
    with c1:
      m1 = st.selectbox("Manual 1:", nombres_manuales, index=0)
      pm1 = st.session_state.perfiles[m1]
      st.markdown(f"**{pm1.cargo}** — *{pm1.entidad}*")
    with c2:
      m2 = st.selectbox("Manual 2:", nombres_manuales, index=1)
      pm2 = st.session_state.perfiles[m2]
      st.markdown(f"**{pm2.cargo}** — *{pm2.entidad}*")

with tab_planes:
  renderizar_planes_pago()
