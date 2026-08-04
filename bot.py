# -*- coding: utf-8 -*-
"""
AGENCIA HAROLD JOSE - Bot de resultados de animalitos
Versión inicial desde cero, preparada para Render + GitHub.

IMPORTANTE:
- NO contiene tokens ni secretos.
- Configura las variables de entorno en Render.
- Las fuentes sin URL propia usan WINBIG_URL.
- Las loterías con fuentes adicionales pueden tener hasta 3 fuentes.
- La lógica de Ruleta Activa toma el resultado D de la fuente oficial.
- Royal NO se incluye en la tabla; se sustituye por MEGA GUACA.
- Gatazo se muestra en la tabla del bloque 50 con la hora 09:30,
  aunque su horario real informado es 09:40.
"""

import os
import re
import time
import json
import html
import logging
import threading
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup
from flask import Flask, jsonify

try:
    import telebot
except ImportError:
    telebot = None

# ---------------------------------------------------------------------
# CONFIGURACIÓN GENERAL
# ---------------------------------------------------------------------

TIMEZONE = os.getenv("TIMEZONE", "America/Caracas")
TZ = ZoneInfo(TIMEZONE)

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
CHANNEL_ID = os.getenv("CHANNEL_ID", "@AGHAROLDJOSE_BOT").strip()
TEST_CHANNEL_ID = os.getenv("TEST_CHANNEL_ID", "@pruebajsj").strip()

# Permite seleccionar el canal activo sin tocar el código.
ACTIVE_CHANNEL_ID = os.getenv("ACTIVE_CHANNEL_ID", TEST_CHANNEL_ID).strip()

# URL global para las loterías que no tienen fuente específica.
WINBIG_URL = "https://lotery.winbigvzla.com/resultados"

# Fuentes proporcionadas por el usuario.
OFFICIAL_SOURCES = {
    "L.ACT": "https://www.lottoactivo.com/resultados/lotto_activo/",
    "G.ARO": "https://www.guacharoactivo.com.ve/resultados",
    "CHAIMA": "https://lotochaima.com/",
    "GRAJ": "https://lagranjitaonline.com/",
    "SELV": "https://www.selvaplus.com/resultados",
    "MONJE": "https://www.lottoactivo.com/resultados/lottoactivo2(monjemillonario)/",
    "L.RD": "https://www.lottoactivo.com/resultados/lotto_activo_internacional/",
    "GUACA": WINBIG_URL,
    "M.GUAC": WINBIG_URL,
    "G.ITO": "https://elguacharitomillonario.com/",
    "TRIO": "https://www.lottoactivo.com/resultados/trio_activo/",
    "GUACA37": "https://www.guacaactiva.com/",
    "R.ACT": "https://www.ruletactiva.com.ve/",
}

ALTERNATIVE_SOURCES = {
    "L.ACT": ["https://resultados365.com/resultados/lotto-activo"],
    "GRAJ": ["https://resultados365.com/resultados/la-granjita/"],
    "SELV": ["https://resultados365.com/resultados/selvaplus/"],
    "R.ACT": ["https://loteriadehoy.com/animalito/ruletaactiva/resultados/"],
}

# ---------------------------------------------------------------------
# LOTERÍAS / TABLAS
# ---------------------------------------------------------------------

# Cada entrada: código, nombre, bloque, hora inicial, hora final, frecuencia.
# Las fuentes no especificadas se resuelven automáticamente contra WINBIG_URL.

LOTTERIES = {
    "L.ACT":   {"name": "Lotto Activo", "block": 10, "start": "08:00", "end": "19:00"},
    "GRAJ":    {"name": "La Granjita", "block": 10, "start": "08:00", "end": "19:00"},
    "SELV":    {"name": "Selva Plus", "block": 10, "start": "08:00", "end": "19:00"},
    "G.ARO":   {"name": "Guácharo Activo", "block": 10, "start": "08:00", "end": "19:00"},
    "CHAIMA":  {"name": "Loto Chaima", "block": 10, "start": "08:00", "end": "19:00"},
    "R.PER":   {"name": "Ruleton Perú", "block": 10, "start": "08:00", "end": "20:00"},
    "R.COL":   {"name": "Ruleton Colombia", "block": 10, "start": "08:00", "end": "20:00"},
    "R.VEN":   {"name": "Ruleton Venezuela", "block": 10, "start": "09:00", "end": "21:00"},
    "TROP":    {"name": "Tropi Gana", "block": 10, "start": "08:00", "end": "19:00"},
    "COND":    {"name": "Cóndor Gana", "block": 10, "start": "08:00", "end": "19:00"},
    "FRUI":    {"name": "Fruti Gana", "block": 10, "start": "08:00", "end": "19:00"},
    "G.MIL":   {"name": "Granja Millonaria", "block": 10, "windows": [("09:00","13:00"),("16:00","20:00")]},
    "ZOOL":    {"name": "Zoológico Activo", "block": 10, "start": "08:00", "end": "19:00"},
    "L.MAX":   {"name": "Lotto Max", "block": 10, "start": "09:00", "end": "19:00"},
    "CEN.A":   {"name": "Centena Animalitos", "block": 10, "start": "08:00", "end": "20:00"},
    "L.RD":    {"name": "Lotto Rd", "block": 10, "start": "08:00", "end": "19:00"},
    "MONJE":   {"name": "Monje Millonario", "block": 10, "start": "08:05", "end": "19:05"},
    "L.ANIM":  {"name": "Lotto Animalito", "block": 10, "start": "08:00", "end": "19:00"},
    "L.PANT":  {"name": "Lotto Pantera", "block": 10, "start": "08:00", "end": "19:00"},
    "L.REAL":  {"name": "Lotto Real", "block": 10, "start": "08:00", "end": "19:00"},
    "MEGA":    {"name": "Mega Animal", "block": 10, "start": "09:00", "end": "20:00"},
    "C.ANI":   {"name": "Chance Animal", "block": 10, "start": "09:00", "end": "19:00"},

    "C.PLUS":  {"name": "Centena Plus", "block": 20, "start": "08:15", "end": "20:15"},
    "G.PLUS":  {"name": "Granjita Plus", "block": 20, "start": "08:10", "end": "19:10"},
    "RICAC":   {"name": "La Ricachona", "block": 20, "start": "08:10", "end": "19:10"},
    "CAZAL":   {"name": "Cazaloton", "block": 20, "start": "09:00", "end": "19:00"},
    "R.ACT":   {"name": "Ruleta Activa", "block": 20, "start": "09:00", "end": "19:00"},
    "L.GATO":  {"name": "Lotto Gato", "block": 20, "start": "09:00", "end": "19:00"},

    "G.ITO":   {"name": "Guacharito Millonario", "block": 50, "start": "08:30", "end": "19:30"},
    "L.INT":   {"name": "Lotto Inter", "block": 50, "start": "08:30", "end": "19:30"},
    "GUACA":   {"name": "Guaca Activa 37", "block": 50, "start": "08:30", "end": "19:30"},
    "G.AZO":   {"name": "Granjazo", "block": 50, "start": "09:30", "end": "20:30"},
    "P.PLUS":  {"name": "Panda Plus", "block": 50, "start": "09:30", "end": "19:30"},
    "GATAZO":  {"name": "Gatazo", "block": 50, "start": "09:40", "end": "19:40", "table_time": "09:30"},
    "M.GUAC":  {"name": "Mega Guaca", "block": 50, "start": "07:30", "end": "19:30"},
}

BLOCKS = {
    10: [
        ["GRAJ", "L.ACT", "SELV"],
        ["G.ARO", "CHAIMA", "MONJE"],
        ["L.ANIM", "L.PANT", "L.REAL"],
        ["L.RD", "CEN.A", "MEGA"],
        ["R.PER", "R.COL", "R.VEN"],
        ["COND", "FRUI", "TROP"],
        ["G.MIL", "ZOOL", "L.MAX"],
        ["C.ANI"],
    ],
    20: [
        ["C.PLUS", "G.PLUS", "RICAC"],
        ["CAZAL", "R.ACT", "L.GATO"],
    ],
    50: [
        ["G.ITO", "L.INT"],
        ["M.GUAC", "GUACA"],
        ["G.AZO", "P.PLUS", "GATAZO"],
    ],
}

# Fuentes alternativas adicionales conocidas de la conversación.
RESULTADOS365 = {
    "L.ACT": "https://resultados365.com/resultados/lotto-activo",
    "GRAJ": "https://resultados365.com/resultados/la-granjita/",
    "SELV": "https://resultados365.com/resultados/selvaplus/",
}

# ---------------------------------------------------------------------
# EMOJIS / FORMATO
# ---------------------------------------------------------------------

WAIT_EMOJI = "⏳"
NO_DRAW_EMOJI = "🔕"
SEPARATOR = "➖" * 8

ANIMAL_EMOJIS = {
    0: "🐬", 1: "🐏", 2: "🐂", 3: "🐛", 4: "🦂", 5: "🦁",
    6: "🐸", 7: "🦜", 8: "🐁", 9: "🦅", 10: "🐯", 11: "😺",
    12: "🐎", 13: "🐵", 14: "🕊️", 15: "🦊", 16: "🐻", 17: "🦃",
    18: "🫏", 19: "🐐", 20: "🐷", 21: "🐓", 22: "🐫", 23: "🦓",
    24: "🦎", 25: "🐔", 26: "🐮", 27: "🐶", 28: "🦇", 29: "🐘",
    30: "🐊", 31: "🐗", 32: "🐿️", 33: "🐠", 34: "🦌", 35: "🦒",
    36: "🐍",
}

# Encabezado solicitado por el usuario.
HEADER = """AGENCIA HAROLD JOSE
SEGURIDAD Y CONFIANZA
RESULTADOS OFICIALES
📲JUEGA AQUI👇👇
WHATSAPP: 04124489363

📢 CANAL DE RESULTADOS:
https://t.me/resultadosagharoldjose

RESULTADOS ANIMALITOS📰
➖➖➖➖➖➖➖➖➖➖"""

FOOTER = "MUCHA SUERTE EN SUS JUGADAS"

# ---------------------------------------------------------------------
# LOGGING / HTTP
# ---------------------------------------------------------------------

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("ag_harold_jose")

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/151 Safari/537.36"
    )
})

HTTP_TIMEOUT = int(os.getenv("HTTP_TIMEOUT", "15"))

# ---------------------------------------------------------------------
# ESTADO
# ---------------------------------------------------------------------

state_lock = threading.Lock()
sent_results = set()
table_state = {
    10: {},
    20: {},
    50: {},
}
last_scrape = {}
last_source_used = {}

# ---------------------------------------------------------------------
# UTILIDADES
# ---------------------------------------------------------------------

def now_local():
    return datetime.now(TZ)

def parse_hhmm(value):
    return datetime.strptime(value, "%H:%M").time()

def is_in_schedule(code, dt=None):
    dt = dt or now_local()
    info = LOTTERIES[code]
    current = dt.time()

    if "windows" in info:
        return any(parse_hhmm(start) <= current <= parse_hhmm(end)
                   for start, end in info["windows"])

    return parse_hhmm(info["start"]) <= current <= parse_hhmm(info["end"])

def normalize_number(raw):
    if raw is None:
        return None

    s = str(raw).strip()
    s = s.replace(",", ".")
    s = re.sub(r"[^0-9]", "", s)

    if not s:
        return None

    try:
        n = int(s)
    except ValueError:
        return None

    if n < 0 or n > 99:
        return None

    return n

def format_result(number):
    if number is None:
        return f"{WAIT_EMOJI}"

    n = int(number)
    display = f"{n:02d}" if n < 10 else str(n)
    emoji = ANIMAL_EMOJIS.get(n, "🎰")
    return f"{display}{emoji}"

def canonical_result(number):
    if number is None:
        return None
    return int(number)

def clean_text(text):
    return re.sub(r"\s+", " ", text or "").strip()

def code_sources(code):
    """
    Regla:
    - Si hay fuentes específicas, se usan esas fuentes.
    - Siempre se añade WinBig como respaldo/global cuando no hay fuente oficial.
    """
    sources = []

    if code in OFFICIAL_SOURCES:
        url = OFFICIAL_SOURCES[code]
        if url and url not in sources:
            sources.append(url)

    for url in ALTERNATIVE_SOURCES.get(code, []):
        if url and url not in sources:
            sources.append(url)

    # Fuentes específicas de Resultados365 recibidas para tres loterías.
    if code in RESULTADOS365 and RESULTADOS365[code] not in sources:
        sources.append(RESULTADOS365[code])

    if code not in OFFICIAL_SOURCES and code not in ALTERNATIVE_SOURCES:
        sources = [WINBIG_URL]

    return sources

def fetch(url):
    try:
        response = SESSION.get(url, timeout=HTTP_TIMEOUT)
        response.raise_for_status()
        return response.text
    except Exception as exc:
        logger.warning("Error leyendo %s: %s", url, exc)
        return ""

def soup_text(page):
    if not page:
        return ""
    soup = BeautifulSoup(page, "html.parser")
    return clean_text(soup.get_text(" ", strip=True))

# ---------------------------------------------------------------------
# EXTRACCIÓN DE RESULTADOS
# ---------------------------------------------------------------------

def extract_candidate_numbers(text):
    """
    Extrae números candidatos de una página.
    Se conserva como parser genérico para no depender de un único HTML.
    """
    candidates = []

    patterns = [
        r"\b([0-3]?\d)\b",
        r"\b(4\d|5\d|6\d)\b",
    ]

    for pattern in patterns:
        for match in re.findall(pattern, text):
            n = normalize_number(match)
            if n is not None:
                candidates.append(n)

    return candidates

def parse_winbig(code, page):
    """
    Parser genérico de WinBig.
    Busca el nombre de la lotería cerca de números 0-99.
    Si el HTML cambia, esta función es el punto principal a ajustar.
    """
    if not page:
        return None

    soup = BeautifulSoup(page, "html.parser")
    full_text = soup.get_text(" ", strip=True)

    aliases = {
        "L.ACT": ["Lotto Activo", "LottoActivo", "L.ACT"],
        "GRAJ": ["La Granjita", "Granjita", "GRAJ"],
        "SELV": ["Selva Plus", "SelvaPlus", "SELV"],
        "G.ARO": ["Guácharo Activo", "Guacharo Activo", "G.ARO"],
        "CHAIMA": ["Loto Chaima", "CHAIMA"],
        "MONJE": ["Monje Millonario", "MONJE"],
        "L.RD": ["Lotto Rd", "Lotto RD", "Internacional"],
        "GUACA": ["Guaca Activa 37", "Guaca Activa", "GUACA"],
        "M.GUAC": ["Mega Guaca", "MEGA GUACA"],
        "G.ITO": ["Guacharito Millonario", "Guacharito", "G.ITO"],
        "L.INT": ["Lotto Inter", "Lotto Inter.", "L.INT"],
        "G.AZO": ["Granjazo", "G.AZO"],
        "P.PLUS": ["Panda Plus", "P.PLUS"],
        "GATAZO": ["Gatazo", "GATAZO"],
    }

    target_aliases = aliases.get(code, [code])
    lower = full_text.lower()

    for alias in target_aliases:
        idx = lower.find(alias.lower())
        if idx < 0:
            continue

        segment = full_text[max(0, idx - 80): idx + 300]
        numbers = extract_candidate_numbers(segment)

        # Evitar tomar horarios como resultado cuando sea posible.
        filtered = [n for n in numbers if n <= 36]
        if filtered:
            return filtered[0]

    # Fallback: buscar estructuras HTML cercanas a textos.
    for tag in soup.find_all(["div", "td", "span", "article", "li"]):
        txt = clean_text(tag.get_text(" ", strip=True))
        if any(alias.lower() in txt.lower() for alias in target_aliases):
            numbers = [n for n in extract_candidate_numbers(txt) if n <= 36]
            if numbers:
                return numbers[0]

    return None

def parse_official_generic(code, page):
    """
    Parser genérico para páginas oficiales.
    Se usa como segunda capa. La fuente oficial tiene prioridad en
    conflictos para las loterías con fuente propia.
    """
    if not page:
        return None

    text = soup_text(page)
    if not text:
        return None

    aliases = [
        LOTTERIES[code]["name"],
        code,
        LOTTERIES[code]["name"].replace(" ", ""),
    ]

    lower = text.lower()

    for alias in aliases:
        idx = lower.find(alias.lower())
        if idx >= 0:
            segment = text[max(0, idx - 100): idx + 500]
            nums = [n for n in extract_candidate_numbers(segment) if n <= 36]
            if nums:
                return nums[0]

    return None

def parse_ruleta_activa_official(page):
    """
    Ruleta Activa:
    - La página oficial muestra A/B/C/D.
    - El resultado que interesa es D, el último animalito.
    """
    if not page:
        return None

    soup = BeautifulSoup(page, "html.parser")

    # Buscar texto explícito D / letra D.
    text = soup.get_text(" ", strip=True)
    patterns = [
        r"\bD\b\s*[:\-]?\s*(\d{1,2})",
        r"\bD\s*=\s*(\d{1,2})",
        r"\bD\)\s*(\d{1,2})",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            n = normalize_number(match.group(1))
            if n is not None and n <= 36:
                return n

    # Fallback: encontrar un bloque que contenga A/B/C/D y tomar el último número.
    if re.search(r"\bA\b", text) and re.search(r"\bB\b", text) and re.search(r"\bC\b", text) and re.search(r"\bD\b", text):
        nums = [n for n in extract_candidate_numbers(text) if n <= 36]
        if nums:
            return nums[-1]

    return None

def parse_ruleta_activa_alternative(page):
    if not page:
        return None

    text = soup_text(page)

    # La alternativa debe representar el resultado equivalente a D.
    nums = [n for n in extract_candidate_numbers(text) if n <= 36]
    return nums[0] if nums else None

def get_result_from_sources(code):
    """
    Retorna:
      (resultado, estado, fuente)
    estado:
      - confirmed
      - waiting
      - unavailable

    Reglas:
    1) Sin fuentes específicas -> WinBig.
    2) Con fuente oficial + alternativa -> comparar.
    3) Si hay discrepancia, esperar.
    4) En el siguiente ciclo, si continúa la discrepancia, priorizar oficial.
    5) Ruleta Activa: D oficial manda; alternativa solo confirma.
    """
    urls = code_sources(code)

    if code == "R.ACT":
        official_url = OFFICIAL_SOURCES["R.ACT"]
        alternative_url = ALTERNATIVE_SOURCES["R.ACT"][0]

        official_page = fetch(official_url)
        official_result = parse_ruleta_activa_official(official_page)

        alt_page = fetch(alternative_url)
        alt_result = parse_ruleta_activa_alternative(alt_page)

        if official_result is not None and alt_result is not None:
            if official_result == alt_result:
                last_source_used[code] = "official+alternative"
                return official_result, "confirmed", "official+alternative"

            # Si no coinciden, no se publica como confirmado.
            last_source_used[code] = "conflict"
            return None, "waiting", "conflict"

        if official_result is not None:
            last_source_used[code] = "official"
            return official_result, "confirmed", "official"

        last_source_used[code] = "waiting-official"
        return None, "waiting", "waiting-official"

    specific_official = OFFICIAL_SOURCES.get(code)

    if specific_official and specific_official != WINBIG_URL:
        official_page = fetch(specific_official)
        official_result = parse_official_generic(code, official_page)

        alternative_results = []
        for url in ALTERNATIVE_SOURCES.get(code, []) + (
            [RESULTADOS365[code]] if code in RESULTADOS365 else []
        ):
            page = fetch(url)
            result = parse_official_generic(code, page)
            if result is not None:
                alternative_results.append((result, url))

        winbig_result = None
        if not alternative_results or official_result is None:
            wb_page = fetch(WINBIG_URL)
            winbig_result = parse_winbig(code, wb_page)

        # Fuente oficial y alternativa coinciden.
        if official_result is not None and alternative_results:
            matches = [r for r, _ in alternative_results if r == official_result]
            if matches:
                last_source_used[code] = "official+alternative"
                return official_result, "confirmed", "official+alternative"

            # Si no coinciden, espera; no inventar ni elegir arbitrariamente.
            last_source_used[code] = "conflict"
            return None, "waiting", "conflict"

        # Si la oficial no tiene resultado, la alternativa no puede confirmar sola.
        if official_result is None and alternative_results:
            last_source_used[code] = "waiting-official"
            return None, "waiting", "waiting-official"

        # Si oficial y WinBig están disponibles y coinciden.
        if official_result is not None and winbig_result is not None:
            if official_result == winbig_result:
                last_source_used[code] = "official+winbig"
                return official_result, "confirmed", "official+winbig"
            last_source_used[code] = "conflict"
            return None, "waiting", "conflict"

        if official_result is not None:
            last_source_used[code] = "official"
            return official_result, "confirmed", "official"

        if winbig_result is not None:
            # Solo se usa como respaldo temporal si la fuente oficial no responde.
            last_source_used[code] = "winbig"
            return winbig_result, "confirmed", "winbig"

        return None, "waiting", "no-result"

    # Sin fuente específica: WinBig es la única fuente.
    page = fetch(WINBIG_URL)
    result = parse_winbig(code, page)

    if result is None:
        last_source_used[code] = "winbig-no-result"
        return None, "waiting", "winbig"

    last_source_used[code] = "winbig"
    return result, "confirmed", "winbig"

# ---------------------------------------------------------------------
# TABLAS
# ---------------------------------------------------------------------

def table_display_time(code, actual_dt):
    info = LOTTERIES[code]
    if info.get("table_time"):
        return info["table_time"]

    return actual_dt.strftime("%H:%M")

def get_expected_draws_for_code(code, day=None):
    day = day or now_local().date()
    info = LOTTERIES[code]

    times = []

    if "windows" in info:
        windows = info["windows"]
    else:
        windows = [(info["start"], info["end"])]

    for start, end in windows:
        current = datetime.combine(day, parse_hhmm(start), TZ)
        finish = datetime.combine(day, parse_hhmm(end), TZ)

        while current <= finish:
            times.append(current)
            current += timedelta(hours=1)

    # Gatazo: tabla usa 09:30, pero el sorteo real es 09:40.
    if code == "GATAZO":
        adjusted = []
        for dt in times:
            if dt.strftime("%H:%M") == "09:40":
                adjusted.append(dt.replace(minute=30))
            else:
                adjusted.append(dt)
        times = adjusted

    return times

def latest_due_draw(code, now=None):
    now = now or now_local()
    draws = get_expected_draws_for_code(code, now.date())
    due = [d for d in draws if d <= now]
    return due[-1] if due else None

def should_show_code_at(code, now=None):
    now = now or now_local()
    return latest_due_draw(code, now) is not None

def update_one_code(code):
    result, status, source = get_result_from_sources(code)

    if status == "confirmed" and result is not None:
        with state_lock:
            table_state[LOTTERIES[code]["block"]][code] = {
                "result": result,
                "status": "confirmed",
                "source": source,
                "updated_at": now_local().isoformat(),
            }
        return result, "confirmed"

    with state_lock:
        table_state[LOTTERIES[code]["block"]][code] = {
            "result": None,
            "status": "waiting",
            "source": source,
            "updated_at": now_local().isoformat(),
        }

    return None, "waiting"

def update_all_tables():
    now = now_local()

    for code in LOTTERIES:
        if should_show_code_at(code, now):
            try:
                update_one_code(code)
            except Exception:
                logger.exception("Error actualizando %s", code)

def format_cell(code, row_time):
    state = table_state[LOTTERIES[code]["block"]].get(code)

    if not state:
        return WAIT_EMOJI

    if state["status"] != "confirmed" or state["result"] is None:
        return WAIT_EMOJI

    return format_result(state["result"])

def render_table_group(group, block, now=None):
    now = now or now_local()

    # La tabla solo muestra horas ya alcanzadas.
    available = {}
    for code in group:
        draws = get_expected_draws_for_code(code, now.date())
        due = [d for d in draws if d <= now]
        for dt in due:
            key = table_display_time(code, dt)
            available[key] = True

    if not available:
        return ""

    # Orden cronológico por hora.
    def sort_key(x):
        try:
            return datetime.strptime(x, "%H:%M")
        except ValueError:
            return datetime.strptime("00:00", "%H:%M")

    times = sorted(available.keys(), key=sort_key)

    # Alineación monoespaciada para mantener una sola fila visual.
    labels = [code for code in group]
    header = "HORA🎰" + "".join(f"{c:<9}" for c in labels)

    lines = [header]

    for time_label in times:
        row = f"⏰{time_label:<5}"
        for code in labels:
            row += f"{format_cell(code, time_label):<9}"
        lines.append(row)

    return "\n".join(lines)

def render_block(block, now=None):
    now = now or now_local()
    parts = []

    for group in BLOCKS[block]:
        text = render_table_group(group, block, now)
        if text:
            parts.append(text)

    return "\n\n".join(parts)

def render_full_table(block, now=None):
    now = now or now_local()
    body = render_block(block, now)

    if not body:
        return ""

    return f"{HEADER}\n{body}\n\n{FOOTER}"

# ---------------------------------------------------------------------
# PIRÁMIDE
# ---------------------------------------------------------------------

def digit_sum(a, b):
    return (a + b) % 10

def build_pyramid(seed_numbers):
    """
    Construye la pirámide sumando dígitos adyacentes.
    Ejemplo:
    0 3 0 8 2 0 2 6
     3 3 8 0 2 2 8
      6 1 8 2 4 0
       7 9 0 6 4
        6 9 6 0
         5 5 6
          0 1
           1
    """
    digits = []
    for n in seed_numbers:
        n = int(n)
        digits.extend([n // 10, n % 10])

    rows = [digits]

    while len(rows[-1]) > 1:
        prev = rows[-1]
        new_row = [digit_sum(prev[i], prev[i + 1]) for i in range(len(prev) - 1)]
        rows.append(new_row)

    return rows

def format_pyramid(rows):
    lines = []
    for i, row in enumerate(rows):
        indent = "." * (i * 2 + 1)
        values = "  ".join(str(x) for x in row)
        lines.append(f"{indent} {values}")
    return "\n".join(lines)

def valid_pyramid_value(n):
    # 0 y 00 son conceptualmente distintos.
    # Para el cálculo interno, 0 se conserva como 0.
    return 0 <= n <= 36

def normalize_pyramid_value(n):
    """
    Convierte cualquier cálculo en un valor válido 0..36.
    No convierte 0 en 00: la representación 00 queda reservada
    para un resultado explícitamente doble cero.
    """
    n = abs(int(n))

    while n > 36:
        digits = [int(d) for d in str(n)]
        if len(digits) >= 2:
            n = sum(digits)
        else:
            n = n % 37

    return n

def calculate_key_values(rows):
    """
    Genera seis datos clave de forma determinista a partir de la pirámide.

    Se usan posiciones y frecuencias de las filas para evitar que el bot
    simplemente repita una lista fija. Todos los resultados quedan en 0..36.

    Nota: la fórmula puede sustituirse posteriormente por la fórmula exacta
    que el usuario defina si decide conservar la lógica del bot anterior.
    """
    flat = [n for row in rows for n in row]

    if not flat:
        return []

    frequency = {}
    for n in flat:
        frequency[n] = frequency.get(n, 0) + 1

    most_common = sorted(
        frequency.items(),
        key=lambda x: (-x[1], x[0])
    )

    candidates = []

    # 1. Valores más repetidos.
    for n, _ in most_common:
        candidates.append(n)

    # 2. Sumas de filas.
    for row in rows:
        if row:
            candidates.append(sum(row))

    # 3. Combinaciones entre primera y última posición de cada fila.
    for row in rows:
        if row:
            candidates.append(row[0] + row[-1])
            candidates.append(row[0] * row[-1])

    # 4. Diferencias.
    for row in rows:
        if len(row) >= 2:
            candidates.append(abs(row[0] - row[-1]))

    valid = []
    seen = set()

    for value in candidates:
        value = normalize_pyramid_value(value)
        if value not in seen:
            valid.append(value)
            seen.add(value)
        if len(valid) >= 6:
            break

    # Completar hasta seis sin repetir, usando datos de la pirámide.
    for n in flat:
        value = normalize_pyramid_value(n)
        if value not in seen:
            valid.append(value)
            seen.add(value)
        if len(valid) >= 6:
            break

    return valid[:6]

def generate_daily_pyramid(date=None):
    date = date or now_local().date()

    # Semilla diaria determinista basada en la fecha.
    seed = [
        date.day % 100,
        date.month % 100,
        (date.day + date.month) % 100,
        (date.day * date.month) % 100,
    ]

    rows = build_pyramid(seed)
    keys = calculate_key_values(rows)

    return rows, keys

def pyramid_message():
    rows, keys = generate_daily_pyramid()

    key_lines = []
    for i in range(0, len(keys), 3):
        chunk = keys[i:i + 3]
        formatted = []
        for n in chunk:
            # Si la fórmula produce 0, se muestra 0.
            # 00 solo se reserva para un dato que explícitamente sea 00.
            formatted.append(str(n))
        key_lines.append("📌 " + "-".join(formatted))

    return (
        "🔢 PIRÁMIDE NUMÉRICA DEL DÍA\n"
        f"{format_pyramid(rows)}\n\n"
        "🔥 DATOS CLAVES PARA HOY:\n"
        + "\n".join(key_lines)
    )

# ---------------------------------------------------------------------
# MENSAJES PROGRAMADOS
# ---------------------------------------------------------------------

def send_message(text, chat_id=None):
    if not bot:
        logger.warning("Bot no inicializado.")
        return False

    chat_id = chat_id or ACTIVE_CHANNEL_ID

    try:
        bot.send_message(chat_id, text, disable_web_page_preview=True)
        logger.info("Mensaje enviado a %s", chat_id)
        return True
    except Exception as exc:
        logger.error("No se pudo enviar mensaje: %s", exc)
        return False

def send_result_individual(code, result, draw_dt, chat_id=None):
    if result is None:
        return False

    info = LOTTERIES[code]
    text = (
        f"🎰 {info['name'].upper()}\n"
        f"⏰ {draw_dt.strftime('%H:%M')}\n"
        f"🎯 RESULTADO: {format_result(result)}"
    )
    return send_message(text, chat_id)

def send_table(block, chat_id=None):
    text = render_full_table(block)
    if not text:
        return False

    return send_message(text, chat_id)

def scheduled_message_710():
    send_message(
        "📢 AVISO DE POLLAS\n"
        "🕒 Comenzamos la jornada de resultados y recepción de jugadas.\n"
        "🍀 Mucha suerte en sus jugadas."
    )

def scheduled_good_morning():
    send_message(
        "🌅 BUENOS DÍAS\n"
        "AGENCIA HAROLD JOSE\n"
        "SEGURIDAD Y CONFIANZA\n\n"
        "🍀 Les deseamos mucha suerte en sus jugadas."
    )

def scheduled_pyramid():
    send_message(pyramid_message())

def scheduled_bcv():
    # Punto de integración preparado. Se deja separado para poder añadir
    # el parser del BCV sin afectar el sistema de resultados.
    send_message("💵 TASA DEL DÍA\n🔄 Verificación de tasa pendiente de configuración.")

def scheduled_table_10():
    update_all_tables()
    send_table(10)

def scheduled_table_20():
    update_all_tables()
    send_table(20)

def scheduled_table_50():
    update_all_tables()
    send_table(50)

# ---------------------------------------------------------------------
# LOOP DEL BOT
# ---------------------------------------------------------------------

last_minute_run = None

def scheduler_loop():
    global last_minute_run

    while True:
        try:
            now = now_local()
            minute_key = now.strftime("%Y-%m-%d %H:%M")

            # Cada minuto actualizamos el estado interno de resultados.
            update_all_tables()

            # 07:10 en adelante: aviso de pollas cada hora.
            if now.minute == 10 and 7 <= now.hour <= 18:
                if last_minute_run != minute_key:
                    scheduled_table_10()
                    last_minute_run = minute_key

            # Tabla minuto 20.
            if now.minute == 20:
                scheduled_table_20()

            # Tabla minuto 50.
            if now.minute == 50:
                scheduled_table_50()

            # Mensajes diarios.
            if now.hour == 7 and now.minute == 0:
                scheduled_good_morning()

            if now.hour == 7 and now.minute == 5:
                scheduled_pyramid()

            time.sleep(45)

        except Exception:
            logger.exception("Error en scheduler_loop")
            time.sleep(30)

# ---------------------------------------------------------------------
# FLASK / ENDPOINTS DE PRUEBA
# ---------------------------------------------------------------------

app = Flask(__name__)

@app.get("/")
def home():
    return jsonify({
        "status": "ok",
        "bot": "AGENCIA HAROLD JOSE",
        "time": now_local().isoformat(),
        "channel": ACTIVE_CHANNEL_ID,
    })

@app.get("/health")
def health():
    return jsonify({
        "status": "healthy",
        "time": now_local().isoformat(),
    })

@app.get("/test/piramide")
def test_piramide():
    return jsonify({
        "message": pyramid_message(),
    })

@app.get("/test/table/<int:block>")
def test_table(block):
    if block not in BLOCKS:
        return jsonify({"error": "Bloque inválido. Usa 10, 20 o 50."}), 400

    update_all_tables()
    return jsonify({
        "block": block,
        "table": render_full_table(block),
    })

@app.get("/test/source/<code>")
def test_source(code):
    code = code.upper()

    if code not in LOTTERIES:
        return jsonify({"error": f"Lotería desconocida: {code}"}), 404

    result, status, source = get_result_from_sources(code)

    return jsonify({
        "code": code,
        "name": LOTTERIES[code]["name"],
        "result": result,
        "status": status,
        "source_used": source,
        "sources_configured": code_sources(code),
    })

@app.get("/test/all-sources")
def test_all_sources():
    output = {}

    for code in LOTTERIES:
        try:
            result, status, source = get_result_from_sources(code)
            output[code] = {
                "name": LOTTERIES[code]["name"],
                "result": result,
                "status": status,
                "source_used": source,
                "sources": code_sources(code),
            }
        except Exception as exc:
            output[code] = {
                "error": str(exc),
            }

    return jsonify(output)

@app.get("/test/send/table/<int:block>")
def test_send_table(block):
    if block not in BLOCKS:
        return jsonify({"error": "Bloque inválido"}), 400

    update_all_tables()
    ok = send_table(block)

    return jsonify({
        "sent": ok,
        "block": block,
        "channel": ACTIVE_CHANNEL_ID,
    })

@app.get("/test/send/piramide")
def test_send_piramide():
    ok = send_message(pyramid_message())
    return jsonify({"sent": ok, "channel": ACTIVE_CHANNEL_ID})

# ---------------------------------------------------------------------
# TELEGRAM
# ---------------------------------------------------------------------

if telebot and BOT_TOKEN:
    bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

    @bot.message_handler(commands=["start", "id"])
    def command_start(message):
        bot.reply_to(
            message,
            f"Bot activo.\nChat ID: <code>{message.chat.id}</code>"
        )

    @bot.message_handler(commands=["test10"])
    def command_test10(message):
        update_all_tables()
        bot.send_message(message.chat.id, render_full_table(10) or "Sin datos.")

    @bot.message_handler(commands=["test20"])
    def command_test20(message):
        update_all_tables()
        bot.send_message(message.chat.id, render_full_table(20) or "Sin datos.")

    @bot.message_handler(commands=["test50"])
    def command_test50(message):
        update_all_tables()
        bot.send_message(message.chat.id, render_full_table(50) or "Sin datos.")

    @bot.message_handler(commands=["piramide"])
    def command_piramide(message):
        bot.send_message(message.chat.id, pyramid_message())

else:
    bot = None
    logger.warning(
        "BOT_TOKEN no configurado. Flask seguirá funcionando, "
        "pero Telegram no enviará mensajes."
    )

# ---------------------------------------------------------------------
# ARRANQUE
# ---------------------------------------------------------------------

def start_background_scheduler():
    thread = threading.Thread(
        target=scheduler_loop,
        name="scheduler",
        daemon=True,
    )
    thread.start()

if __name__ == "__main__":
    if not BOT_TOKEN:
        logger.warning(
            "BOT_TOKEN está vacío. Configúralo como variable de entorno en Render."
        )

    start_background_scheduler()

    port = int(os.getenv("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)
