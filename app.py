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
CLAVE_MAESTRA_ADMIN = "OMAR2026"  # Cámbiala si deseas otra clave para tu generador de licencias
LIMITE_PREGUNTAS_GRATIS = 2

# ==========================================
# CONFIGURACIÓN DE PÁGINA Y ESTILOS SAAS
# ==========================================
st.set_page_config(
    page_title="Mérito PRO | Simulador Inteligente CNSC, DIAN y Contraloría",
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

# ==========================================
# SISTEMA DE LICENCIAS CON FECHA DE VENCIMIENTO
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
      return False, f"Tu licencia venció el {fecha_vence.strftime('%d/%m/%Y')}. Renueva tu plan por Nequi."
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
          st.warning("⚠️ Tu clave de API alcanzó el límite de velocidad por minuto. Espera 20 segundos y vuelve a intentar.")
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

  Analiza el siguiente Manual de Funciones y extrae toda su estructura con total fidelidad:
  {muestra}

  DEVUELVE ÚNICAMENTE ESTE JSON VÁLIDO (sin bloques markdown):
  {{
    "entidad": "Nombre de la entidad pública (ej. DIAN, Contraloría, Alcaldía, etc.)",
    "cargo": "Denominación exacta del empleo (ej. Gestor I, Secretario, Profesional Universitario)",
    "codigo_grado": "Código, Grado y Ficha si aparece (ej. Código 301 Grado 01)",
    "nivel": "Nivel jerárquico y proceso o dependencia (ej. Profesional / Fiscalización)",
    "proposito": "Propósito principal del empleo textual o resumido con precisión",
    "funciones_esenciales": ["Función 1...", "Función 2...", "Función 3..."],
    "conocimientos_ejes": ["Eje o conocimiento básico 1...", "Conocimiento 2..."],
    "competencias_funcionales": ["Competencia funcional 1...", "Competencia funcional 2..."],
    "competencias_comportamentales": ["Competencia comportamental 1...", "Competencia 2..."],
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
        proposito=d.get("proposito", "Cumplir las funciones asignadas al cargo."),
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
  # Selección inteligente o aleatoria del eje a evaluar
  if modalidad_eje.startswith("🎲 Aleatoria Integral"):
    categorias = [
        ("FUNCIÓN ESENCIAL DEL CARGO", perfil.funciones_esenciales),
        ("EJE TEMÁTICO / CONOCIMIENTO ESENCIAL", perfil.conocimientos_ejes),
        ("COMPETENCIA FUNCIONAL", perfil.competencias_funcionales),
        ("COMPETENCIA COMPORTAMENTAL (Juicio Situacional)", perfil.competencias_comportamentales),
    ]
    categorias_validas = [(nombre, lista) for nombre, lista in categorias if lista]
    cat_nombre, lista_items = random.choice(categorias_validas)
    foco_evaluacion = f"{cat_nombre}: {random.choice(lista_items)}"
  elif modalidad_eje.startswith("📋 Solo Funciones"):
    foco_evaluacion = "FUNCIÓN ESENCIAL: " + (
        random.choice(perfil.funciones_esenciales) if perfil.funciones_esenciales else perfil.proposito
    )
  elif modalidad_eje.startswith("📘 Solo Ejes Temáticos"):
    combinada = perfil.conocimientos_ejes + perfil.competencias_funcionales
    foco_evaluacion = "EJE TEMÁTICO / FUNCIONAL: " + (
        random.choice(combinada) if combinada else perfil.proposito
    )
  elif modalidad_eje.startswith("🤝 Solo Competencias Comportamentales"):
    foco_evaluacion = "COMPETENCIA COMPORTAMENTAL: " + (
        random.choice(perfil.competencias_comportamentales)
        if perfil.competencias_comportamentales
        else "Comportamiento Ético, Adaptabilidad y Trabajo en Equipo"
    )
  else:
    foco_evaluacion = f"ENFOQUE ESPECÍFICO: {item_especifico}"

  texto_manual = st.session_state.manuales_texto.get(
      perfil.nombre_archivo, construir_texto_desde_perfil(perfil)
  )[:8000]

  prompt = f"""Actúa como un experto constructor de pruebas escritas de Juicio Situacional para concursos públicos de méritos en Colombia (CNSC, DIAN, Contraloría, Universidad Libre, UNAL, ESAP).

ENTIDAD: {perfil.entidad}
CARGO A EVALUAR: {perfil.cargo} ({perfil.codigo_grado}) - {perfil.nivel}
PROPÓSITO PRINCIPAL: {perfil.proposito}
EJE SELECCIONADO PARA ESTA PREGUNTA: {foco_evaluacion}
DIFICULTAD: {dificultad}

TEXTO DEL MANUAL DE FUNCIONES DE REFERENCIA:
{texto_manual}

INSTRUCCIONES DE DISEÑO:
1. Crea un CASO SITUACIONAL REALISTA ubicado en la oficina o dependencia del cargo ({perfil.cargo} en {perfil.entidad}), donde se presente un dilema técnico, normativo, procedimental o comportamental directamente relacionado con el EJE SELECCIONADO ({foco_evaluacion}).
2. Formula un enunciado claro y 4 opciones de actuación (A, B, C, D) redactadas con estilo oficial de prueba CNSC.
3. Solo UNA opción debe ser la respuesta correcta; las otras 3 deben ser distractores plausibles (errores comunes de procedimiento, vencimiento de términos o conductas que incumplen el nivel de la competencia).
4. En "explicacion", justifica detalladamente por qué la opción correcta es la única válida y por qué se descartan las demás.
5. En "fragmento_soporte", cita la función, competencia o conocimiento del manual que respalda la pregunta.

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

# Estado de Suscripción
lic = st.session_state.licencia_info
if lic["activa"]:
  st.sidebar.success(
      f"👑 **PLAN PRO ACTIVO**\n\nID: `{lic['cedula']}`\nVence: **{lic['vence']}**"
  )
else:
  disp = max(0, LIMITE_PREGUNTAS_GRATIS - st.session_state.usos_gratis)
  st.sidebar.warning(
      f"🎁 **Modo Prueba Gratis:** Te quedan **{disp}** de {LIMITE_PREGUNTAS_GRATIS} preguntas de demostración."
  )

# 1. Configuración Segura de API Key por cada Usuario (BYOK)
st.sidebar.markdown("---")
st.sidebar.subheader("🔑 1. Tu Clave Gratuita de IA")
api_key_user = st.sidebar.text_input(
    "Pega tu GEMINI_API_KEY personal:",
    type="password",
    help="Cada estudiante utiliza su propia clave gratuita de Google AI Studio. Tu clave es 100% privada en tu navegador.",
)
with st.sidebar.expander("❓ ¿Cómo obtener mi clave GRATIS en 30 seg?"):
  st.markdown(
      """
      1. Entra gratis a [**Google AI Studio (Clic aquí)**](https://aistudio.google.com/apikey) con tu correo de Gmail.
      2. Haz clic en el botón azul **"Create API key"**.
      3. Copia el código generado y pégalo arriba. ¡Es 100% gratis!
      """
  )

client = genai.Client(api_key=api_key_user.strip()) if api_key_user.strip() else None

# 2. Carga y Selección de Manual de Funciones
st.sidebar.markdown("---")
st.sidebar.subheader("📂 2. Sube tu Manual de Funciones")
archivos_up = st.sidebar.file_uploader(
    "Carga cualquier Manual OPEC (PDF o TXT)",
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
          with st.spinner(f"Analizando estructura de {arc.name} con IA..."):
            nuevo_p = analizar_manual_universal(client, arc.name, txt_doc)
            if nuevo_p:
              st.session_state.perfiles[arc.name] = nuevo_p
              st.sidebar.success(f"✅ Cargo detectado: {nuevo_p.cargo}")
        else:
          st.sidebar.info(f"📄 {arc.name} cargado. Ingresa tu API Key y presiona Re-analizar.")

nombres_manuales = list(st.session_state.perfiles.keys())
manual_activo_key = st.sidebar.selectbox(
    "Selecciona el Manual / Cargo para Entrenar:",
    nombres_manuales,
    index=0,
)
perfil_activo = st.session_state.perfiles[manual_activo_key]

# Si subieron un archivo sin API key, permitir analizarlo luego
archivos_sin_perfil = [
    k for k in st.session_state.manuales_texto.keys() if k not in st.session_state.perfiles
]
if archivos_sin_perfil and client:
  for k_pend in archivos_sin_perfil:
    if st.sidebar.button(f"🔍 Extraer Funciones de {k_pend}"):
      with st.spinner("Extrayendo funciones, ejes y competencias..."):
        p_ext = analizar_manual_universal(client, k_pend, st.session_state.manuales_texto[k_pend])
        if p_ext:
          st.session_state.perfiles[k_pend] = p_ext
          st.rerun()

# 3. Selector de Ejes de Entrenamiento
st.sidebar.markdown("---")
st.sidebar.subheader("🎯 3. Modo de Entrenamiento")
modalidad_eje = st.sidebar.selectbox(
    "¿Sobre qué quieres que te pregunte la IA?",
    [
        "🎲 Aleatoria Integral (Mezcla Funciones + Ejes + Comportamentales)",
        "📋 Solo Funciones Esenciales del Cargo",
        "📘 Solo Ejes Temáticos y Competencias Funcionales",
        "🤝 Solo Competencias Comportamentales",
        "🔍 Elegir una Función o Eje Específico...",
    ],
)

item_especifico = ""
if modalidad_eje.startswith("🔍"):
  todos_los_items = (
      [f"[Función] {x}" for x in perfil_activo.funciones_esenciales]
      + [f"[Conocimiento/Eje] {x}" for x in perfil_activo.conocimientos_ejes]
      + [f"[Funcional] {x}" for x in perfil_activo.competencias_funcionales]
      + [f"[Comportamental] {x}" for x in perfil_activo.competencias_comportamentales]
  )
  item_especifico = st.sidebar.selectbox("Selecciona el ítem exacto:", todos_los_items)

dificultad = st.sidebar.select_slider(
    "Nivel de Dificultad",
    options=["Básica", "Alta", "Muy Alta (Nivel Prueba CNSC/DIAN)"],
    value="Alta",
)
cantidad_simulacro = st.sidebar.selectbox("Preguntas por Simulacro", [3, 5, 10, 20], index=1)

# 4. Activación de Licencia del Cliente y Panel Admin de Omar
st.sidebar.markdown("---")
with st.sidebar.expander("🔐 Activar mi Código PRO (Clientes)"):
  ced_cli = st.text_input("Tu Número de Cédula:", key="input_ced_cli")
  cod_cli = st.text_input("Tu Código de Licencia PRO:", key="input_cod_cli")
  if st.button("Activar Acceso Ilimitado 👑", use_container_width=True):
    ok_lic, msg_lic = verificar_licencia_temporal(ced_cli, cod_cli)
    if ok_lic:
      st.session_state.licencia_info = {
          "activa": True,
          "cedula": ced_cli.strip(),
          "vence": msg_lic,
      }
      st.success(f"🎉 ¡Bienvenido! Plan activo hasta el {msg_lic}.")
      time.sleep(1)
      st.rerun()
    else:
      st.error(msg_lic)

with st.sidebar.expander("🛠️ Generador de Accesos (Solo Admin)"):
  pwd_admin = st.text_input("Contraseña de Administrador:", type="password")
  if pwd_admin == CLAVE_MAESTRA_ADMIN:
    st.markdown("**Generar licencia tras confirmar pago en Nequi:**")
    ced_comprador = st.text_input("Cédula del cliente que pagó:")
    plan_dias = st.selectbox(
        "Plan adquirido:",
        [
            (7, "⚡ Pase 7 Días ($14.900)"),
            (30, "⭐ Pase 30 Días ($24.900)"),
            (180, "👑 Pase 6 Meses ($39.900)"),
        ],
        format_func=lambda x: x[1],
    )
    if ced_comprador:
      token_generado = generar_licencia_temporal(ced_comprador, plan_dias[0])
      st.code(
          f"Cédula: {ced_comprador.strip()}\nCódigo PRO: {token_generado}\nVigencia: {plan_dias[0]} días"
      )
      st.caption("Copia y envíale este código a tu cliente por WhatsApp.")

# ==========================================
# CABECERA PRINCIPAL Y KPIS
# ==========================================
st.markdown(
    f"""
<div class="hero-box">
    <div class="hero-tag">🇨🇴 ENTRENADOR OFICIAL MULTICONCURSO • {html.escape(perfil_activo.entidad.upper())}</div>
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
  total_items_manual = (
      len(perfil_activo.funciones_esenciales)
      + len(perfil_activo.conocimientos_ejes)
      + len(perfil_activo.competencias_funcionales)
      + len(perfil_activo.competencias_comportamentales)
  )
  st.markdown(
      f'<div class="kpi-box"><div class="kpi-label">Funciones y Ejes del Cargo</div><div class="kpi-num">{total_items_manual}</div></div>',
      unsafe_allow_html=True,
  )
with k4:
  est_txt = (
      f"PRO (Vence {lic['vence']})"
      if lic["activa"]
      else f"DEMO ({max(0, LIMITE_PREGUNTAS_GRATIS - st.session_state.usos_gratis)} disp.)"
  )
  st.markdown(
      f'<div class="kpi-box"><div class="kpi-label">Estado de tu Cuenta</div><div class="kpi-num" style="font-size:16px; color:#16a34a;">{est_txt}</div></div>',
      unsafe_allow_html=True,
  )

st.write("")

# ==========================================
# PESTAÑAS DE LA PLATAFORMA
# ==========================================
tab_sim, tab_ficha, tab_comp, tab_planes = st.tabs([
    "🎯 Simulador Inteligente",
    "📋 Radiografía del Manual Activo",
    "🔄 Comparador de Manuales (DIAN vs Contraloría / Otros)",
    "💎 Planes de Acceso (Nequi / PSE)",
])


def renderizar_planes_de_pago():
  st.markdown(
      """
      <div style="text-align:center; margin-bottom:18px;">
          <h3>🚀 Elige tu Plan de Entrenamiento y Asegura tu Puesto en el Concurso</h3>
          <p style="color:#475569;">Sube cualquier Manual de Funciones (DIAN, Contraloría, CNSC, Gobernaciones, Alcaldías) y entrena sin límites con preguntas aleatorias sobre tus funciones reales.</p>
      </div>
      """,
      unsafe_allow_html=True,
  )

  p1, p2, p3 = st.columns(3)
  with p1:
    wa_1 = f"https://wa.me/{WHATSAPP_INTL}?text=Hola,%20acabo%20de%20pagar%20el%20Pase%20Intensivo%20de%20$14.900%20(7%20dias)%20a%20Nequi%20{NUMERO_NEQUI_WHATSAPP}.%20Mi%20cedula%20es:%20"
    st.markdown(
        f"""
        <div class="plan-card">
            <span class="eje-badge">⚡ COMPRA RÁPIDA</span>
            <h4 style="margin:10px 0 4px 0;">Pase Intensivo (7 Días)</h4>
            <div class="plan-price">$14.900 <small style="font-size:13px; color:#64748b;">COP</small></div>
            <p style="font-size:13px; color:#64748b;">Ideal para repaso final antes del examen</p>
            <hr>
            <div style="text-align:left; font-size:13.5px; line-height:1.7;">
                ✅ <b>7 días</b> de simulacros ilimitados.<br>
                ✅ Sube tus propios manuales en PDF.<br>
                ✅ Preguntas por Funciones, Ejes y Comportamentales.<br>
                ✅ Retroalimentación normativa inmediata.
            </div>
            <a href="{wa_1}" target="_blank" class="btn-pay">📲 Pagar $14.900 y Pedir Código</a>
            <a href="{URL_PSE_NEQUI}" target="_blank" class="btn-pse">🏦 Pagar por PSE a Nequi {NUMERO_NEQUI_WHATSAPP}</a>
        </div>
        """,
        unsafe_allow_html=True,
    )

  with p2:
    wa_2 = f"https://wa.me/{WHATSAPP_INTL}?text=Hola,%20acabo%20de%20pagar%20el%20Pase%20Mensual%20PRO%20de%20$24.900%20(30%20dias)%20a%20Nequi%20{NUMERO_NEQUI_WHATSAPP}.%20Mi%20cedula%20es:%20"
    st.markdown(
        f"""
        <div class="plan-card-popular">
            <span class="dif-badge">⭐ EL MÁS VENDIDO • RECOMENDADO</span>
            <h4 style="margin:10px 0 4px 0;">Pase Mensual PRO (30 Días)</h4>
            <div class="plan-price">$24.900 <small style="font-size:13px; color:#64748b;">COP</small></div>
            <p style="font-size:13px; color:#1e40af; font-weight:600;">Entrenamiento completo para dominar tu OPEC</p>
            <hr>
            <div style="text-align:left; font-size:13.5px; line-height:1.7;">
                ✅ <b>30 días completos</b> de acceso ilimitado.<br>
                ✅ Carga ilimitada de Manuales y Leyes.<br>
                ✅ Comparador de cargos y OPEC.<br>
                ✅ Simulacros cronometrados de hasta 20 preguntas.<br>
                ✅ Soporte prioritario por WhatsApp.
            </div>
            <a href="{wa_2}" target="_blank" class="btn-pay">📲 Pagar $24.900 y Activar por WhatsApp</a>
            <a href="{URL_PSE_NEQUI}" target="_blank" class="btn-pse">🏦 Pagar por PSE a Nequi {NUMERO_NEQUI_WHATSAPP}</a>
        </div>
        """,
        unsafe_allow_html=True,
    )

  with p3:
    wa_3 = f"https://wa.me/{WHATSAPP_INTL}?text=Hola,%20acabo%20de%20pagar%20el%20Pase%20Convocatoria%20de%20$39.900%20(6%20meses)%20a%20Nequi%20{NUMERO_NEQUI_WHATSAPP}.%20Mi%20cedula%20es:%20"
    st.markdown(
        f"""
        <div class="plan-card">
            <span class="eje-badge">👑 MÁXIMO AHORRO</span>
            <h4 style="margin:10px 0 4px 0;">Pase Convocatoria (6 Meses)</h4>
            <div class="plan-price">$39.900 <small style="font-size:13px; color:#64748b;">COP</small></div>
            <p style="font-size:13px; color:#64748b;">Para concursar en múltiples entidades todo el semestre</p>
            <hr>
            <div style="text-align:left; font-size:13.5px; line-height:1.7;">
                ✅ <b>180 días (6 meses)</b> de acceso total.<br>
                ✅ Sirve para DIAN, Contraloría, CNSC y más.<br>
                ✅ Todos los modos aleatorios e integrales.<br>
                ✅ Ahorras más del 70% frente al pase semanal.
            </div>
            <a href="{wa_3}" target="_blank" class="btn-pay">📲 Pagar $39.900 y Pedir Código</a>
            <a href="{URL_PSE_NEQUI}" target="_blank" class="btn-pse">🏦 Pagar por PSE a Nequi {NUMERO_NEQUI_WHATSAPP}</a>
        </div>
        """,
        unsafe_allow_html=True,
    )

  st.info(
      f"💡 **¿Cómo activar tu plan en 1 minuto?**\n"
      f"1. Transfiere el valor de tu plan a **Nequi `{NUMERO_NEQUI_WHATSAPP}`** (desde tu app Nequi, por **Transfiya/Bre-B** desde cualquier banco, o por **PSE** haciendo clic en el botón azul e ingresando el número `{NUMERO_NEQUI_WHATSAPP}`).\n"
      f"2. Haz clic en el botón verde de **WhatsApp** para enviar tu comprobante y tu número de cédula.\n"
      f"3. Recibirás al instante tu **Código PRO** para pegarlo en la barra lateral izquierda."
  )


# ------------------------------------------
# PESTAÑA 1: SIMULADOR INTELIGENTE
# ------------------------------------------
with tab_sim:
  if not client:
    st.info(
        "👈 **Paso 1 para empezar:** Pega tu clave gratuita **`GEMINI_API_KEY`** en la barra lateral izquierda (tienes una guía desplegable de 30 segundos ahí mismo si aún no tienes una). Mientras tanto, puedes explorar la pestaña **📋 Radiografía del Manual Activo** o **🔄 Comparador de Manuales**."
    )
  else:
    bloqueado = (
        not lic["activa"]
        and st.session_state.usos_gratis >= LIMITE_PREGUNTAS_GRATIS
    )
    if bloqueado:
      st.error(
          f"🔒 Has completado tus {LIMITE_PREGUNTAS_GRATIS} preguntas de demostración gratuita. ¡Elige tu plan desde **$14.900 COP** para desbloquear preguntas y simulacros ilimitados!"
      )
      renderizar_planes_de_pago()
    else:
      b1, b2 = st.columns(2)
      with b1:
        btn_una = st.button(
            "🎲 Generar Caso Situacional Aleatorio (Modo Estudio)",
            type="primary",
            use_container_width=True,
        )
      with b2:
        btn_lote = st.button(
            f"⏱️ Iniciar Simulacro de Examen ({cantidad_simulacro} Preguntas)",
            use_container_width=True,
        )

      if btn_lote:
        if not lic["activa"]:
          st.warning(
              "🔒 El modo Simulacro Múltiple Cronometrado es exclusivo para usuarios con Plan Activo ($14.900 / $24.900). En el modo gratuito puedes usar el botón izquierdo de Práctica Individual."
          )
        else:
          with st.spinner("Generando simulacro aleatorio basado en las funciones y ejes del cargo..."):
            lote = []
            vistos = set()
            for _ in range(cantidad_simulacro * 2):
              if len(lote) >= cantidad_simulacro:
                break
              q_cand = generar_pregunta_por_eje(
                  client, perfil_activo, modalidad_eje, item_especifico, dificultad
              )
              if q_cand and q_cand["_id"] not in vistos:
                vistos.add(q_cand["_id"])
                lote.append(q_cand)
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
                  <span class="eje-badge">🎯 {html.escape(q.get('eje_evaluado', 'Eje del Cargo'))}</span>
                  <span class="dif-badge">{html.escape(dificultad)}</span>
                  <div class="enunciado-box">{html.escape(q['pregunta'])}</div>
              </div>
              """,
              unsafe_allow_html=True,
          )
          eleccion = st.radio(
              "Selecciona la respuesta correcta:",
              ["A", "B", "C", "D"],
              format_func=lambda x: f"{x}) {q['opciones'][x]}",
              key=f"ex_rad_{idx}",
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
          t_emp = time.time() - st.session_state.examen_t0
          st.markdown(
              f"""
              <div class="saas-card" style="text-align:center;">
                  <h2>{'🏆 ¡APROBADO CON NIVEL COMPETITIVO!' if pct >= 65 else '📚 PUNTAJE INSUFICIENTE — SIGUE ENTRENANDO'}</h2>
                  <p style="font-size:18px;">Obtuviste <b>{ok_cnt} de {tot_cnt} aciertos ({pct:.1f}%)</b> en {t_emp:.0f} segundos.</p>
              </div>
              """,
              unsafe_allow_html=True,
          )
          for i_r, r in enumerate(res):
            st.markdown(f"**{'✅' if r['ok'] else '❌'} P{i_r+1} ({r['eje']}):** {r['q']}")
            st.caption(f"Elegiste: {r['elegida']} | Correcta: {r['correcta']} — {r['exp']}")
            st.divider()
          if st.button("🔄 Volver al Simulador", type="primary"):
            st.session_state.modo_examen = False
            st.rerun()
      else:
        if btn_una or "q_actual" not in st.session_state:
          with st.spinner("Construyendo caso práctico aleatorio acorde a tu manual..."):
            q_nueva = generar_pregunta_por_eje(
                client, perfil_activo, modalidad_eje, item_especifico, dificultad
            )
            if q_nueva:
              st.session_state.q_actual = q_nueva
              st.session_state.q_respondida = False
              if btn_una or st.session_state.usos_gratis == 0:
                st.session_state.usos_gratis += 1
            else:
              st.error("No se pudo generar la pregunta. Verifica que tu GEMINI_API_KEY sea válida.")
              st.stop()

        if "q_actual" in st.session_state:
          q = st.session_state.q_actual
          st.markdown(
              f"""
              <div class="saas-card">
                  <div style="display:flex; justify-content:space-between; flex-wrap:wrap; gap:8px;">
                      <div>
                          <span class="eje-badge">📌 {html.escape(q.get('eje_evaluado', 'Competencia del Cargo'))}</span>
                          <span class="dif-badge">⚡ {html.escape(dificultad)}</span>
                      </div>
                      <small style="color:#64748b; font-weight:600;">Cargo: {html.escape(perfil_activo.cargo)}</small>
                  </div>
                  <div class="enunciado-box">{html.escape(q['pregunta'])}</div>
              </div>
              """,
              unsafe_allow_html=True,
          )

          op_sel = st.radio(
              "Elige la decisión correcta según el manual y la normativa:",
              ["A", "B", "C", "D"],
              format_func=lambda x: f"{x}) {q['opciones'][x]}",
              key=f"prac_rad_{q['_id']}",
          )

          if not st.session_state.q_respondida:
            if st.button("✅ Validar Respuesta y Ver Justificación", type="primary"):
              st.session_state.q_respondida = True
              st.session_state.total += 1
              if op_sel == q["correcta"]:
                st.session_state.puntaje += 1
              st.rerun()
          else:
            corr = q["correcta"]
            if op_sel == corr:
              st.markdown(
                  f'<div class="feedback-ok"><h4>🎉 ¡Excelente! La opción {corr} es la correcta</h4><p>{html.escape(q["explicacion"])}</p></div>',
                  unsafe_allow_html=True,
              )
            else:
              st.markdown(
                  f'<div class="feedback-err"><h4>❌ Respuesta Incorrecta (Marcaste {op_sel}, la correcta era {corr})</h4><p><b>Opción Correcta ({corr}):</b> {html.escape(q["opciones"][corr])}</p><hr><p>{html.escape(q["explicacion"])}</p></div>',
                  unsafe_allow_html=True,
              )

            st.markdown(
                f"""
                <div class="saas-card" style="background:#f8fafc; margin-top:12px; padding:16px;">
                    <b>💡 Tip Estratégico para el Examen:</b> {html.escape(q.get('tip_estrategico', 'Verifica siempre la competencia funcional y el verbo rector de la función esencial.'))}<br><br>
                    <small style="color:#475569;"><b>📖 Sustento en el Manual ({html.escape(q.get('fuente',''))}):</b> <i>"{html.escape(q.get('fragmento_soporte',''))}"</i></small>
                </div>
                """,
                unsafe_allow_html=True,
            )

            if st.button("➡️ Siguiente Pregunta Aleatoria", type="primary"):
              del st.session_state.q_actual
              st.session_state.q_respondida = False
              st.rerun()

# ------------------------------------------
# PESTAÑA 2: RADIOGRAFÍA DEL MANUAL ACTIVO
# ------------------------------------------
with tab_ficha:
  st.markdown(
      f"""
      <div class="saas-card">
          <span class="eje-badge">🏛️ {html.escape(perfil_activo.entidad)}</span>
          <span class="dif-badge">{html.escape(perfil_activo.codigo_grado)}</span>
          <h3 style="margin:10px 0 6px 0;">{html.escape(perfil_activo.cargo)} ({html.escape(perfil_activo.nivel)})</h3>
          <p><b>Propósito Principal:</b> {html.escape(perfil_activo.proposito)}</p>
          <p style="font-size:13.5px; color:#475569;"><b>🎓 Requisitos de Estudio y Experiencia:</b> {html.escape(perfil_activo.requisitos)}</p>
      </div>
      """,
      unsafe_allow_html=True,
  )

  c_fun, c_eje = st.columns(2)
  with c_fun:
    st.markdown("#### 📋 Funciones Esenciales del Empleo")
    for f_item in perfil_activo.funciones_esenciales:
      st.markdown(f'<div class="saas-card" style="padding:12px; margin-bottom:8px;">🔹 {html.escape(f_item)}</div>', unsafe_allow_html=True)

    st.markdown("#### 🤝 Competencias Comportamentales")
    for cc_item in perfil_activo.competencias_comportamentales:
      st.markdown(f'<div class="saas-card" style="padding:12px; margin-bottom:8px;">🌟 {html.escape(cc_item)}</div>', unsafe_allow_html=True)

  with c_eje:
    st.markdown("#### 📘 Conocimientos Básicos / Ejes Temáticos")
    for ej_item in perfil_activo.conocimientos_ejes:
      st.markdown(f'<div class="saas-card" style="padding:12px; margin-bottom:8px;">📗 {html.escape(ej_item)}</div>', unsafe_allow_html=True)

    st.markdown("#### ⚙️ Competencias Funcionales Específicas")
    for cf_item in perfil_activo.competencias_funcionales:
      st.markdown(f'<div class="saas-card" style="padding:12px; margin-bottom:8px;">⚡ {html.escape(cf_item)}</div>', unsafe_allow_html=True)

# ------------------------------------------
# PESTAÑA 3: COMPARADOR DE MANUALES (OPEC)
# ------------------------------------------
with tab_comp:
  st.markdown("#### 🔄 Comparador Estratégico de Manuales de Funciones")
  st.caption("Compara lado a lado dos cargos (por ejemplo, DIAN vs. Contraloría o dos fichas OPEC que hayas subido) para identificar temas comunes de estudio.")

  col_m1, col_m2 = st.columns(2)
  with col_m1:
    m1_key = st.selectbox("Manual A:", nombres_manuales, index=0, key="comp_m1")
    p_m1 = st.session_state.perfiles[m1_key]
    st.markdown(
        f"""
        <div class="saas-card">
            <span class="eje-badge">{html.escape(p_m1.entidad)}</span>
            <h4>{html.escape(p_m1.cargo)} ({html.escape(p_m1.codigo_grado)})</h4>
            <p style="font-size:13.5px;"><b>Nivel:</b> {html.escape(p_m1.nivel)}</p>
            <p style="font-size:13.5px;"><b>Propósito:</b> {html.escape(p_m1.proposito)}</p>
            <hr>
            <b>📋 Funciones ({len(p_m1.funciones_esenciales)}):</b>
            <ul style="font-size:13px;">{''.join(f'<li>{html.escape(x)}</li>' for x in p_m1.funciones_esenciales)}</ul>
            <b>📘 Ejes y Competencias Funcionales:</b>
            <ul style="font-size:13px;">{''.join(f'<li>{html.escape(x)}</li>' for x in (p_m1.conocimientos_ejes + p_m1.competencias_funcionales))}</ul>
            <b>🎓 Requisitos:</b> <span style="font-size:13px;">{html.escape(p_m1.requisitos)}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

  with col_m2:
    idx_def = 1 if len(nombres_manuales) > 1 else 0
    m2_key = st.selectbox("Manual B:", nombres_manuales, index=idx_def, key="comp_m2")
    p_m2 = st.session_state.perfiles[m2_key]
    st.markdown(
        f"""
        <div class="saas-card">
            <span class="dif-badge">{html.escape(p_m2.entidad)}</span>
            <h4>{html.escape(p_m2.cargo)} ({html.escape(p_m2.codigo_grado)})</h4>
            <p style="font-size:13.5px;"><b>Nivel:</b> {html.escape(p_m2.nivel)}</p>
            <p style="font-size:13.5px;"><b>Propósito:</b> {html.escape(p_m2.proposito)}</p>
            <hr>
            <b>📋 Funciones ({len(p_m2.funciones_esenciales)}):</b>
            <ul style="font-size:13px;">{''.join(f'<li>{html.escape(x)}</li>' for x in p_m2.funciones_esenciales)}</ul>
            <b>📘 Ejes y Competencias Funcionales:</b>
            <ul style="font-size:13px;">{''.join(f'<li>{html.escape(x)}</li>' for x in (p_m2.conocimientos_ejes + p_m2.competencias_funcionales))}</ul>
            <b>🎓 Requisitos:</b> <span style="font-size:13px;">{html.escape(p_m2.requisitos)}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ------------------------------------------
# PESTAÑA 4: PLANES Y PAGOS NEQUI / PSE
# ------------------------------------------
with tab_planes:
  renderizar_planes_de_pago()
