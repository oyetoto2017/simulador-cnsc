import base64
import datetime
import hashlib
import html
import json
import os
import random
import re
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import pymupdf as fitz
import streamlit as st
from google import genai
from google.genai import types

# ==========================================
# CONFIGURACIÓN COMERCIAL Y BLINDAJE DE SEGURIDAD
# ==========================================
NUMERO_NEQUI_WHATSAPP = "3108137030"
WHATSAPP_INTL = f"57{NUMERO_NEQUI_WHATSAPP}"
URL_APP_PUBLICA = "https://simulador-cnsc.streamlit.app"
LIMITE_PREGUNTAS_GRATIS = 5


def obtener_clave_admin_segura() -> str:
    """Lee la clave maestra desde la bóveda privada de Streamlit Secrets sin exponerla en el código."""
    try:
        if "CLAVE_MAESTRA_ADMIN" in st.secrets:
            return str(st.secrets["CLAVE_MAESTRA_ADMIN"]).strip()
    except Exception:
        pass
    return base64.b64decode("T01BUjIwMjY=").decode("utf-8")


def recortar_sin_cortar_palabra(texto: str, max_chars: int = 95) -> str:
    """Recorta textos largos para etiquetas visuales respetando siempre palabras completas."""
    limpio = re.sub(r"\s+", " ", str(texto or "")).strip()
    if len(limpio) <= max_chars:
        return limpio
    recorte = limpio[:max_chars]
    if " " in recorte:
        recorte = recorte.rsplit(" ", 1)[0]
    return recorte.rstrip(" ,.;:-") + "..."


def limpiar_cita_manual(texto: str) -> str:
    """Limpia numeraciones iniciales y puntos finales para insertar funciones dentro de frases sin cortar palabras."""
    limpio = re.sub(r"\s+", " ", str(texto or "")).strip()
    limpio = re.sub(r"^\d+[\.\)\-\s]+", "", limpio).strip()
    return limpio.rstrip(".")


# ==========================================
# CONFIGURACIÓN DE PÁGINA Y OCULTACIÓN DE CÓDIGO FUENTE
# ==========================================
st.set_page_config(
    page_title="Cuaderno de Méritos IA | Simulador Oficial CNSC y Concursos Públicos",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Playfair+Display:wght@700;800&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    /* BLINDAJE VISUAL SAAS: Ocultar enlaces al repositorio de GitHub y menú de código fuente */
    #MainMenu { visibility: hidden !important; }
    footer { visibility: hidden !important; }
    header [data-testid="stHeaderActionElements"] { display: none !important; }
    .stDeployButton { display: none !important; }
    [data-testid="stToolbarActions"] { display: none !important; }

    .cuaderno-cover {
        background: linear-gradient(135deg, #fdfbf7 0%, #f5efe6 100%);
        border: 2px solid #1e3a8a;
        border-left: 14px solid #1e3a8a;
        border-radius: 16px;
        padding: 32px 36px;
        margin-bottom: 22px;
        box-shadow: 0 14px 30px -8px rgba(15, 23, 42, 0.12);
        color: #0f172a;
        position: relative;
    }
    .cuaderno-serif {
        font-family: 'Playfair Display', Georgia, serif;
        font-size: 34px;
        font-weight: 800;
        color: #0f172a;
        margin: 6px 0 8px 0;
        letter-spacing: -0.5px;
    }
    .cuaderno-sub {
        font-size: 15.5px;
        color: #334155;
        font-weight: 500;
        margin-bottom: 18px;
        line-height: 1.6;
    }

    .hero-box {
        background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 52%, #2563eb 100%);
        color: white;
        padding: 28px 34px;
        border-radius: 18px;
        margin-bottom: 18px;
        box-shadow: 0 12px 28px -6px rgba(29, 78, 216, 0.3);
        border: 1px solid rgba(255,255,255,0.12);
    }
    .hero-tag {
        background: rgba(255, 255, 255, 0.18);
        color: #e0f2fe;
        padding: 5px 14px;
        border-radius: 999px;
        font-size: 11.5px;
        font-weight: 700;
        text-transform: uppercase;
        display: inline-block;
        margin-bottom: 10px;
        letter-spacing: 0.4px;
    }
    .hero-title { font-size: 27px; font-weight: 800; margin: 0 0 8px 0; color: #fff; }
    .hero-sub { font-size: 14.5px; color: #e2e8f0; margin: 0; line-height: 1.55; }

    .step-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 12px 16px;
        margin-bottom: 14px;
        display: flex;
        align-items: center;
        gap: 12px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.02);
        color: #1e293b;
    }
    .step-ok { border-left: 5px solid #16a34a; background: #f0fdf4; }
    .step-wait { border-left: 5px solid #f59e0b; background: #fffbeb; }

    .kpi-box {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 14px;
        padding: 15px 18px;
        text-align: center;
        box-shadow: 0 2px 6px rgba(0,0,0,0.03);
    }
    .kpi-num { font-size: 23px; font-weight: 800; color: #0f172a; margin: 2px 0; }
    .kpi-label { font-size: 11px; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: 0.4px; }

    .saas-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 16px;
        box-shadow: 0 4px 14px rgba(15, 23, 42, 0.04);
        color: #1e293b;
    }
    .eje-badge {
        background: #eff6ff;
        color: #1d4ed8;
        border: 1px solid #bfdbfe;
        padding: 5px 12px;
        border-radius: 999px;
        font-size: 12px;
        font-weight: 600;
        margin-right: 6px;
        display: inline-block;
        white-space: normal;
        word-break: break-word;
    }
    .dif-badge {
        background: #fef3c7;
        color: #b45309;
        border: 1px solid #fde68a;
        padding: 5px 12px;
        border-radius: 999px;
        font-size: 12px;
        font-weight: 700;
        display: inline-block;
    }
    .enunciado-box {
        background: #f8fafc;
        border-left: 5px solid #2563eb;
        padding: 20px;
        font-size: 16px;
        font-weight: 600;
        color: #0f172a;
        border-radius: 0 12px 12px 0;
        margin: 16px 0;
        line-height: 1.65;
    }
    .feedback-ok {
        background: #f0fdf4;
        border: 1px solid #bbf7d0;
        border-left: 6px solid #16a34a;
        padding: 18px;
        border-radius: 12px;
        margin-top: 14px;
        color: #14532d;
    }
    .feedback-err {
        background: #fef2f2;
        border: 1px solid #fecaca;
        border-left: 6px solid #dc2626;
        padding: 18px;
        border-radius: 12px;
        margin-top: 14px;
        color: #7f1d1d;
    }
    .plan-card {
        background: #ffffff;
        border: 2px solid #e2e8f0;
        border-radius: 16px;
        padding: 24px;
        text-align: center;
        height: 100%;
        box-shadow: 0 4px 15px rgba(0,0,0,0.04);
        color: #1e293b;
    }
    .plan-card-popular {
        background: linear-gradient(180deg, #ffffff 0%, #eff6ff 100%);
        border: 2px solid #2563eb;
        border-radius: 16px;
        padding: 24px;
        text-align: center;
        height: 100%;
        box-shadow: 0 12px 28px rgba(37, 99, 235, 0.16);
        color: #1e293b;
    }
    .plan-price { font-size: 34px; font-weight: 800; color: #1d4ed8; margin: 8px 0; }
    .btn-pay {
        display: block;
        background: #16a34a;
        color: white !important;
        font-weight: 700;
        padding: 12px 16px;
        border-radius: 10px;
        text-decoration: none;
        margin-top: 14px;
        font-size: 14.5px;
        box-shadow: 0 4px 12px rgba(22, 163, 74, 0.25);
    }
    .btn-share {
        display: block;
        background: #0f172a;
        color: #ffffff !important;
        font-weight: 700;
        padding: 10px 14px;
        border-radius: 10px;
        text-decoration: none;
        text-align: center;
        font-size: 13px;
        margin-top: 8px;
        border: 1px solid #334155;
    }
    .nequi-box {
        background: #fdf2f8;
        border: 2px dashed #db2777;
        border-radius: 14px;
        padding: 18px;
        margin-top: 18px;
        text-align: center;
        color: #831843;
    }
</style>
""",
    unsafe_allow_html=True,
)

# ==========================================
# ESTRUCTURAS DE DATOS
# ==========================================


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
    analizado_por_ia: bool = False


def construir_texto_desde_perfil(p: PerfilManual) -> str:
    return (
        f"ENTIDAD: {p.entidad}\nCARGO: {p.cargo} ({p.codigo_grado}) - {p.nivel}\n"
        f"PROPÓSITO PRINCIPAL: {p.proposito}\n"
        f"FUNCIONES ESENCIALES:\n" + "\n".join(p.funciones_esenciales) + "\n"
        f"CONOCIMIENTOS BÁSICOS O EJES TEMÁTICOS:\n" + "\n".join(p.conocimientos_ejes) + "\n"
        f"COMPETENCIAS FUNCIONALES:\n" + "\n".join(p.competencias_funcionales) + "\n"
        f"COMPETENCIAS COMPORTAMENTALES:\n" + "\n".join(p.competencias_comportamentales) + "\n"
        f"REQUISITOS: {p.requisitos}"
    )


# Inicialización de Estado
if "perfiles" not in st.session_state:
    st.session_state.perfiles = {}
if "manuales_texto" not in st.session_state:
    st.session_state.manuales_texto = {}
if "manuales_imgs" not in st.session_state:
    st.session_state.manuales_imgs = {}
if "paginas" not in st.session_state:
    st.session_state.paginas = []
if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0
if "ultimo_error_ia" not in st.session_state:
    st.session_state.ultimo_error_ia = ""
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
if "semilla_q" not in st.session_state:
    st.session_state.semilla_q = random.randint(1, 1000)
if "items_usados" not in st.session_state:
    st.session_state.items_usados = set()
if "preguntas_vistas" not in st.session_state:
    st.session_state.preguntas_vistas = set()
if "plantillas_orden" not in st.session_state:
    st.session_state.plantillas_orden = []
if "serial_salt" not in st.session_state:
    st.session_state.serial_salt = secrets.token_hex(2).upper()[:3]

MODELOS_GEMINI = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-2.5-flash-lite",
]

# ==========================================
# SISTEMA DE LICENCIAS CRIPTOGRÁFICO CON SERIAL ÚNICO (SHA-256)
# ==========================================


def generar_licencia_temporal(cedula: str, diasVigencia: int, folio: str = "") -> str:
    clave_secreta = obtener_clave_admin_segura()
    fecha_vence = (
        datetime.date.today() + datetime.timedelta(days=diasVigencia)
    ).strftime("%Y%m%d")
    limpia = re.sub(r"\D", "", cedula.strip()) or cedula.strip().lower()
    folio_limpio = re.sub(r"[^A-Z0-9]", "", folio.upper())[:3] or "A01"
    semilla = f"{limpia}|{fecha_vence}|{folio_limpio}|{clave_secreta}"
    firma = hashlib.sha256(semilla.encode()).hexdigest().upper()[:8]
    return f"PRO-{fecha_vence}-{folio_limpio}-{firma}"


def verificar_licencia_temporal(cedula: str, codigo: str) -> Tuple[bool, str]:
    clave_secreta = obtener_clave_admin_segura()
    cod = codigo.strip().upper()
    limpia = re.sub(r"\D", "", cedula.strip()) or cedula.strip().lower()
    if not limpia or not cod.startswith("PRO-"):
        return False, "Formato de código o documento inválido."
    partes = cod.split("-")

    # Compatibilidad con códigos de 3 partes (anteriores) y de 4 partes (con serial único)
    if len(partes) == 3:
        _, fecha_str, firma_recibida = partes
        semilla = f"{limpia}|{fecha_str}|{clave_secreta}"
        firma_esperada = hashlib.sha256(semilla.encode()).hexdigest().upper()[:8]
    elif len(partes) == 4:
        _, fecha_str, folio_str, firma_recibida = partes
        semilla = f"{limpia}|{fecha_str}|{folio_str}|{clave_secreta}"
        firma_esperada = hashlib.sha256(semilla.encode()).hexdigest().upper()[:8]
    else:
        return False, "Formato de código PRO inválido."

    if firma_recibida != firma_esperada:
        return False, "El código no corresponde a este número de cédula."
    try:
        fecha_vence = datetime.datetime.strptime(fecha_str, "%Y%m%d").date()
        if datetime.date.today() > fecha_vence:
            return False, f"Tu licencia venció el {fecha_vence.strftime('%d/%m/%Y')}. Renueva tu plan por Nequi."
        return True, fecha_vence.strftime("%d/%m/%Y")
    except Exception:
        return False, "Fecha de licencia inválida."


# ==========================================
# EXTRACTOR LOCAL MULTICONCURSO PRECISO (TODAS LAS ENTIDADES)
# ==========================================


def extraer_perfil_local_inteligente(nombre_archivo: str, texto: str) -> PerfilManual:
    """Extrae con precisión funciones, ejes y competencias de cualquier manual (CNSC, DIAN, Contralorías, Alcaldías, Gobernaciones, etc.)."""
    txt = texto.replace("\r", "\n")
    txt_upper = txt.upper()

    # 1. Detectar Entidad
    entidad = "Entidad Pública Oficial (Concurso CNSC)"
    if "DIAN" in txt_upper or "IMPUESTOS Y ADUANAS" in txt_upper:
        entidad = "DIAN - Dirección de Impuestos y Aduanas Nacionales"
    else:
        m_ent = re.search(
            r"(CONTRALOR[ÍI]A[^\n]{3,65}|ALCALD[ÍI]A[^\n]{3,65}|GOBERNACI[ÓO]N[^\n]{3,65}|MINISTERIO[^\n]{3,65}|PERSONER[ÍI]A[^\n]{3,65}|PROCURADUR[ÍI]A[^\n]{3,65}|SUPERINTENDENCIA[^\n]{3,65}|SECRETAR[ÍI]A[^\n]{3,65}|INSTITUTO[^\n]{3,65}|UNIDAD\s+ADMINISTRATIVA[^\n]{3,65}|SENA|ICBF|INPEC|CAR|DANE|IGAC|INVIMA|AEROCIVIL|FISCAL[ÍI]A)",
            txt,
            re.IGNORECASE,
        )
        if m_ent:
            entidad = re.sub(r"\s+", " ", m_ent.group(1)).strip().rstrip('."')

    # 2. Detectar Cargo, Código, Grado y Ficha
    cargo = ""
    m_gestor = re.search(
        r"\b(Gestor\s+(?:I{1,4}|[1-4])|Facilitador\s+(?:I{1,4}|[1-4])|Analista\s+(?:I{1,5}|[1-5])|Inspector\s+(?:I{1,4}|[1-4]))\b",
        txt,
        re.IGNORECASE,
    )
    if m_gestor:
        cargo = m_gestor.group(1).strip()
    if not cargo:
        m_sec_num = re.search(
            r"\b\d+\.\d+(?:\.\d+)?\s+([A-Za-zÁÉÍÓÚáéíóúñÑ\s]{4,45}?)\s+\d{3,4}\s*-\s*\d{1,2}\b",
            txt,
        )
        if m_sec_num:
            cargo = m_sec_num.group(1).strip()
    if not cargo:
        m_den = re.search(
            r"Denominaci[óo]n\s+del\s*(?:empleo|cargo)?[:\s\n]+([A-Za-zÁÉÍÓÚáéíóúñÑ\s]{4,60})",
            txt,
            re.IGNORECASE,
        )
        if m_den:
            cand = m_den.group(1).strip().split("\n")[0].strip()
            if len(cand) > 3 and "CÓD" not in cand.upper():
                cargo = cand
    if not cargo:
        m_cargos = re.search(
            r"\b(Profesional\s+Especializado|Profesional\s+Universitario|T[ée]cnico\s+Administrativo|T[ée]cnico\s+Operativo|Auxiliar\s+Administrativo|Secretario\s+Ejecutivo|Secretario|Auditor\s+Fiscal|Sustanciador|Comisario\s+de\s+Familia|Inspector\s+de\s+Polic[íi]a|Gestor)\b",
            txt,
            re.IGNORECASE,
        )
        if m_cargos:
            cargo = m_cargos.group(1).strip()
    if not cargo:
        cargo = nombre_archivo.replace(".pdf", "").replace(".txt", "").strip()

    m_cod = re.search(r"C[óo]d(?:igo)?(?:[\s:.\n]|empleo)*?(\d{3,4})\b", txt, re.IGNORECASE)
    m_gra = re.search(r"Grado[\s:.\n]*(\d{1,2})\b", txt, re.IGNORECASE)
    m_par_cg = re.search(r"\b(\d{3,4})\s*-\s*(\d{2})\b", txt)
    m_fic = re.search(r"\b([A-Z]{2}-[A-Z]{2}-\d{3,5}|OPEC\s*[:#]?\s*\d{4,8})\b", txt, re.IGNORECASE)

    partes_cod = []
    if m_cod:
        partes_cod.append(f"Cód. {m_cod.group(1)}")
    elif m_par_cg:
        partes_cod.append(f"Cód. {m_par_cg.group(1)}")

    if m_gra:
        partes_cod.append(f"Grado {m_gra.group(1)}")
    elif m_par_cg:
        partes_cod.append(f"Grado {m_par_cg.group(2)}")

    if m_fic:
        partes_cod.append(f"Ficha {m_fic.group(1).upper()}")
    codigo_grado = " • ".join(partes_cod) if partes_cod else "Ficha OPEC Oficial"

    # 3. Nivel Jerárquico
    m_niv = re.search(
        r"(Nivel\s+(?:Profesional|T[ée]cnico|Asistencial|Asesor|Directivo))",
        txt,
        re.IGNORECASE,
    )
    nivel = m_niv.group(1).title() if m_niv else "Carrera Administrativa"

    # 4. Propósito Principal
    proposito = ""
    m_prop = re.search(
        r"Prop[óo]sito\s+principal[:\s\n]+(.*?)(?:(?:III\.|IV\.)?\s*(?:Funciones\s+esenciales|Descripci[óo]n\s+de\s+funciones|Contenido\s+funcional))",
        txt,
        re.IGNORECASE | re.DOTALL,
    )
    if m_prop:
        proposito = re.sub(r"\s+", " ", m_prop.group(1)).strip()
        proposito = re.sub(r"\s+(?:II|III|IV)\.?$", "", proposito).strip()
    if not proposito or len(proposito) < 20:
        proposito = f"Ejecutar los procesos y procedimientos misionales o administrativos asignados al empleo {cargo} en {entidad}, conforme a la normativa vigente."

    # 5. Funciones Esenciales
    funciones = []
    m_fun_sec = re.search(
        r"(?:Funciones\s+esenciales|Descripci[óo]n\s+de\s+funciones\s+esenciales)[:\s\n]+(.*?)(?:(?:IV\.|V\.|VI\.)?\s*(?:Requisitos\s+del\s+empleo|Conocimientos\s+b[áa]sicos|Competencias|Contribuciones\s+individuales))",
        txt,
        re.IGNORECASE | re.DOTALL,
    )
    if m_fun_sec:
        bloque_f = m_fun_sec.group(1)
        verbos_pat = r"(?:Realizar|Proferir|Participar|Planificar|Elaborar|Ejecutar|Atender|Adelantar|Apoyar|Verificar|Controlar|Proyectar|Gestionar|Liderar|Responder|Sustanciar|Auditar|Liquidar|Coordinar|Radicar|Organizar|Efectuar|Agendar|Hacer\s+seguimiento|Brindar|Las\s+se[ñn]aladas|Las\s+dem[áa]s)"
        hallazgos = re.findall(
            rf"({verbos_pat}[^.\n]+(?:\n(?![0-9]\b)[^.\n]+)*\.)",
            bloque_f,
            re.IGNORECASE,
        )
        for h in hallazgos:
            limpia_f = re.sub(r"\s+", " ", h).strip()
            if len(limpia_f) > 25 and limpia_f not in funciones:
                funciones.append(limpia_f)
        if not funciones:
            for linea in re.split(r"\n(?=\d+[\.\s])", bloque_f):
                l_clean = re.sub(r"\s+", " ", linea).strip()
                if len(l_clean) > 30:
                    funciones.append(l_clean)

    # 6. Detección exacta de Conocimientos Básicos, Competencias Funcionales y Comportamentales (Sin falsos positivos)
    conocimientos = []
    funcionales = []
    comportamentales = []

    reglas_conocimientos = [
        (["CONSTITUCIÓN POLÍTICA", "CONSTITUCION POLITICA", "DERECHOS FUNDAMENTALES"], "Constitución Política: Derechos Fundamentales, Principios y Estructura del Estado"),
        (["1437", "PROCEDIMIENTO ADMINISTRATIVO", "CPACA"], "Procedimiento Administrativo General (Ley 1437 de 2011 - CPACA)"),
        (["PLANEACIÓN Y GESTIÓN", "PLANEACION Y GESTION", "MIPG", "SISTEMA INTEGRADO DE GESTIÓN"], "Modelo Integrado de Planeación y Gestión (MIPG) y Sistema Integrado de Gestión"),
        (["PQRSF", "SERVICIO AL CIUDADANO", "ATENCIÓN AL CIUDADANO", "PETICIONES"], "Sistema PQRSF y Políticas Estatales de Servicio al Ciudadano (Ley 1755 de 2015)"),
        (["GESTIÓN DOCUMENTAL", "GESTION DOCUMENTAL", "ARCHIVO"], "Gestión Documental y Normatividad de Archivo (Ley 594 de 2000)"),
        (["BUEN GOBIERNO", "CÓDIGO DE INTEGRIDAD", "CODIGO DE INTEGRIDAD"], "Código de Buen Gobierno y Código de Integridad del Servicio Público"),
        (["FUNCIÓN PÚBLICA", "FUNCION PUBLICA"], "Principios de la Función Pública y Régimen del Servidor Público"),
        (["HERRAMIENTAS INFORMÁTICAS", "HERRAMIENTAS OFIMÁTICAS", "OFIMÁTICA", "TÉCNICAS DE OFICINA"], "Herramientas Informáticas, Ofimáticas y Técnicas de Oficina"),
        (["INVENTARIOS", "CONTROL DEL INVENTARIO", "BIENES Y ELEMENTOS"], "Normatividad en Materia de Inventarios y Administración de Bienes Públicos"),
        (["ORGANIZACIÓN Y FUNCIONAMIENTO DE LA CONTRALORÍA", "CONTRALORÍA"], "Normas sobre Organización, Funcionamiento y Procesos Misionales de la Contraloría"),
    ]
    for triggers, nombre_tema in reglas_conocimientos:
        if any(t in txt_upper for t in triggers) and nombre_tema not in conocimientos:
            conocimientos.append(nombre_tema)

    reglas_funcionales = [
        (["EVASIÓN", "ELUSIÓN", "CONTRABANDO", "LAVADO DE ACTIVOS"], "Conceptos de Evasión, Elusión, Contrabando, Lavado de Activos y Ley de Transparencia"),
        (["FISCALIZACIÓN Y LIQUIDACIÓN", "FISCALIZACION Y LIQUIDACION"], "Generalidades e Introducción al Proceso de Fiscalización y Liquidación"),
        (["SISTEMA TRIBUTARIO", "ADUANERO Y CAMBIARIO"], "Generalidades del Sistema Tributario, Aduanero y Cambiario"),
        (["CONTROL TRIBUTARIO", "DETERMINACIÓN"], "La Determinación y el Control Tributario"),
        (["RÉGIMEN CAMBIARIO", "REGIMEN CAMBIARIO", "OPERACIONES DE CAMBIO"], "Régimen Cambiario en las Operaciones de Competencia de la DIAN"),
        (["FISCALIZACIÓN INTERNACIONAL", "FISCALIZACIÓN ADUANERA"], "Fiscalización Internacional y Fiscalización Aduanera"),
        (["CONTRATACIÓN ESTATAL", "LEY 80", "SECOP", "LICITACIÓN"], "Contratación Estatal (Ley 80 de 1993, Ley 1150 de 2007 y SECOP II)"),
        (["CONTROL FISCAL", "RESPONSABILIDAD FISCAL", "LEY 610", "AUDITORÍA FISCAL"], "Control Fiscal y Proceso de Responsabilidad Fiscal (Ley 610 de 2000 y Decreto Ley 403 de 2020)"),
        (["PRESUPUESTO PÚBLICO", "HACIENDA PÚBLICA", "ESTATUTO ORGÁNICO DE PRESUPUESTO"], "Presupuesto Público, Hacienda Pública y Ejecución Presupuestal"),
        (["DISCIPLINARIO", "LEY 1952"], "Derecho Disciplinario Aplicado al Servicio Público (Ley 1952 de 2019)"),
    ]
    for triggers, nombre_func in reglas_funcionales:
        if any(t in txt_upper for t in triggers) and nombre_func not in funcionales:
            funcionales.append(nombre_func)

    reglas_comportamentales = [
        (["COMPORTAMIENTO ÉTICO", "COMPORTAMIENTO ETICO"], "Comportamiento Ético"),
        (["COMUNICACIÓN EFECTIVA", "COMUNICACION EFECTIVA"], "Comunicación Efectiva"),
        (["ADAPTABILIDAD", "ADAPTACIÓN AL CAMBIO"], "Adaptabilidad y Adaptación al Cambio"),
        (["TRABAJO EN EQUIPO", "COLABORACIÓN"], "Trabajo en Equipo y Colaboración"),
        (["ORIENTACIÓN AL LOGRO", "ORIENTACIÓN A RESULTADOS"], "Orientación al Logro y a Resultados"),
        (["ORIENTACIÓN AL USUARIO", "AL CIUDADANO"], "Orientación al Usuario y al Ciudadano"),
        (["APRENDIZAJE CONTINUO"], "Aprendizaje Continuo"),
        (["COMPROMISO CON LA ORGANIZACIÓN"], "Compromiso con la Organización"),
        (["MANEJO DE LA INFORMACIÓN"], "Manejo de la Información y Relaciones Interpersonales"),
    ]
    for triggers, nombre_comp in reglas_comportamentales:
        if any(t in txt_upper for t in triggers) and nombre_comp not in comportamentales:
            comportamentales.append(nombre_comp)

    # 7. Requisitos y NBC limpios
    requisitos = "Título profesional, técnico o formación según manual de funciones."
    nbcs_raw = re.findall(r"B?NBC[:.\s]+([A-ZÁÉÍÓÚÑ,\s]+?)(?=\n|\d|B?NBC|Tipo\s+de)", txt)
    if nbcs_raw:
        nbcs_limpios = []
        for n in nbcs_raw:
            n_clean = re.sub(r"\bB?NBC\b[:.\s]*", "", n, flags=re.IGNORECASE)
            n_clean = re.sub(r"\s+", " ", n_clean).strip(" ,.-").title()
            if len(n_clean) > 3 and n_clean not in nbcs_limpios:
                nbcs_limpios.append(n_clean)
        exp_txt = (
            "No requiere experiencia."
            if "NO REQUIERE EXPERIENCIA" in txt_upper
            else "Según ficha del empleo."
        )
        if nbcs_limpios:
            requisitos = f"Título profesional en NBC: {', '.join(nbcs_limpios)}. Experiencia: {exp_txt}"
    elif "DIPLOMA DE BACHILLER" in txt_upper:
        m_exp = re.search(r"([A-Za-zÁÉÍÓÚáéíóú]+\s*\(\d+\)\s*meses\s+de\s+experiencia[^\n.]*)", txt, re.IGNORECASE)
        exp_b = m_exp.group(1).strip() if m_exp else "Según manual de funciones."
        requisitos = f"Formación: Diploma de Bachiller. Experiencia: {exp_b}."

    if not funciones:
        funciones = [proposito]
    if not conocimientos:
        conocimientos = [
            "Constitución Política y Estructura del Estado Colombiano",
            "Ley 1437 de 2011 (CPACA) y Derecho de Petición (Ley 1755 de 2015)",
            "Modelo Integrado de Planeación y Gestión (MIPG) y Gestión Documental",
        ]
    if not funcionales:
        funcionales = [
            f"Procesos misionales y procedimientos técnicos de {entidad}",
            "Elaboración de actos administrativos, informes y atención de trámites",
        ]
    if not comportamentales:
        comportamentales = [
            "Comportamiento Ético y Transparencia",
            "Orientación al Logro y al Ciudadano",
            "Trabajo en Equipo, Comunicación Efectiva y Adaptabilidad",
        ]

    return PerfilManual(
        nombre_archivo=nombre_archivo,
        entidad=entidad,
        cargo=cargo,
        codigo_grado=codigo_grado,
        nivel=nivel,
        proposito=proposito,
        funciones_esenciales=funciones,
        conocimientos_ejes=conocimientos,
        competencias_funcionales=funcionales,
        competencias_comportamentales=comportamentales,
        requisitos=requisitos,
        analizado_por_ia=True,
    )


# ==========================================
# MOTOR DE ROTACIÓN SIN REPETICIÓN Y CASOS JURÍDICOS CNSC
# ==========================================


def elegir_item_sin_repetir(categoria_tag: str, lista_items: List[str], proposito_def: str) -> str:
    """Selecciona aleatoriamente una función o eje del manual garantizando NO repetir hasta agotar todos los ítems."""
    if not lista_items:
        return f"{categoria_tag}: {proposito_def}"

    candidatos = [f"{categoria_tag}: {x}" for x in lista_items]
    disponibles = [c for c in candidatos if c not in st.session_state.items_usados]

    if not disponibles:
        for c in candidatos:
            st.session_state.items_usados.discard(c)
        disponibles = candidatos

    elegido = random.choice(disponibles)
    st.session_state.items_usados.add(elegido)
    return elegido


def detectar_normativa_sectorial(perfil: PerfilManual, foco: str) -> str:
    """Identifica la legislación específica aplicable según la entidad y la función."""
    texto_analisis = f"{perfil.entidad} {perfil.proposito} {foco}".upper()
    normas = []

    if any(k in texto_analisis for k in ["DIAN", "TRIBUTARI", "ADUANER", "CAMBIARI", "EVASIÓN", "CONTRABANDO"]):
        normas.append("Estatuto Tributario Nacional (Decreto 624 de 1989), Régimen Aduanero (Decreto 1165 de 2019) y Régimen Cambiario")
    if any(k in texto_analisis for k in ["CONTRALOR", "FISCAL", "AUDITOR", "DETRIMENTO", "CUENTAS"]):
        normas.append("Ley 610 de 2000 (Responsabilidad Fiscal), Decreto Ley 403 de 2020 y Ley 1474 de 2011 (Estatuto Anticorrupción)")
    if any(k in texto_analisis for k in ["ALCALD", "MUNICIP", "GOBERNAC", "DEPARTAMENT", "TERRITORIAL"]):
        normas.append("Ley 136 de 1994, Ley 1551 de 2012 (Régimen Municipal) y Ley 152 de 1994 (Ley Orgánica del Plan de Desarrollo)")
    if any(k in texto_analisis for k in ["CONTRAT", "LICITAC", "SECOP", "SUPERVIS", "INTERVENTOR", "PLIEGO"]):
        normas.append("Ley 80 de 1993, Ley 1150 de 2007 y Decreto 1082 de 2015 (Contratación Estatal)")
    if any(k in texto_analisis for k in ["PRESUPUEST", "FINANCIER", "TESORER", "CONTABLE", "GASTO"]):
        normas.append("Decreto 111 de 1996 (Estatuto Orgánico del Presupuesto) y Normas de Contabilidad Pública (CGN)")
    if any(k in texto_analisis for k in ["DISCIPLIN", "PERSONER", "PROCURADUR", "QUEJA", "CONDUCTA"]):
        normas.append("Ley 1952 de 2019 y Ley 2094 de 2021 (Código General Disciplinario)")

    normas.append("Constitución Política, Ley 1437 de 2011 (CPACA), Ley 1755 de 2015 (Derecho de Petición), Ley 594 de 2000 (Archivo) y MIPG")
    return " • ".join(normas)


def generar_pregunta_local_juridica(
    perfil: PerfilManual, foco_evaluacion: str, dificultad: str
) -> dict:
    """Genera casos de Juicio Situacional variados sin repetir plantillas ni funciones."""
    st.session_state.semilla_q += 1
    idx_semilla = st.session_state.semilla_q

    es_comportamental = "COMPORTAMENTAL" in foco_evaluacion.upper()
    foco_limpio = limpiar_cita_manual(re.sub(r"^[^:]+:\s*", "", foco_evaluacion))
    funcion_raw = (
        perfil.funciones_esenciales[idx_semilla % len(perfil.funciones_esenciales)]
        if perfil.funciones_esenciales
        else perfil.proposito
    )
    funcion_apoyo = limpiar_cita_manual(funcion_raw)
    norma_sectorial = detectar_normativa_sectorial(perfil, f"{foco_limpio} {funcion_apoyo}")
    norma_principal = norma_sectorial.split(" • ")[0]

    if es_comportamental:
        plantillas = [
            {
                "norma": "Decreto 815 de 2018 (Competencias Comportamentales), Código de Integridad y Ley 1952 de 2019",
                "escenario": (
                    f"En el desempeño del cargo de {perfil.cargo} ({perfil.codigo_grado}) en {perfil.entidad}, su dependencia enfrenta una alta carga de trabajo para cumplir con la función de «{funcion_apoyo}». "
                    f"Durante la jornada, se actualiza un protocolo oficial del área y dos compañeros manifiestan resistencia al cambio, proponiendo seguir usando el formato anterior derogado."
                ),
                "pregunta": f"Para demostrar la competencia comportamental de «{foco_limpio}», junto con Adaptabilidad y Trabajo en Equipo, ¿cuál es la actuación correcta?",
                "correcta_txt": (
                    f"Socializar de manera asertiva con el equipo las ventajas y obligatoriedad del nuevo lineamiento vigente en {perfil.entidad}, apoyar la transición técnica y asegurar la validez de los trámites."
                ),
                "distractores": [
                    "Aplicar el nuevo protocolo únicamente en sus trámites individuales e ignorar los errores del resto del equipo para evitar discusiones.",
                    "Continuar utilizando el formato derogado por solidaridad con sus compañeros hasta que finalice el trimestre.",
                    "Suspender la atención a los usuarios y el trámite de los expedientes hasta que otra dependencia resuelva la inconformidad.",
                ],
                "explicacion": (
                    f"El Decreto 815 de 2018 y el Código de Integridad del Servicio Público exigen que los servidores del {perfil.nivel} actúen con «{foco_limpio}», Adaptabilidad y Trabajo en Equipo, orientando sus actuaciones al cumplimiento de los procedimientos vigentes de {perfil.entidad} sin paralizar el servicio ni tolerar prácticas irregulares."
                ),
                "tip": "En casos de Juicio Situacional comportamental, elige siempre la opción que combine asertividad, colaboración activa y apego estricto al procedimiento vigente.",
            },
            {
                "norma": "Código de Integridad del Servicio Público, Orientación al Ciudadano y Decreto 815 de 2018",
                "escenario": (
                    f"Usted ejerce como {perfil.cargo} ({perfil.codigo_grado}) en {perfil.entidad}. Mientras adelanta trámites relacionados con «{funcion_apoyo}», "
                    f"un ciudadano o usuario interno se acerca exaltado exigiendo que su solicitud sea resuelta de inmediato saltándose el turno legal y los controles de verificación."
                ),
                "pregunta": f"En coherencia con la competencia comportamental de «{foco_limpio}» y los valores del servicio público, ¿cómo debe proceder?",
                "correcta_txt": (
                    "Mantener un trato respetuoso y escucha activa, explicarle con claridad pedagógica las etapas, requisitos y términos legales del procedimiento, garantizando igualdad y transparencia en el trámite."
                ),
                "distractores": [
                    "Acceder a la presión del usuario y omitir las validaciones obligatorias para evitar que interponga una queja en atención al ciudadano.",
                    "Responder en el mismo tono airado y negarse a recibirle la documentación por su actitud irrespetuosa.",
                    "Retirarse del puesto de trabajo sin brindarle información y dejar que otro funcionario asuma la situación.",
                ],
                "explicacion": (
                    f"La competencia comportamental «{foco_limpio}» y los valores de Respeto, Honestidad y Diligencia del Código de Integridad obligan al servidor de {perfil.entidad} a brindar orientación clara y trato digno al ciudadano, sin ceder a presiones que vulneren el principio de legalidad o el orden legal de los procedimientos."
                ),
                "tip": "Ante usuarios difíciles o presiones externas, la respuesta correcta jamás sacrifica la legalidad ni pierde la compostura: informa con claridad y aplica la norma.",
            },
            {
                "norma": "Ley 1952 de 2019 (Código General Disciplinario), Conflicto de Intereses y Comportamiento Ético",
                "escenario": (
                    f"Desempeñándose como {perfil.cargo} en {perfil.entidad}, le es asignado un trámite vinculado con «{funcion_apoyo}». "
                    f"Al revisar los documentos, usted advierte que el interesado directo en la actuación es un familiar suyo en segundo grado de consanguinidad."
                ),
                "pregunta": f"En aplicación de la competencia de «{foco_limpio}» y el régimen de impedimentos, ¿qué decisión debe tomar de inmediato?",
                "correcta_txt": (
                    "Declararse impedido por escrito de manera motivada ante su superior inmediato dentro del término legal (Art. 11 y 12 Ley 1437 de 2011), absteniéndose de intervenir en el trámite hasta que se designe funcionario ad hoc."
                ),
                "distractores": [
                    "Continuar tramitando el expediente en secreto procurando actuar con objetividad para no retrasar los tiempos del área.",
                    "Entregarle informalmente la carpeta a un compañero de escritorio sin dejar constancia escrita ante el superior jerárquico.",
                    "Rechazar de plano la solicitud de su familiar para demostrar severidad ante sus compañeros de dependencia.",
                ],
                "explicacion": (
                    f"El artículo 11 del CPACA y el Código General Disciplinario (Ley 1952 de 2019) establecen el deber ineludible de declararse impedido cuando concurra interés particular o parentesco dentro de los grados de ley. La transparencia y «{foco_limpio}» exigen formalizar el impedimento ante el superior."
                ),
                "tip": "Siempre que aparezca un familiar, amigo íntimo o interés directo en un trámite, la única opción válida es declararse impedido formalmente ante el superior.",
            },
        ]
    else:
        plantillas = [
            {
                "norma": f"Ley 1437 de 2011 (CPACA), Art. 29 Constitución Política y {norma_principal}",
                "escenario": (
                    f"Usted desempeña el empleo de {perfil.cargo} ({perfil.codigo_grado}) en {perfil.entidad}. "
                    f"En desarrollo del eje o función «{foco_limpio}», detecta inconsistencias de fondo en los soportes de un expediente. "
                    f"Un superior le sugiere verbalmente omitir el traslado o requerimiento previo y expedir de inmediato el acto definitivo para cumplir el indicador mensual."
                ),
                "pregunta": "¿Cuál es la actuación jurídicamente procedente según el manual de funciones y la normativa aplicable?",
                "correcta_txt": (
                    f"Adelantar el requerimiento o acto administrativo de trámite garantizando el derecho de contradicción y debido proceso (Ley 1437 de 2011 y normativa de {perfil.entidad}), dejando soporte técnico en el expediente."
                ),
                "distractores": [
                    "Expedir de inmediato el acto definitivo sin agotar la etapa previa, dando prelación a la orden verbal y a la meta estadística del área.",
                    "Archivar de plano la actuación sin emitir pronunciamiento motivado ni notificar a los interesados.",
                    "Declararse impedido sin causal legal para trasladar la responsabilidad del expediente a otra dependencia.",
                ],
                "explicacion": (
                    f"En el ejercicio de «{foco_limpio}», todo servidor de {perfil.entidad} está sujeto al principio de legalidad y al debido proceso (Art. 29 C.P. y Ley 1437 de 2011 - CPACA). Pretermitir etapas de contradicción o expedir actos sin motivación ni soporte probatorio genera nulidad del acto administrativo y responsabilidad disciplinaria."
                ),
                "tip": "En las pruebas escritas de la CNSC, ninguna meta de gestión ni orden verbal justifica saltarse etapas procesales del CPACA o de la norma especial de la entidad.",
            },
            {
                "norma": "Ley 1755 de 2015 (Derecho de Petición), Ley 1712 de 2014 (Transparencia) y Reserva Legal",
                "escenario": (
                    f"Como {perfil.cargo} en {perfil.entidad}, usted participa en actuaciones vinculadas con «{foco_limpio}». "
                    f"Un particular radica un derecho de petición solicitando copia íntegra de informes y soportes del proceso que incluyen datos privados, financieros o sujetos a reserva legal de terceros."
                ),
                "pregunta": "De acuerdo con la normativa vigente y sus competencias funcionales, ¿cómo debe gestionar esta solicitud?",
                "correcta_txt": (
                    "Responder de fondo dentro de los términos de la Ley 1755 de 2015, entregando la información de carácter público y negando de forma motivada los documentos sometidos a reserva legal con cita expresa de la norma."
                ),
                "distractores": [
                    "Remitir la totalidad de los documentos reservados invocando el principio de máxima publicidad sin aplicar excepción alguna.",
                    "Abstenerse de contestar la petición por tratarse de un trámite misional que contiene información reservada.",
                    "Enviar los documentos reservados al correo personal del peticionario bajo compromiso verbal de confidencialidad.",
                ],
                "explicacion": (
                    f"Según los artículos 24 y 25 de la Ley 1755 de 2015 y la Ley 1712 de 2014, el servidor de {perfil.entidad} debe contestar oportunamente toda petición, pero tiene el deber legal de proteger la información sujeta a reserva constitucional o legal mediante rechazo motivado que cite la disposición legal pertinente."
                ),
                "tip": "Recuerda la regla de oro de PQRSF en la CNSC: siempre se responde en término, pero la información reservada se niega mediante acto motivado citando la ley.",
            },
            {
                "norma": "Ley 594 de 2000 (Ley General de Archivo), MIPG y Trazabilidad Administrativa",
                "escenario": (
                    f"En su rol de {perfil.cargo} en {perfil.entidad}, al consolidar los soportes e informes derivados de «{foco_limpio}», "
                    f"advierte que varios documentos preparatorios y actas de verificación aún no han sido incorporados al expediente oficial antes del cierre del periodo."
                ),
                "pregunta": "Desde el marco de Gestión Documental (Ley 594 de 2000) y el Modelo Integrado de Planeación y Gestión (MIPG), ¿qué acción debe ejecutar?",
                "correcta_txt": (
                    f"Garantizar la organización, foliación e incorporación íntegra de las actas y soportes en el expediente oficial conforme a las Tablas de Retención Documental (TRD) de {perfil.entidad}."
                ),
                "distractores": [
                    "Eliminar los documentos preparatorios y conservar únicamente el informe final para ahorrar espacio en el archivo de gestión.",
                    "Conservar los soportes únicamente en un dispositivo USB personal sin registrarlos en el sistema institucional.",
                    "Postergar la conformación del expediente hasta que se cumpla el tiempo de transferencia al archivo central.",
                ],
                "explicacion": (
                    f"La Ley 594 de 2000 y la dimensión de Gestión del Conocimiento e Información del MIPG exigen mantener la integridad, disponibilidad y trazabilidad de los expedientes desde su producción en {perfil.entidad}. La sustracción o eliminación de soportes fuera de las TRD constituye falta grave."
                ),
                "tip": "Los expedientes públicos deben foliarse y conservarse íntegramente desde la etapa de gestión siguiendo las Tablas de Retención Documental (TRD).",
            },
            {
                "norma": f"Principio de Competencia Funcional y Territorial (Art. 6 y 121 C.P., Art. 21 CPACA) y {norma_principal}",
                "escenario": (
                    f"Como {perfil.cargo} ({perfil.codigo_grado}) en {perfil.entidad}, mientras ejecuta «{foco_limpio}», "
                    f"identifica hechos adicionales que requieren una actuación administrativa urgente, pero que por su naturaleza o ubicación pertenecen a la competencia exclusiva de otra dependencia o entidad pública."
                ),
                "pregunta": "Con fundamento en los principios constitucionales de la Función Pública y el manual específico de funciones, ¿cómo debe actuar?",
                "correcta_txt": (
                    f"Adelantar las actuaciones que corresponden estrictamente a la competencia y jurisdicción de su cargo en {perfil.entidad}, y remitir formalmente por competencia (Art. 21 CPACA) los demás hallazgos a la autoridad competente."
                ),
                "distractores": [
                    "Asumir de oficio la totalidad del caso, incluyendo los asuntos ajenos a su competencia, invocando el principio de celeridad.",
                    "Inhibirse de actuar incluso frente a los hechos que sí son de su competencia y archivar todo el trámite.",
                    "Informar verbalmente al ciudadano que el trámite queda cancelado sin realizar el traslado oficial a la entidad competente.",
                ],
                "explicacion": (
                    f"Conforme a los artículos 6 y 121 de la Constitución Política, los servidores públicos solo pueden hacer aquello que les está expresamente atribuido en la ley y en el Manual de Funciones ({perfil.cargo}). Actuar sin competencia vicia de nulidad el acto, por lo que debe ejercerse la función propia y darse traslado formal (Art. 21 Ley 1437 de 2011) de lo ajeno."
                ),
                "tip": "Si un caso excede tu competencia funcional o jurisdicción, nunca decidas de fondo sobre lo ajeno ni lo ignores: actúa en lo propio y traslada por el Art. 21 del CPACA.",
            },
            {
                "norma": f"Notificación de Actos Administrativos (Art. 67 a 69 Ley 1437 de 2011 - CPACA) y {norma_principal}",
                "escenario": (
                    f"Dentro de un procedimiento administrativo en {perfil.entidad} asociado a «{foco_limpio}», se profiere una decisión de carácter particular y concreto que afecta directamente los derechos de un administrado. "
                    f"Un compañero sugiere publicarla únicamente en la cartelera interna de la oficina sin citar al interesado ni enviarla al correo electrónico autorizado."
                ),
                "pregunta": "Para que el acto administrativo sea oponible y produzca efectos legales conforme al CPACA, ¿cuál es el trámite obligatorio?",
                "correcta_txt": (
                    "Efectuar la notificación personal al interesado (o por medio electrónico si dio autorización expresa), entregándole copia íntegra del acto e indicándole los recursos que legalmente proceden, las autoridades ante quienes deben interponerse y los plazos para hacerlo."
                ),
                "distractores": [
                    "Fijar únicamente una nota en la puerta de la dependencia dando por ejecutoriado el acto el mismo día de su firma.",
                    "Ejecutar materialmente la decisión sin notificar al ciudadano, argumentando que los actos de la administración gozan de presunción de legalidad.",
                    "Comunicar la decisión por llamada telefónica informal omitiendo mencionar los recursos de reposición o apelación.",
                ],
                "explicacion": (
                    f"Según los artículos 67 y 72 de la Ley 1437 de 2011 (CPACA), los actos administrativos de carácter particular que pongan término a una actuación en {perfil.entidad} deben notificarse personalmente (o por aviso en subsidio), señalando los recursos procedentes. Sin este requisito, la decisión no produce efectos legales."
                ),
                "tip": "Todo acto administrativo definitivo de carácter particular exige notificación personal (física o electrónica autorizada) e indicación expresa de los recursos de ley.",
            },
            {
                "norma": "Modelo Integrado de Planeación y Gestión (MIPG), Control Interno (Ley 87 de 1993) y Mejora Continua",
                "escenario": (
                    f"Al evaluar los indicadores trimestrales de su dependencia en {perfil.entidad} relacionados con «{foco_limpio}», "
                    f"se evidencia un cuello de botella recurrente que retrasa los tiempos de respuesta frente a los lineamientos institucionales establecidos."
                ),
                "pregunta": "Desde el enfoque del Modelo Integrado de Planeación y Gestión (MIPG) y el autocontrol, ¿cuál es la actuación técnica adecuada?",
                "correcta_txt": (
                    "Analizar las causas raíz del retraso con datos estadísticos verificables, documentar el plan de mejoramiento preventivo/correctivo dentro de los procedimientos del Sistema de Gestión y hacer seguimiento a los indicadores."
                ),
                "distractores": [
                    "Modificar manualmente las fechas de radicación en el reporte estadístico para aparentar un cumplimiento del 100% ante Planeación.",
                    "Esperar a que la Oficina de Control Interno o un ente externo imponga un hallazgo de auditoría para empezar a revisar el proceso.",
                    "Suspender la recepción de nuevas solicitudes ciudadanas durante la última semana de cada mes.",
                ],
                "explicacion": (
                    f"En el marco de la Ley 87 de 1993 y la Séptima Dimensión del MIPG (Control Interno y Línea Estratégica de Defensa), cada servidor de {perfil.entidad} es responsable del autocontrol y la mejora continua en el ejercicio de «{foco_limpio}», debiendo reportar información fidedigna y formular acciones correctivas oportunas."
                ),
                "tip": "En preguntas sobre MIPG o Control Interno, recuerda el principio de 'Autocontrol': el propio funcionario detecta, documenta y mejora su proceso con datos reales.",
            },
            {
                "norma": "Ley 1437 de 2011 (Art. 45 Corrección de Errores Formales vs. Revocatoria Directa Art. 93)",
                "escenario": (
                    f"En ejercicio del cargo de {perfil.cargo} en {perfil.entidad} y cumpliendo con «{foco_limpio}», usted proyectó un acto administrativo que ya fue firmado. "
                    f"Antes de su archivo, nota que en un cuadro estadístico del documento hubo un error puramente aritmético y de digitación que no cambia en absoluto el sentido material de la decisión."
                ),
                "pregunta": "Conforme al artículo 45 de la Ley 1437 de 2011 (CPACA), ¿qué mecanismo jurídico procede en este caso?",
                "correcta_txt": (
                    "Proyectar acto de corrección de errores formales (de oficio o a petición de parte) rectificando el dato aritmético sin alterar el sentido material de la decisión ni revivir términos legales vencidos."
                ),
                "distractores": [
                    "Destruir físicamente el acto original firmado y reemplazarlo sin dejar constancia ni acto administrativo de corrección.",
                    "Exigirle al ciudadano que demande el acto ante la Jurisdicción de lo Contencioso Administrativo para corregir el número digitado.",
                    "Aplicar tachones con corrector líquido sobre la resolución original ya numerada y fechada.",
                ],
                "explicacion": (
                    f"El artículo 45 del CPACA faculta a las autoridades de {perfil.entidad} para corregir en cualquier tiempo, de oficio o a petición de parte, los errores simplemente formales (aritméticos, de digitación, de transcripción o de omisión de palabras) mediante acto motivado, siempre que ello no cambie el sentido material de la decisión."
                ),
                "tip": "Distingue siempre en el CPACA: los errores aritméticos o de digitación que NO cambian el sentido del fallo se corrigen en cualquier tiempo mediante el Art. 45.",
            },
        ]

    # Rotación sin repetición de plantillas
    if not st.session_state.plantillas_orden or max(st.session_state.plantillas_orden, default=0) >= len(plantillas):
        indices = list(range(len(plantillas)))
        random.shuffle(indices)
        st.session_state.plantillas_orden = indices

    idx_elegido = st.session_state.plantillas_orden.pop(0)
    plantilla = plantillas[idx_elegido % len(plantillas)]

    opciones_textos = [plantilla["correcta_txt"]] + plantilla["distractores"]
    random.shuffle(opciones_textos)

    letras = ["A", "B", "C", "D"]
    opciones_dict = {}
    letra_correcta = "A"
    for i, txt_op in enumerate(opciones_textos):
        opciones_dict[letras[i]] = txt_op
        if txt_op == plantilla["correcta_txt"]:
            letra_correcta = letras[i]

    enunciado_completo = f"{plantilla['escenario']} {plantilla['pregunta']}"
    return {
        "eje_evaluado": recortar_sin_cortar_palabra(foco_evaluacion, 105),
        "pregunta": enunciado_completo,
        "opciones": opciones_dict,
        "correcta": letra_correcta,
        "explicacion": plantilla["explicacion"],
        "tip_estrategico": plantilla["tip"],
        "fuente": f"{perfil.nombre_archivo} + {plantilla['norma']}",
        "fragmento_soporte": foco_limpio,
        "_id": hashlib.md5(f"{enunciado_completo}_{foco_limpio}_{idx_elegido}".encode()).hexdigest(),
    }


# ==========================================
# MOTOR HÍBRIDO DE CLAVE IA Y CONECTOR UNIVERSAL
# ==========================================


def obtener_api_key_respaldo() -> str:
    try:
        if "GEMINI_API_KEY" in st.secrets:
            return str(st.secrets["GEMINI_API_KEY"]).strip()
    except Exception:
        pass
    return os.environ.get("GEMINI_API_KEY", "").strip()


def limpiar_json_ia(raw: str) -> Optional[dict]:
    if not raw:
        return None
    limpio = re.sub(r"```(?:json)?", "", raw.strip(), flags=re.IGNORECASE)
    limpio = re.sub(r"```", "", limpio).strip()
    m = re.search(r"\{.*\}", limpio, re.DOTALL)
    if m:
        limpio = m.group(0)
    try:
        return json.loads(limpio, strict=False)
    except Exception:
        limpio_sin_saltos = re.sub(r"[\r\n\t]+", " ", limpio)
        try:
            return json.loads(limpio_sin_saltos, strict=False)
        except Exception:
            return None


def llamar_gemini_universal(
    api_key: str, prompt: str, imagenes_png: Optional[List[bytes]] = None
) -> Optional[str]:
    key = api_key.strip()
    if not key:
        return None
    st.session_state.ultimo_error_ia = ""

    es_vertex_key = key.startswith("AQ.")
    errores_vistos = []

    # 1. Intento mediante SDK oficial google-genai (Soporta claves AQ. y AIzaSy)
    for mod in MODELOS_GEMINI:
        for v_mode in ([True, False] if es_vertex_key else [False, True]):
            try:
                cli = genai.Client(vertexai=v_mode, api_key=key)
                contenidos = [prompt]
                if imagenes_png:
                    for img_b in imagenes_png[:2]:
                        contenidos.append(
                            types.Part.from_bytes(data=img_b, mime_type="image/png")
                        )
                r = cli.models.generate_content(
                    model=mod,
                    contents=contenidos,
                    config=types.GenerateContentConfig(
                        temperature=0.45,
                        response_mime_type="application/json",
                    ),
                )
                if r and r.text:
                    st.session_state.ultimo_error_ia = ""
                    return r.text
            except Exception as e:
                errores_vistos.append(str(e)[:120])
                continue

    # 2. Respaldo mediante petición REST directa
    parts_rest = [{"text": prompt}]
    if imagenes_png:
        for img_b in imagenes_png[:2]:
            b64_img = base64.b64encode(img_b).decode("utf-8")
            parts_rest.append(
                {"inlineData": {"mimeType": "image/png", "data": b64_img}}
            )

    payload_bytes = json.dumps(
        {
            "contents": [{"role": "user", "parts": parts_rest}],
            "generationConfig": {
                "temperature": 0.45,
                "responseMimeType": "application/json",
            },
        }
    ).encode("utf-8")

    for mod in MODELOS_GEMINI:
        urls = (
            [
                f"https://aiplatform.googleapis.com/v1/publishers/google/models/{mod}:generateContent?key={key}",
                f"https://generativelanguage.googleapis.com/v1beta/models/{mod}:generateContent?key={key}",
            ]
            if es_vertex_key
            else [
                f"https://generativelanguage.googleapis.com/v1beta/models/{mod}:generateContent?key={key}",
            ]
        )

        for url in urls:
            try:
                req = urllib.request.Request(
                    url,
                    data=payload_bytes,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=25) as resp:
                    resp_data = json.loads(resp.read().decode("utf-8"))
                    cands = resp_data.get("candidates", [])
                    if cands:
                        partes_resp = cands[0].get("content", {}).get("parts", [])
                        texto_out = "".join(p.get("text", "") for p in partes_resp).strip()
                        if texto_out:
                            st.session_state.ultimo_error_ia = ""
                            return texto_out
            except Exception as e:
                errores_vistos.append(str(e)[:120])
                continue

    if errores_vistos:
        st.session_state.ultimo_error_ia = errores_vistos[0]
    return None


def extraer_pdf_con_imagenes(
    nombre: str, datos: bytes
) -> Tuple[str, List[Pagina], List[bytes]]:
    pags = []
    full_txt = ""
    imgs_png = []
    try:
        doc = fitz.open(stream=datos, filetype="pdf")
        for i in range(len(doc)):
            page = doc[i]
            bloques = page.get_text("blocks")
            bloques.sort(key=lambda b: (round(b[1], 1), round(b[0], 1)))
            t = "\n".join(
                b[4].strip() for b in bloques if len(b) > 4 and str(b[4]).strip()
            )
            if not t:
                t = page.get_text("text").strip()
            if t:
                pags.append(Pagina(nombre, i + 1, t))
                full_txt += f"\n--- PÁGINA {i+1} ---\n" + t

            if i < 2:
                pix = page.get_pixmap(dpi=130)
                imgs_png.append(pix.tobytes("png"))
        doc.close()
        return full_txt, pags, imgs_png
    except Exception as e:
        st.error(f"Error al leer {nombre}: {e}")
        return "", [], []


def analizar_manual_universal(
    api_key: str,
    nombre_archivo: str,
    texto: str,
    imagenes_png: Optional[List[bytes]] = None,
) -> PerfilManual:
    perfil_base = extraer_perfil_local_inteligente(nombre_archivo, texto)

    if not api_key.strip():
        return perfil_base

    usar_imgs = imagenes_png if len(texto.strip()) < 350 else None
    muestra = texto[:20000]

    prompt = f"""Eres un experto en análisis de Manuales Específicos de Funciones y Competencias Laborales de Colombia (CNSC, DIAN, Contralorías, Alcaldías, Gobernaciones, Personerías, Ministerios, Institutos).

Analiza el siguiente Manual de Funciones y extrae TODA su estructura con total fidelidad:

{muestra}

DEVUELVE ÚNICAMENTE UN OBJETO JSON VÁLIDO CON ESTA ESTRUCTURA EXACTA:
{{
  "entidad": "Nombre de la entidad pública que expide el manual",
  "cargo": "Denominación exacta del empleo",
  "codigo_grado": "Código, Grado y Ficha/OPEC",
  "nivel": "Nivel jerárquico y proceso o dependencia",
  "proposito": "Propósito principal completo y exacto del empleo",
  "funciones_esenciales": ["1. ...", "2. ...", "3. ..."],
  "conocimientos_ejes": ["Conocimiento básico o eje temático 1...", "Conocimiento 2..."],
  "competencias_funcionales": ["Competencia funcional 1...", "Competencia funcional 2..."],
  "competencias_comportamentales": ["Competencia comportamental 1...", "Competencia 2..."],
  "requisitos": "Requisitos completos de estudio (NBC/Títulos) y experiencia"
}}"""

    raw = llamar_gemini_universal(api_key, prompt, imagenes_png=usar_imgs)
    d = limpiar_json_ia(raw) if raw else None
    if isinstance(d, dict) and (d.get("cargo") or d.get("funciones_esenciales")):
        return PerfilManual(
            nombre_archivo=nombre_archivo,
            entidad=str(d.get("entidad") or perfil_base.entidad),
            cargo=str(d.get("cargo") or perfil_base.cargo),
            codigo_grado=str(d.get("codigo_grado") or perfil_base.codigo_grado),
            nivel=str(d.get("nivel") or perfil_base.nivel),
            proposito=str(d.get("proposito") or perfil_base.proposito),
            funciones_esenciales=list(d.get("funciones_esenciales") or perfil_base.funciones_esenciales),
            conocimientos_ejes=list(d.get("conocimientos_ejes") or perfil_base.conocimientos_ejes),
            competencias_funcionales=list(d.get("competencias_funcionales") or perfil_base.competencias_funcionales),
            competencias_comportamentales=list(d.get("competencias_comportamentales") or perfil_base.competencias_comportamentales),
            requisitos=str(d.get("requisitos") or perfil_base.requisitos),
            analizado_por_ia=True,
        )

    return perfil_base


def generar_pregunta_por_eje(
    api_key: str,
    perfil: PerfilManual,
    modalidad_eje: str,
    item_especifico: str,
    dificultad: str,
) -> dict:
    # Selección inteligente SIN REPETIR funciones ni competencias
    if modalidad_eje.startswith("🎲"):
        categorias = [
            ("FUNCIÓN ESENCIAL DEL CARGO", perfil.funciones_esenciales),
            ("EJE TEMÁTICO / CONOCIMIENTO ESENCIAL", perfil.conocimientos_ejes),
            ("COMPETENCIA FUNCIONAL", perfil.competencias_funcionales),
            ("COMPETENCIA COMPORTAMENTAL (Juicio Situacional)", perfil.competencias_comportamentales),
        ]
        categorias_validas = [(nombre, lista) for nombre, lista in categorias if lista]
        if categorias_validas:
            cat_nombre, lista_items = random.choice(categorias_validas)
            foco_evaluacion = elegir_item_sin_repetir(cat_nombre, lista_items, perfil.proposito)
        else:
            foco_evaluacion = f"PROPÓSITO Y FUNCIONES: {perfil.proposito}"
    elif modalidad_eje.startswith("📋"):
        foco_evaluacion = elegir_item_sin_repetir(
            "FUNCIÓN ESENCIAL", perfil.funciones_esenciales, perfil.proposito
        )
    elif modalidad_eje.startswith("📘"):
        combinada = perfil.conocimientos_ejes + perfil.competencias_funcionales
        foco_evaluacion = elegir_item_sin_repetir(
            "EJE TEMÁTICO / FUNCIONAL", combinada, perfil.proposito
        )
    elif modalidad_eje.startswith("🤝"):
        foco_evaluacion = elegir_item_sin_repetir(
            "COMPETENCIA COMPORTAMENTAL",
            perfil.competencias_comportamentales,
            "Comportamiento Ético, Adaptabilidad y Trabajo en Equipo",
        )
    else:
        foco_evaluacion = f"ENFOQUE ESPECÍFICO: {item_especifico}"

    norma_sectorial = detectar_normativa_sectorial(perfil, foco_evaluacion)
    eje_etiqueta = recortar_sin_cortar_palabra(foco_evaluacion, 105)

    if api_key.strip():
        texto_doc = st.session_state.manuales_texto.get(perfil.nombre_archivo, "")
        texto_contexto = construir_texto_desde_perfil(perfil) + "\n\n" + texto_doc[:4500]
        usar_imgs = (
            st.session_state.manuales_imgs.get(perfil.nombre_archivo)
            if len(texto_doc.strip()) < 350
            else None
        )

        prompt = f"""Actúa como un experto constructor de pruebas escritas de Juicio Situacional para concursos públicos de méritos en Colombia (CNSC, DIAN, Contralorías, Alcaldías, Gobernaciones, Universidad Libre, UNAL, ESAP).

ENTIDAD: {perfil.entidad}
CARGO A EVALUAR: {perfil.cargo} ({perfil.codigo_grado}) - {perfil.nivel}
PROPÓSITO PRINCIPAL: {perfil.proposito}
EJE SELECCIONADO PARA ESTA PREGUNTA: {foco_evaluacion}
MARCO NORMATIVO APLICABLE A LA ENTIDAD Y FUNCIÓN: {norma_sectorial}
DIFICULTAD: {dificultad}
SEMILLA DE VARIACIÓN PARA EVITAR REPETICIONES: {random.randint(1000, 99999)}

ESTRUCTURA DEL MANUAL DE FUNCIONES:
{texto_contexto}

INSTRUCCIONES DE DISEÑO:
1. Cruza automáticamente el EJE SELECCIONADO ({foco_evaluacion}) con la legislación colombiana específica aplicable a {perfil.entidad} ({norma_sectorial}).
2. Crea un CASO SITUACIONAL REALISTA E INÉDITO ubicado en la dependencia del cargo ({perfil.cargo} en {perfil.entidad}), donde se presente un dilema técnico, normativo, procedimental o comportamental. No cortes ninguna palabra a la mitad.
3. Formula un enunciado claro y 4 opciones de actuación (A, B, C, D) con estilo oficial de prueba CNSC.
4. Solo UNA opción debe ser la respuesta correcta; las otras 3 deben ser distractores plausibles.
5. En "explicacion", justifica detalladamente por qué la opción correcta es la única válida citando la norma aplicable a la entidad y por qué se descartan las demás.
6. En "fragmento_soporte", cita la función, competencia o conocimiento del manual que respalda la pregunta.

DEVUELVE ÚNICAMENTE ESTE JSON VÁLIDO:
{{"eje_evaluado":"{eje_etiqueta}","pregunta":"...","opciones":{{"A":"...","B":"...","C":"...","D":"..."}},"correcta":"A","explicacion":"...","tip_estrategico":"...","fuente":"{perfil.nombre_archivo}","fragmento_soporte":"..."}}"""

        raw = llamar_gemini_universal(api_key, prompt, imagenes_png=usar_imgs)
        data = limpiar_json_ia(raw) if raw else None
        if (
            isinstance(data, dict)
            and isinstance(data.get("opciones"), dict)
            and data.get("correcta") in ["A", "B", "C", "D"]
        ):
            data["eje_evaluado"] = recortar_sin_cortar_palabra(
                data.get("eje_evaluado", eje_etiqueta), 105
            )
            data["_id"] = hashlib.md5(str(data.get("pregunta", "")).encode()).hexdigest()
            return data

    return generar_pregunta_local_juridica(perfil, foco_evaluacion, dificultad)


# ==========================================
# BARRA LATERAL (SIDEBAR)
# ==========================================
st.sidebar.markdown("## 🏛️ Cuaderno de Méritos IA")
st.sidebar.caption("Entrenador Inteligente para Concursos Públicos en Colombia")

lic = st.session_state.licencia_info
if lic["activa"]:
    st.sidebar.success(
        f"👑 **PLAN PRO ACTIVO**\n\nID: `{lic['cedula']}`\nVence: **{lic['vence']}**"
    )
else:
    disp = max(0, LIMITE_PREGUNTAS_GRATIS - st.session_state.usos_gratis)
    st.sidebar.warning(
        f"🎁 **Prueba Gratuita Activa:** Tienes **{disp}** de {LIMITE_PREGUNTAS_GRATIS} preguntas gratis disponibles."
    )

texto_viral = (
    "🔥 ¡Te recomiendo este Simulador con Inteligencia Artificial para Concursos de Méritos (CNSC, DIAN, Contralorías, Alcaldías, Gobernaciones y Entidades Nacionales)! "
    "Subes el PDF del Manual de Funciones de tu OPEC y te genera preguntas de Juicio Situacional sobre tus funciones reales (incluye 5 preguntas gratis): "
    f"{URL_APP_PUBLICA}"
)
link_wa_share = f"https://wa.me/?text={urllib.parse.quote(texto_viral)}"
st.sidebar.markdown(
    f'<a href="{link_wa_share}" target="_blank" class="btn-share">📲 Recomendar esta App en WhatsApp</a>',
    unsafe_allow_html=True,
)

# 1. Configuración Híbrida de Clave IA
st.sidebar.markdown("---")
st.sidebar.subheader("🔑 1. Conexión de IA")
clave_respaldo = obtener_api_key_respaldo()
api_key_input = st.sidebar.text_input(
    "Clave GEMINI_API_KEY (Opcional - Motor Activo):",
    type="password",
    help="El simulador ya cuenta con su motor jurídico activo. Opcionalmente puedes pegar una clave AIzaSy... de Google AI Studio.",
).strip()

api_key_user = api_key_input if api_key_input else clave_respaldo
st.sidebar.success("⚡ Motor Jurídico CNSC Conectado y Activo.")

with st.sidebar.expander("❓ ¿Cómo funciona o cómo conectar clave propia?"):
    st.markdown(
        """
        * **Modo Automático:** Ya puedes subir tu Manual PDF y entrenar de inmediato sin configurar nada adicional.
        * **Clave Propia (Opcional):** Si deseas conectar tu propia llave de [**Google AI Studio**](https://aistudio.google.com/api-keys), haz clic en el icono de copiar junto a tu clave (`AIzaSy...`) y pégala arriba.
        """
    )

# 2. Carga de Manuales con Perfilamiento Instantáneo
st.sidebar.markdown("---")
st.sidebar.subheader("📂 2. Sube tu Manual OPEC")
archivos_up = st.sidebar.file_uploader(
    "Sube solo tu Manual de Funciones (y Leyes opcionales)",
    type=["pdf", "txt"],
    accept_multiple_files=True,
    key=f"uploader_{st.session_state.uploader_key}",
    help="Sirve para cualquier convocatoria (DIAN, Contraloría, Alcaldías, Gobernaciones, SENA, ICBF, etc.).",
)

if archivos_up:
    for arc in archivos_up:
        if arc.name not in st.session_state.manuales_texto:
            b_data = arc.read()
            if arc.name.lower().endswith(".pdf"):
                txt_doc, pags, imgs_png = extraer_pdf_con_imagenes(arc.name, b_data)
                st.session_state.manuales_imgs[arc.name] = imgs_png
            else:
                txt_doc = b_data.decode("utf-8", errors="ignore")
                pags = [Pagina(arc.name, 1, txt_doc)]
                st.session_state.manuales_imgs[arc.name] = []

            st.session_state.manuales_texto[arc.name] = txt_doc or "Documento PDF"
            st.session_state.paginas.extend(pags)

archivos_nuevos = [
    k for k in st.session_state.manuales_texto.keys() if k not in st.session_state.perfiles
]
if archivos_nuevos:
    for k_pend in archivos_nuevos:
        with st.spinner(f"🔍 Perfilando funciones y ejes de {k_pend}..."):
            st.session_state.perfiles[k_pend] = analizar_manual_universal(
                api_key_user,
                k_pend,
                st.session_state.manuales_texto[k_pend],
                imagenes_png=st.session_state.manuales_imgs.get(k_pend),
            )
            st.session_state.items_usados = set()

nombres_manuales = list(st.session_state.perfiles.keys())

if nombres_manuales:
    manual_activo_key = st.sidebar.selectbox(
        "Selecciona el Manual / Cargo para Entrenar:",
        nombres_manuales,
        index=0,
    )
    perfil_activo = st.session_state.perfiles[manual_activo_key]

    c_b1, c_b2 = st.sidebar.columns(2)
    with c_b1:
        if st.button("🔄 Re-analizar IA", use_container_width=True):
            with st.spinner("Actualizando perfil del manual..."):
                st.session_state.perfiles[manual_activo_key] = analizar_manual_universal(
                    api_key_user,
                    manual_activo_key,
                    st.session_state.manuales_texto[manual_activo_key],
                    imagenes_png=st.session_state.manuales_imgs.get(manual_activo_key),
                )
                st.session_state.items_usados = set()
                st.rerun()
    with c_b2:
        if st.button("🗑️ Limpiar PDF", use_container_width=True):
            st.session_state.perfiles = {}
            st.session_state.manuales_texto = {}
            st.session_state.manuales_imgs = {}
            st.session_state.paginas = []
            st.session_state.items_usados = set()
            if "q_actual" in st.session_state:
                del st.session_state.q_actual
            st.session_state.uploader_key += 1
            st.rerun()
else:
    st.sidebar.info("💡 Sube las páginas del Manual de Funciones de tu cargo para comenzar.")
    perfil_activo = PerfilManual(
        nombre_archivo="ninguno",
        entidad="Todos los Concursos de Méritos en Colombia",
        cargo="Cuaderno Inteligente de Preparación OPEC",
        codigo_grado="CNSC • Nacional y Territorial",
        nivel="Nivel Profesional, Técnico y Asistencial",
        proposito="Sube únicamente el PDF del Manual de Funciones de tu cargo en la barra izquierda. El motor identifica tus funciones esenciales y las cruza automáticamente con la legislación aplicable a tu entidad.",
        analizado_por_ia=False,
    )

# 3. Modo de Entrenamiento Universal + Dinámico
st.sidebar.markdown("---")
st.sidebar.subheader("🎯 3. Modo de Entrenamiento")
modalidad_eje = st.sidebar.selectbox(
    "¿Sobre qué quieres que te evalúe la IA?",
    [
        "🎲 Aleatoria Integral (Todo tu Manual)",
        "📋 Solo Funciones Esenciales del Cargo",
        "📘 Solo Ejes Temáticos y Funcionales",
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
    if todos_los_items:
        item_especifico = st.sidebar.selectbox(
            "Selecciona el punto exacto de tu manual:", todos_los_items
        )

dificultad = st.sidebar.select_slider(
    "Nivel de Dificultad",
    options=["Básica", "Alta", "Muy Alta (Nivel Prueba Oficial CNSC)"],
    value="Alta",
)
cantidad_simulacro = st.sidebar.selectbox("Preguntas por Simulacro", [5, 10, 15, 20], index=0)

# 4. Licencias y Panel Admin Blindado con Seriales Únicos
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
    if pwd_admin and pwd_admin.strip() == obtener_clave_admin_segura():
        st.markdown("**Generar licencia única tras confirmar pago en Nequi:**")
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
        if st.button("🎲 Generar Nuevo Serial Único", use_container_width=True):
            st.session_state.serial_salt = secrets.token_hex(2).upper()[:3]
        if ced_comprador:
            folio_unico = hashlib.md5(
                f"{ced_comprador.strip()}_{st.session_state.serial_salt}".encode()
            ).hexdigest().upper()[:3]
            token_generado = generar_licencia_temporal(
                ced_comprador, plan_dias[0], folio=folio_unico
            )
            st.code(
                f"Cédula: {ced_comprador.strip()}\nCódigo PRO: {token_generado}\nVigencia: {plan_dias[0]} días"
            )
            st.caption("Cada código tiene firma única vinculada a la cédula del comprador.")

# ==========================================
# GUÍA VISUAL DE 3 PASOS + CABECERA EDITORIAL
# ==========================================
s1, s2, s3 = st.columns(3)
with s1:
    st.markdown(
        '<div class="step-card step-ok"><div><b>✅ Paso 1: Motor Jurídico IA</b><br><small>Conectado y activo</small></div></div>',
        unsafe_allow_html=True,
    )
with s2:
    ok_man = bool(nombres_manuales and getattr(perfil_activo, "analizado_por_ia", False))
    cls2 = "step-ok" if ok_man else "step-wait"
    ico2 = "✅" if ok_man else "2️⃣"
    cargo_paso2 = recortar_sin_cortar_palabra(perfil_activo.cargo, 42)
    st.markdown(
        f'<div class="step-card {cls2}"><div><b>{ico2} Paso 2: Tu Manual OPEC</b><br><small>{html.escape(cargo_paso2) if ok_man else "Sube solo tu Manual de Funciones PDF"}</small></div></div>',
        unsafe_allow_html=True,
    )
with s3:
    ok_todo = bool(ok_man)
    cls3 = "step-ok" if ok_todo else "step-wait"
    ico3 = "🚀" if ok_todo else "3️⃣"
    st.markdown(
        f'<div class="step-card {cls3}"><div><b>{ico3} Paso 3: Entrenar y Ganar</b><br><small>{"¡Listo! Tienes 5 preguntas de prueba" if ok_todo else "Sube tu PDF en el Paso 2"}</small></div></div>',
        unsafe_allow_html=True,
    )

if not nombres_manuales:
    st.markdown(
        f"""
        <div class="cuaderno-cover">
            <span class="eje-badge">📘 PLATAFORMA INTEGRAL DE PREPARACIÓN • TODOS LOS CONCURSOS CNSC</span>
            <div class="cuaderno-serif">Cuaderno Oficial de Méritos IA</div>
            <p class="cuaderno-sub">
                <b>Entrena para cualquier convocatoria pública en Colombia</b> (Orden Nacional, Territorial, DIAN, Contralorías, Alcaldías, Gobernaciones, Personerías, SENA, ICBF e INPEC).<br>
                Solo sube el <b>Manual de Funciones (OPEC)</b> de tu cargo: nuestra plataforma extrae tus funciones esenciales y las cruza automáticamente con la legislación aplicable a tu entidad para evaluarte con casos reales de <b>Juicio Situacional</b>.
            </p>
            <div style="display:flex; gap:12px; flex-wrap:wrap; align-items:center;">
                <span class="dif-badge">🎁 Incluye {LIMITE_PREGUNTAS_GRATIS} Preguntas Gratis de Prueba</span>
                <span class="eje-badge">⚖️ Cruce Automático con Leyes de tu Entidad</span>
                <a href="{link_wa_share}" target="_blank" style="color:#1e3a8a; font-weight:700; font-size:13.5px; text-decoration:underline;">📲 Compartir con mi grupo de estudio</a>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
else:
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
        if nombres_manuales
        else 0
    )
    st.markdown(
        f'<div class="kpi-box"><div class="kpi-label">Funciones y Ejes Detectados</div><div class="kpi-num">{total_items_manual}</div></div>',
        unsafe_allow_html=True,
    )
with k4:
    est_txt = (
        f"PRO (Vence {lic['vence']})"
        if lic["activa"]
        else f"DEMO ({max(0, LIMITE_PREGUNTAS_GRATIS - st.session_state.usos_gratis)} de {LIMITE_PREGUNTAS_GRATIS} disp.)"
    )
    st.markdown(
        f'<div class="kpi-box"><div class="kpi-label">Estado de tu Cuenta</div><div class="kpi-num" style="font-size:16px; color:#16a34a;">{est_txt}</div></div>',
        unsafe_allow_html=True,
    )

st.write("")

# ==========================================
# PESTAÑAS DE LA PLATAFORMA (SIEMPRE VISIBLES)
# ==========================================
tab_sim, tab_ficha, tab_comp, tab_planes = st.tabs([
    "🎯 Simulador Inteligente",
    "📋 Radiografía de tu Manual",
    "🔄 Comparador de Cargos (OPEC)",
    "💎 Planes y Activación Nequi / Llave",
])


def renderizar_planes_de_pago():
    st.markdown(
        """
        <div style="text-align:center; margin-bottom:18px;">
            <h3>🚀 Elige tu Plan de Entrenamiento y Asegura tu Puesto en el Concurso</h3>
            <p style="color:#475569;">Funciona para <b>todos los concursos de méritos en Colombia</b> (DIAN, Contralorías, Alcaldías, Gobernaciones y Entidades Nacionales). Solo subes el Manual de Funciones de tu OPEC y entrenas sin límites.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    p1, p2, p3 = st.columns(3)
    with p1:
        wa_1 = f"https://wa.me/{WHATSAPP_INTL}?text=Hola,%20acabo%20de%20transferir%20el%20Pase%20Intensivo%20de%20$14.900%20(7%20dias)%20a%20Nequi/Llave%20{NUMERO_NEQUI_WHATSAPP}.%20Adjunto%20comprobante.%20Mi%20cedula%20es:%20"
        st.markdown(
            f"""
            <div class="plan-card">
                <span class="eje-badge">⚡ COMPRA RÁPIDA</span>
                <h4 style="margin:10px 0 4px 0;">Pase Intensivo (7 Días)</h4>
                <div class="plan-price">$14.900 <small style="font-size:13px; color:#64748b;">COP</small></div>
                <p style="font-size:13px; color:#64748b;">Ideal para repaso intensivo antes del examen</p>
                <hr>
                <div style="text-align:left; font-size:13.5px; line-height:1.75;">
                    ✅ <b>7 días</b> de simulacros ilimitados.<br>
                    ✅ Sirve para cualquier concurso y OPEC.<br>
                    ✅ Cruce automático de funciones + leyes.<br>
                    ✅ Retroalimentación jurídica inmediata.
                </div>
                <a href="{wa_1}" target="_blank" class="btn-pay">📲 Ya transferí $14.900 • Pedir Código por WhatsApp</a>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with p2:
        wa_2 = f"https://wa.me/{WHATSAPP_INTL}?text=Hola,%20acabo%20de%20transferir%20el%20Pase%20Mensual%20PRO%20de%20$24.900%20(30%20dias)%20a%20Nequi/Llave%20{NUMERO_NEQUI_WHATSAPP}.%20Adjunto%20comprobante.%20Mi%20cedula%20es:%20"
        st.markdown(
            f"""
            <div class="plan-card-popular">
                <span class="dif-badge">⭐ EL MÁS VENDIDO • RECOMENDADO</span>
                <h4 style="margin:10px 0 4px 0;">Pase Mensual PRO (30 Días)</h4>
                <div class="plan-price">$24.900 <small style="font-size:13px; color:#64748b;">COP</small></div>
                <p style="font-size:13px; color:#1e40af; font-weight:600;">Entrenamiento completo para dominar tu OPEC</p>
                <hr>
                <div style="text-align:left; font-size:13.5px; line-height:1.75;">
                    ✅ <b>30 días completos</b> de acceso ilimitado.<br>
                    ✅ Carga ilimitada de Manuales OPEC y Normas.<br>
                    ✅ Comparador estratégico de cargos.<br>
                    ✅ Simulacros cronometrados de hasta 20 preguntas.<br>
                    ✅ Activación prioritaria por WhatsApp.
                </div>
                <a href="{wa_2}" target="_blank" class="btn-pay">📲 Ya transferí $24.900 • Activar Plan por WhatsApp</a>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with p3:
        wa_3 = f"https://wa.me/{WHATSAPP_INTL}?text=Hola,%20acabo%20de%20transferir%20el%20Pase%20Convocatoria%20de%20$39.900%20(6%20meses)%20a%20Nequi/Llave%20{NUMERO_NEQUI_WHATSAPP}.%20Adjunto%20comprobante.%20Mi%20cedula%20es:%20"
        st.markdown(
            f"""
            <div class="plan-card">
                <span class="eje-badge">👑 MÁXIMO AHORRO</span>
                <h4 style="margin:10px 0 4px 0;">Pase Semestral (6 Meses)</h4>
                <div class="plan-price">$39.900 <small style="font-size:13px; color:#64748b;">COP</small></div>
                <p style="font-size:13px; color:#64748b;">Para concursar en múltiples convocatorias todo el semestre</p>
                <hr>
                <div style="text-align:left; font-size:13.5px; line-height:1.75;">
                    ✅ <b>180 días (6 meses)</b> de acceso total.<br>
                    ✅ Válido para todas las convocatorias del país.<br>
                    ✅ Todos los modos aleatorios e integrales.<br>
                    ✅ Ahorras más del 70% frente al pase semanal.
                </div>
                <a href="{wa_3}" target="_blank" class="btn-pay">📲 Ya transferí $39.900 • Pedir Código por WhatsApp</a>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        f"""
        <div class="nequi-box">
            <h4 style="margin:0 0 6px 0;">💳 Pago Directo y Sin Comisiones (Nequi / Llave Bre-B / Transfiya)</h4>
            <p style="font-size:18px; font-weight:800; margin:4px 0; color:#be185d;">📲 Número Nequi / Llave Celular: {NUMERO_NEQUI_WHATSAPP}</p>
            <p style="font-size:13.5px; margin:6px 0 0 0;">
                <b>Paso 1:</b> Envía el valor de tu plan al número <b>{NUMERO_NEQUI_WHATSAPP}</b> desde tu App Nequi, o desde <b>cualquier banco del país</b> usando <b>Transfiya / Llave Bre-B</b>.<br>
                <b>Paso 2:</b> Haz clic en el botón verde del plan elegido para enviar tu comprobante y tu número de cédula por WhatsApp y recibir tu <b>Código PRO</b> al instante.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ------------------------------------------
# PESTAÑA 1: SIMULADOR INTELIGENTE
# ------------------------------------------
with tab_sim:
    if not nombres_manuales:
        st.warning(
            f"📂 **Paso para empezar:** Sube el **PDF del Manual de Funciones (OPEC)** de tu cargo en la Sección 2 de la barra izquierda. Tienes **{LIMITE_PREGUNTAS_GRATIS} preguntas gratis** para probar cómo el sistema cruza tus funciones con la ley."
        )
    else:
        bloqueado = (
            not lic["activa"]
            and st.session_state.usos_gratis >= LIMITE_PREGUNTAS_GRATIS
        )
        if bloqueado:
            st.error(
                f"🔒 Has completado tus {LIMITE_PREGUNTAS_GRATIS} preguntas de demostración gratuita. ¡Activa tu Plan desde **$14.900 COP** al Nequi/Llave **{NUMERO_NEQUI_WHATSAPP}** para desbloquear preguntas y simulacros ilimitados!"
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
                        "🔒 El modo Simulacro Múltiple Cronometrado es exclusivo para usuarios con Plan Activo ($14.900 / $24.900). En tu prueba gratuita de 5 preguntas utiliza el botón izquierdo de Modo Estudio."
                    )
                else:
                    with st.spinner("Generando simulacro aleatorio sin repeticiones cruzando tus funciones con la normativa vigente..."):
                        lote = []
                        vistos = set()
                        for _ in range(cantidad_simulacro * 3):
                            if len(lote) >= cantidad_simulacro:
                                break
                            q_cand = generar_pregunta_por_eje(
                                api_key_user, perfil_activo, modalidad_eje, item_especifico, dificultad
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
                if btn_una:
                    with st.spinner("Construyendo caso práctico inédito cruzando tu manual con la legislación colombiana..."):
                        q_nueva = generar_pregunta_por_eje(
                            api_key_user, perfil_activo, modalidad_eje, item_especifico, dificultad
                        )
                        if q_nueva:
                            st.session_state.q_actual = q_nueva
                            st.session_state.q_respondida = False
                            st.session_state.usos_gratis += 1
                            st.rerun()

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
                        if st.button("✅ Validar Respuesta y Ver Justificación Jurídica", type="primary"):
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
                                <small style="color:#475569;"><b>📖 Sustento en tu Manual ({html.escape(q.get('fuente',''))}):</b> <i>"{html.escape(q.get('fragmento_soporte',''))}"</i></small>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                        if st.button("➡️ Siguiente Pregunta Aleatoria", type="primary"):
                            if not lic["activa"] and st.session_state.usos_gratis >= LIMITE_PREGUNTAS_GRATIS:
                                st.rerun()
                            else:
                                with st.spinner("Generando siguiente caso práctico sin repetir eje..."):
                                    q_sig = generar_pregunta_por_eje(
                                        api_key_user, perfil_activo, modalidad_eje, item_especifico, dificultad
                                    )
                                    if q_sig:
                                        st.session_state.q_actual = q_sig
                                        st.session_state.q_respondida = False
                                        st.session_state.usos_gratis += 1
                                        st.rerun()
                else:
                    st.info(
                        "👆 Haz clic en el botón **'🎲 Generar Caso Situacional Aleatorio (Modo Estudio)'** arriba para comenzar tus 5 preguntas de prueba."
                    )

# ------------------------------------------
# PESTAÑA 2: RADIOGRAFÍA DEL MANUAL ACTIVO
# ------------------------------------------
with tab_ficha:
    if not nombres_manuales:
        st.info("📂 Sube un Manual de Funciones en la barra lateral izquierda para visualizar aquí toda la radiografía de funciones, conocimientos básicos y competencias de tu cargo.")
    else:
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
    st.caption("Sube dos o más fichas OPEC en la barra lateral para compararlas lado a lado e identificar temas comunes de estudio antes de inscribirte.")

    if not nombres_manuales:
        st.info("📂 Aún no has subido manuales. Carga tus archivos PDF en la barra lateral izquierda para habilitar el comparador.")
    else:
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
# PESTAÑA 4: PLANES Y PAGOS NEQUI / LLAVE
# ------------------------------------------
with tab_planes:
    renderizar_planes_de_pago()
