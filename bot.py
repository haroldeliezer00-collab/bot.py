import os
import re
import json
import time
import logging
import threading
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from flask import Flask, jsonify
import telebot
from telebot import types

# ============================================================
# AG HAROLD JOSE BOT - VERSION COMPLETA
# ============================================================
# IMPORTANTE:
# - El token NO está aquí. Se configura en Render como BOT_TOKEN.
# - Durante las pruebas el destino activo es @pruebajsj.
# - El canal principal solo aparece como referencia/firma.
# ============================================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
TEST_CHANNEL_ID = os.getenv("TEST_CHANNEL_ID", "@pruebajsj").strip()
ACTIVE_CHANNEL_ID = os.getenv("ACTIVE_CHANNEL_ID", TEST_CHANNEL_ID).strip()
MAIN_CHANNEL_REFERENCE = os.getenv("MAIN_CHANNEL_REFERENCE", "@AGHAROLDJOSE_BOT").strip()
TIMEZONE = os.getenv("TIMEZONE", "America/Caracas").strip()
PORT = int(os.getenv("PORT", "10000"))

if not BOT_TOKEN:
    raise RuntimeError("Falta la variable de entorno BOT_TOKEN en Render.")

TZ = ZoneInfo(TIMEZONE)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
log = logging.getLogger("ag_harold_jose_bot")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
app = Flask(__name__)

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/151.0 Safari/537.36"
})

STATE_FILE = "bot_state.json"
state_lock = threading.Lock()

BANNER = """<b>AGENCIA HAROLD JOSE</b>
<b>SEGURIDAD Y CONFIANZA</b>
<b>RESULTADOS OFICIALES</b>
📲JUEGA AQUI👇👇
WHATSAPP: 04124489363

📢 CANAL DE RESULTADOS:
https://t.me/resultadosagharoldjose"""

# Símbolos:
# ⏳ = sorteo esperado pero aún no confirmado
# 🔕 = ese horario no tiene sorteo para esa lotería
PENDING = "⏳"
NO_DRAW = "🔕"

ANIMAL_EMOJI = {
    0: "🐬", 1: "🐏", 2: "🐂", 3: "🐛", 4: "🦂", 5: "🦁",
    6: "🐸", 7: "🦜", 8: "🐁", 9: "🦅", 10: "🐯", 11: "😺",
    12: "🐎", 13: "🐵", 14: "🕊️", 15: "🦊", 16: "🐻", 17: "🦃",
    18: "🫏", 19: "🐐", 20: "🐷", 21: "🐓", 22: "🐫", 23: "🦓",
    24: "🦎", 25: "🐔", 26: "🐮", 27: "🐶", 28: "🦇", 29: "🐘",
    30: "🐊", 31: "🐗", 32: "🐿️", 33: "🐠", 34: "🦌", 35: "🦒",
    36: "🐍",
}

# Fuente global. Si una lotería no tiene fuente específica, se consulta aquí.
WINBIG_URL = "https://lotery.winbigvzla.com/resultados"

# Fuentes oficiales entregadas por el usuario.
OFFICIAL = {
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
    "P.PLUS": "https://www.guacaactiva.com/",
}

# Alternativas entregadas por el usuario.
ALTERNATIVE = {
    "L.ACT": ["https://resultados365.com/resultados/lotto-activo"],
    "GRAJ": ["https://resultados365.com/resultados/la-granjita/"],
    "SELV": ["https://resultados365.com/resultados/selvaplus/"],
    "R.ACT": ["https://loteriadehoy.com/animalito/ruletaactiva/resultados/"],
}

# La fuente global se usa para todo lo que no tenga fuentes específicas.
# Las tres fuentes principales (oficial + alternativa + Winbig) se consultan
# cuando corresponde.
LOTTERIES = {
    "L.ACT": {"name": "Lotto Activo", "start": "08:00", "end": "19:00", "block": 10},
    "GRAJ": {"name": "La Granjita", "start": "08:00", "end": "19:00", "block": 10},
    "SELV": {"name": "Selva Plus", "start": "08:00", "end": "19:00", "block": 10},
    "G.ARO": {"name": "Guácharo Activo", "start": "08:00", "end": "19:00", "block": 10},
    "CHAIMA": {"name": "Loto Chaima", "start": "08:00", "end": "19:00", "block": 10},
    "R.PER": {"name": "Ruleton Perú", "start": "08:00", "end": "20:00", "block": 10},
    "R.COL": {"name": "Ruleton Colombia", "start": "08:00", "end": "20:00", "block": 10},
    "R.VEN": {"name": "Ruleton Venezuela", "start": "09:00", "end": "21:00", "block": 10},
    "TROP": {"name": "Tropi Gana", "start": "08:00", "end": "19:00", "block": 10},
    "COND": {"name": "Cóndor Gana", "start": "08:00", "end": "19:00", "block": 10},
    "FRUI": {"name": "Fruti Gana", "start": "08:00", "end": "19:00", "block": 10},
    "G.MIL": {"name": "Granja Millonaria", "windows": [("09:00", "13:00"), ("16:00", "20:00")], "block": 10},
    "ZOOL": {"name": "Zoológico Activo", "start": "08:00", "end": "19:00", "block": 10},
    "L.MAX": {"name": "Lotto Max", "start": "09:00", "end": "19:00", "block": 10},
    "CEN.A": {"name": "Centena Animalitos", "start": "08:00", "end": "20:00", "block": 10},
    "L.RD": {"name": "Lotto Rd", "start": "08:00", "end": "19:00", "block": 10},
    "MONJE": {"name": "Monje Millonario", "start": "08:05", "end": "19:05", "block": 10},
    "L.ANIM": {"name": "Lotto Animalito", "start": "08:00", "end": "19:00", "block": 10},
    "L.PANT": {"name": "Lotto Pantera", "start": "08:00", "end": "19:00", "block": 10},
    "L.REAL": {"name": "Lotto Real", "start": "08:00", "end": "19:00", "block": 10},
    "MEGA": {"name": "Mega Animal", "start": "09:00", "end": "20:00", "block": 10},
    "C.ANI": {"name": "Chance Animal", "start": "09:00", "end": "19:00", "block": 10},

    "C.PLUS": {"name": "Centena Plus", "start": "08:15", "end": "20:15", "block": 20, "table_minute": 15},
    "G.PLUS": {"name": "Granjita Plus", "start": "08:10", "end": "19:10", "block": 20, "table_minute": 15},
    "RICAC": {"name": "La Ricachona", "start": "08:10", "end": "19:10", "block": 20, "table_minute": 15},
    "CAZAL": {"name": "Cazaloton", "start": "09:00", "end": "19:00", "block": 20},
    "R.ACT": {"name": "Ruleta Activa", "start": "09:00", "end": "19:00", "block": 20},
    "L.GATO": {"name": "Lotto Gato", "start": "09:00", "end": "19:00", "block": 20},

    "G.ITO": {"name": "Guacharito Millonario", "start": "08:30", "end": "19:30", "block": 50},
    "L.INT": {"name": "Lotto Inter", "start": "08:30", "end": "19:30", "block": 50},
    "GUACA": {"name": "Guaca Activa 37", "start": "08:30", "end": "19:30", "block": 50},
    "G.AZO": {"name": "Granjazo", "start": "09:30", "end": "20:30", "block": 50},
    "P.PLUS": {"name": "Panda Plus", "start": "09:30", "end": "19:30", "block": 50},
    "GATAZO": {"name": "Gatazo", "start": "09:40", "end": "19:40", "block": 50, "display_start": "09:30"},
    "M.GUAC": {"name": "Mega Guaca", "start": "07:30", "end": "19:30", "block": 50},
}

# Orden exacto de las tablas.
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

HEADERS = {
    10: "📰RESULTADOS ANIMALITOS📰",
    20: "📰RESULTADOS ANIMALITOS📰",
    50: "📰RESULTADOS ANIMALITOS📰",
}

# Estado en memoria/persistencia.
state = {
    "sent_results": {},
    "tables": {},
    "last_pyramid_date": "",
    "last_scheduled": {},
    "last_individual": {},
}

def load_state():
    global state
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        if isinstance(loaded, dict):
            state.update(loaded)
    except FileNotFoundError:
        pass
    except Exception as exc:
        log.warning("No se pudo cargar estado: %s", exc)

def save_state():
    tmp = STATE_FILE + ".tmp"
    with state_lock:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        os.replace(tmp, STATE_FILE)

load_state()

def now():
    return datetime.now(TZ)

def norm_text(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()

def normalize_name(value):
    value = norm_text(value).upper()
    value = re.sub(r"[^A-Z0-9ÁÉÍÓÚÜÑ ]", " ", value)
    return re.sub(r"\s+", " ", value).strip()

ALIASES = {
    "LOTTO ACTIVO": "L.ACT",
    "LOTO ACTIVO": "L.ACT",
    "LA GRANJITA": "GRAJ",
    "GRANJITA": "GRAJ",
    "SELVA PLUS": "SELV",
    "GUACHARO ACTIVO": "G.ARO",
    "GUÁCHARO ACTIVO": "G.ARO",
    "LOTO CHAIMA": "CHAIMA",
    "CHAIMA": "CHAIMA",
    "RULETON PERU": "R.PER",
    "RULETON PERÚ": "R.PER",
    "RULETON COLOMBIA": "R.COL",
    "RULETON VENEZUELA": "R.VEN",
    "TROPI GANA": "TROP",
    "CONDOR GANA": "COND",
    "CÓNDOR GANA": "COND",
    "FRUTI GANA": "FRUI",
    "GRANJA MILLONARIA": "G.MIL",
    "ZOOLOGICO ACTIVO": "ZOOL",
    "ZOOLÓGICO ACTIVO": "ZOOL",
    "LOTTO MAX": "L.MAX",
    "CENTENA ANIMALITOS": "CEN.A",
    "LOTTO RD": "L.RD",
    "LOTTO RD INTERNACIONAL": "L.RD",
    "MONJE MILLONARIO": "MONJE",
    "LOTTO ANIMALITO": "L.ANIM",
    "LOTTO PANTERA": "L.PANT",
    "LOTTO REAL": "L.REAL",
    "MEGA ANIMAL": "MEGA",
    "CHANCE ANIMAL": "C.ANI",
    "CHANCE ANIMALITOS": "C.ANI",
    "CENTENA PLUS": "C.PLUS",
    "GRANJITA PLUS": "G.PLUS",
    "LA RICACHONA": "RICAC",
    "CAZALOTON": "CAZAL",
    "RULETA ACTIVA": "R.ACT",
    "LOTTO GATO": "L.GATO",
    "GUACHARITO MILLONARIO": "G.ITO",
    "LOTTO INTER": "L.INT",
    "GUACA ACTIVA 37": "GUACA",
    "TRIPLE GUACA37": "GUACA",
    "GRANJAZO": "G.AZO",
    "PANDA PLUS": "P.PLUS",
    "GATAZO": "GATAZO",
    "MEGA GUACA": "M.GUAC",
}

def canonical_lottery(name):
    return ALIASES.get(normalize_name(name))

def parse_number(raw):
    if raw is None:
        return None
    s = str(raw).strip().upper()
    if s in {"", "-", "...", "....", "FALSE", "NONE", "NULL"}:
        return None
    m = re.search(r"(?<!\d)(\d{1,2})(?!\d)", s)
    if not m:
        return None
    n = int(m.group(1))
    if 0 <= n <= 99:
        return n
    return None

def format_result(n):
    if n is None:
        return PENDING
    if n == 0:
        return "00" if False else "0"
    if n == 0:
        return "00"
    return f"{n:02d}"

def result_display(n):
    if n is None:
        return PENDING
    return f"{n:02d}{ANIMAL_EMOJI.get(n, '🎰')}"

def parse_time_from_text(text):
    text = text.replace(".", ":")
    patterns = [
        r"\b([01]?\d):([0-5]\d)\s*(AM|PM)?\b",
        r"\b([01]?\d)\s*(AM|PM)\b",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.I)
        if not m:
            continue
        hour = int(m.group(1))
        minute = int(m.group(2)) if len(m.groups()) >= 2 and m.group(2).isdigit() else 0
        ampm = m.group(3) if len(m.groups()) >= 3 else (m.group(2) if m.group(2).isalpha() else None)
        if ampm:
            ampm = ampm.upper()
            if ampm == "PM" and hour < 12:
                hour += 12
            if ampm == "AM" and hour == 12:
                hour = 0
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return hour, minute
    return None

def extract_candidates(text):
    """Extrae pares hora/resultado de texto y HTML visible."""
    text = norm_text(text)
    candidates = []
    # 08:00 ... 14
    for m in re.finditer(r"\b(\d{1,2}):(\d{2})\b.{0,80}?\b(\d{1,2})\b", text):
        hh, mm, num = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if 0 <= hh <= 23 and mm <= 59 and 0 <= num <= 99:
            candidates.append((hh, mm, num))
    # 08:00 14 / 09:00 36
    for m in re.finditer(r"\b(\d{1,2}):(\d{2})\s+(\d{1,2})\b", text):
        hh, mm, num = int(m.group(1)), int(m.group(2)), int(m.group(3))
        candidates.append((hh, mm, num))
    # 08:00 -> 14
    for m in re.finditer(r"\b(\d{1,2}):(\d{2})\s*(?:-|:|→|>)\s*(\d{1,2})\b", text):
        candidates.append((int(m.group(1)), int(m.group(2)), int(m.group(3))))
    # dedupe
    seen = set()
    out = []
    for item in candidates:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out

def fetch(url, timeout=15):
    r = SESSION.get(url, timeout=timeout, allow_redirects=True)
    r.raise_for_status()
    return r.text

def extract_source_results(url, lottery_code=None):
    """
    Parser tolerante: intenta localizar resultados en tablas/cards.
    Se mantiene genérico porque las webs pueden cambiar.
    Devuelve {HH:MM: number}.
    """
    try:
        html = fetch(url)
    except Exception as exc:
        log.warning("Fuente falló %s: %s", url, exc)
        return {}

    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)
    results = {}

    # 1) Tablas HTML.
    for tr in soup.find_all("tr"):
        cells = [norm_text(c.get_text(" ", strip=True)) for c in tr.find_all(["td", "th"])]
        if len(cells) < 2:
            continue
        row = " ".join(cells)
        found = extract_candidates(row)
        for hh, mm, num in found:
            results[f"{hh:02d}:{mm:02d}"] = num

    # 2) Cards/elementos visibles.
    for el in soup.find_all(["article", "div", "li", "section"]):
        txt = norm_text(el.get_text(" ", strip=True))
        if len(txt) > 300:
            continue
        found = extract_candidates(txt)
        for hh, mm, num in found:
            results[f"{hh:02d}:{mm:02d}"] = num

    # 3) Texto completo como último recurso.
    for hh, mm, num in extract_candidates(text):
        results[f"{hh:02d}:{mm:02d}"] = num

    # Heurística para Ruleta Activa: buscar A/B/C/D y usar D.
    if lottery_code == "R.ACT":
        d_results = {}
        for tag in soup.find_all(["div", "li", "tr", "td", "article"]):
            txt = norm_text(tag.get_text(" ", strip=True))
            if re.search(r"\bD\b", txt, re.I):
                nums = re.findall(r"(?<!\d)(\d{1,2})(?!\d)", txt)
                if nums:
                    n = int(nums[-1])
                    if 0 <= n <= 99:
                        tm = parse_time_from_text(txt)
                        if tm:
                            d_results[f"{tm[0]:02d}:{tm[1]:02d}"] = n
        if d_results:
            results.update(d_results)

    return results

def source_urls(code):
    urls = []
    if code in OFFICIAL:
        urls.append(("official", OFFICIAL[code]))
    for u in ALTERNATIVE.get(code, []):
        urls.append(("alternative", u))
    if code not in OFFICIAL or OFFICIAL.get(code) == WINBIG_URL:
        urls.append(("winbig", WINBIG_URL))
    elif code not in ALTERNATIVE:
        # Para las loterías oficiales, Winbig actúa como comprobación adicional.
        urls.append(("winbig", WINBIG_URL))
    return urls

def extract_winbig_for_code(code):
    # Winbig contiene múltiples loterías; se intenta detectar por nombre/código.
    try:
        html = fetch(WINBIG_URL)
    except Exception as exc:
        log.warning("Winbig falló: %s", exc)
        return {}

    soup = BeautifulSoup(html, "html.parser")
    target_names = [LOTTERIES.get(code, {}).get("name", "")]
    target_names += [k for k, v in ALIASES.items() if v == code]

    results = {}
    # Busca contenedores que mencionen el nombre de la lotería.
    for el in soup.find_all(["article", "div", "section", "li", "tr"]):
        txt = norm_text(el.get_text(" ", strip=True))
        upper = normalize_name(txt)
        if not any(normalize_name(n) and normalize_name(n) in upper for n in target_names):
            continue
        for hh, mm, num in extract_candidates(txt):
            results[f"{hh:02d}:{mm:02d}"] = num
    return results

def merge_source_results(code):
    """
    Prioridad:
    - Una fuente única: ese resultado.
    - Múltiples fuentes: se busca consenso.
    - Oficial tiene prioridad si el resto no coincide en el siguiente ciclo.
    - Si solo alternativa tiene resultado y oficial no, queda pendiente.
    - Ruleta Activa: D de principal debe coincidir con alternativa.
    """
    by_source = {}
    urls = source_urls(code)

    for label, url in urls:
        if url == WINBIG_URL:
            data = extract_winbig_for_code(code)
            if not data:
                data = extract_source_results(url, code)
        else:
            data = extract_source_results(url, code)
        by_source[label] = data

    all_times = set()
    for data in by_source.values():
        all_times.update(data.keys())

    merged = {}
    for tm in sorted(all_times):
        vals = {label: data[tm] for label, data in by_source.items() if tm in data}
        if not vals:
            continue

        # Si solo hay una fuente disponible.
        if len(vals) == 1:
            only_label, only_val = next(iter(vals.items()))
            if only_label == "alternative" and "official" in by_source:
                # No se confirma solo con alternativa.
                continue
            merged[tm] = only_val
            continue

        unique = set(vals.values())
        if len(unique) == 1:
            merged[tm] = next(iter(unique))
            continue

        # Conflicto: oficial manda cuando existe.
        if "official" in vals:
            # Si oficial ya tiene resultado, usamos oficial.
            merged[tm] = vals["official"]
        else:
            # Sin oficial, no inventar consenso.
            continue

    return merged, by_source

def lottery_is_active_at(code, hhmm):
    cfg = LOTTERIES[code]
    h, m = map(int, hhmm.split(":"))
    minutes = h * 60 + m

    if "windows" in cfg:
        for start, end in cfg["windows"]:
            sh, sm = map(int, start.split(":"))
            eh, em = map(int, end.split(":"))
            if sh * 60 + sm <= minutes <= eh * 60 + em:
                return True
        return False

    sh, sm = map(int, cfg["start"].split(":"))
    eh, em = map(int, cfg["end"].split(":"))
    return sh * 60 + sm <= minutes <= eh * 60 + em

def scheduled_times(code, block):
    cfg = LOTTERIES[code]
    start = cfg.get("display_start", cfg.get("start"))
    end = cfg["end"]
    sh, sm = map(int, start.split(":"))
    eh, em = map(int, end.split(":"))

    # Gatazo se muestra como 09:30 en la tabla, aunque su horario real empieza 09:40.
    if code == "GATAZO":
        sm = 30

    times = []
    cur = sh * 60 + sm
    endm = eh * 60 + em
    while cur <= endm:
        hhmm = f"{cur // 60:02d}:{cur % 60:02d}"
        if lottery_is_active_at(code, hhmm) or code == "GATAZO":
            times.append(hhmm)
        else:
            times.append(hhmm)
        cur += 60
    return times

def display_time(hhmm):
    h, m = map(int, hhmm.split(":"))
    suffix = "AM" if h < 12 else "PM"
    hour = h % 12 or 12
    return f"{hour:02d}:{m:02d}"

def table_header(codes):
    return " HORA🎰" + "🪙".join(codes)

def table_cell(code, hhmm, results):
    if not lottery_is_active_at(code, hhmm) and code != "GATAZO":
        return NO_DRAW
    n = results.get(hhmm)
    return result_display(n)

def update_all_results():
    """
    Actualiza todas las fuentes y rellena resultados históricos pendientes.
    Nunca reemplaza un resultado confirmado por un pendiente.
    """
    today = now().strftime("%Y-%m-%d")
    all_data = {}

    for code in LOTTERIES:
        try:
            merged, sources = merge_source_results(code)
            all_data[code] = merged
            state["tables"].setdefault(today, {}).setdefault(code, {})
            for tm, n in merged.items():
                state["tables"][today][code][tm] = n
        except Exception as exc:
            log.exception("Error actualizando %s: %s", code, exc)

    save_state()
    return all_data

def build_table(block, refresh=True):
    today = now().strftime("%Y-%m-%d")
    if refresh:
        update_all_results()

    lines = [BANNER, "", HEADERS[block], "➖" * 12]

    for group in BLOCKS[block]:
        lines.append(table_header(group))
        # Tabla visible desde la hora más temprana del grupo.
        all_times = set()
        for code in group:
            all_times.update(scheduled_times(code, block))

        # No mostrar horas futuras.
        current_minutes = now().hour * 60 + now().minute
        visible = []
        for tm in sorted(all_times):
            h, m = map(int, tm.split(":"))
            if h * 60 + m <= current_minutes:
                visible.append(tm)

        # Las tablas empiezan a publicarse a partir de 08:10.
        if block in (10, 20, 50) and current_minutes < 8 * 60 + 10:
            visible = []

        for tm in visible:
            row = [f"⏰{display_time(tm)}"]
            for code in group:
                results = state["tables"].get(today, {}).get(code, {})
                row.append(table_cell(code, tm, results))
            lines.append("  ".join(row))
        lines.append("")

    lines.append("MUCHA SUERTE EN SUS JUGADAS")
    return "\n".join(lines)

def get_latest_result(code):
    today = now().strftime("%Y-%m-%d")
    data = state["tables"].get(today, {}).get(code, {})
    if not data:
        return None, None
    tm = sorted(data.keys())[-1]
    return tm, data[tm]

def send_message(text):
    try:
        return bot.send_message(ACTIVE_CHANNEL_ID, text, disable_web_page_preview=True)
    except Exception as exc:
        log.exception("No se pudo enviar a %s: %s", ACTIVE_CHANNEL_ID, exc)
        return None

def send_individual_result(code, tm, number):
    key = f"{now().strftime('%Y-%m-%d')}:{code}:{tm}:{number}"
    if state["sent_results"].get(key):
        return False

    cfg = LOTTERIES[code]
    text = (
        f"{BANNER}\n\n"
        f"🎰 <b>{cfg['name'].upper()}</b>\n"
        f"⏰ <b>{display_time(tm)}</b>\n"
        f"🎯 <b>Resultado: {number:02d}{ANIMAL_EMOJI.get(number, '🎰')}</b>"
    )
    msg = send_message(text)
    if msg:
        state["sent_results"][key] = True
        save_state()
        return True
    return False

def pyramid_for_date(dt):
    """
    Construye una pirámide a partir de 4 pares numéricos.
    La regla de cada fila: suma de dígitos adyacentes; si supera 9,
    conserva el dígito de unidades. Los datos clave se calculan a partir
    de la pirámide y siempre quedan en 0, 00 o 01..36.
    """
    # Semilla reproducible diaria basada en la fecha.
    seed = [int(x) for x in dt.strftime("%d%m")]
    # Expandir a 8 dígitos para formar 4 pares.
    digits = seed + [int(x) for x in dt.strftime("%Y")[:2]]
    top = digits[:8]

    rows = [top]
    current = top
    while len(current) > 1:
        nxt = [(current[i] + current[i + 1]) % 10 for i in range(len(current) - 1)]
        rows.append(nxt)
        current = nxt

    # Dos pares de datos clave basados en posiciones de la pirámide.
    candidates = []
    for row in rows:
        for i in range(0, len(row) - 1, 2):
            pair = int(f"{row[i]}{row[i+1]}")
            candidates.append(pair)

    # Selección determinista de seis valores dentro de 0/00/01..36.
    valid = []
    for x in candidates:
        if x == 0:
            valid.append("00")
        elif 1 <= x <= 36:
            valid.append(f"{x:02d}")

    # Completar con cálculos de suma/reducción si faltan.
    flat_sum = sum(top)
    for x in [
        flat_sum,
        sum(rows[-1]),
        sum(sum(r) for r in rows),
        abs(top[0] - top[-1]) * 3,
        (top[0] + top[-1]) * 2,
        (rows[-1][0] if rows[-1] else 0),
    ]:
        x = x % 37
        if x == 0:
            valid.append("00")
        else:
            valid.append(f"{x:02d}")

    # Únicos, máximo 6.
    out = []
    for x in valid:
        if x not in out:
            out.append(x)
        if len(out) == 6:
            break

    while len(out) < 6:
        out.append("00" if len(out) % 2 == 0 else "01")

    return rows, out[:6]

def pyramid_text():
    dt = now()
    rows, keys = pyramid_for_date(dt)
    lines = ["<b>🔥 PIRÁMIDE NUMÉRICA DEL DÍA 🔥</b>", ""]
    for row in rows:
        lines.append("  " * (len(rows) - len(row)) + " ".join(str(x) for x in row))
    lines += [
        "",
        "🔥 <b>DATOS CLAVES PARA HOY:</b>",
        f"📌 {keys[0]}-{keys[1]}-{keys[2]}",
        f"📌 {keys[3]}-{keys[4]}-{keys[5]}",
    ]
    return "\n".join(lines)

# ============================================================
# PROGRAMACIÓN
# ============================================================

def scheduler_loop():
    log.info("Scheduler iniciado. Destino activo: %s", ACTIVE_CHANNEL_ID)
    last_minute = None

    while True:
        try:
            current = now()
            stamp = current.strftime("%Y-%m-%d %H:%M")
            minute = current.minute

            # Actualización de fuentes cada minuto.
            update_all_results()

            # Pirámide una vez al día, 07:00.
            if current.hour == 7 and minute == 0:
                key = f"pyramid:{current.strftime('%Y-%m-%d')}"
                if not state["last_scheduled"].get(key):
                    send_message(pyramid_text())
                    state["last_scheduled"][key] = True
                    save_state()

            # Aviso de taquilla desde 07:10, cada hora.
            if current.hour >= 7 and current.hour <= 18 and minute == 10:
                key = f"taquilla:{current.strftime('%Y-%m-%d')}:{current.hour}"
                if not state["last_scheduled"].get(key):
                    send_message(
                        f"{BANNER}\n\n"
                        f"📢 <b>TAQUILLA ACTIVA</b>\n"
                        f"⏰ {current.strftime('%I:%M %p')}\n"
                        f"Envía tus jugadas y participa."
                    )
                    state["last_scheduled"][key] = True
                    save_state()

            # Tablas: minuto 10, 20 y 50.
            for block, target_minute in [(10, 10), (20, 20), (50, 50)]:
                if minute == target_minute:
                    key = f"table:{current.strftime('%Y-%m-%d')}:{block}:{current.hour}"
                    if not state["last_scheduled"].get(key):
                        send_message(build_table(block, refresh=True))
                        state["last_scheduled"][key] = True
                        save_state()

            # Individuales: después de actualizar, detectar resultados nuevos.
            today = current.strftime("%Y-%m-%d")
            for code, cfg in LOTTERIES.items():
                data = state["tables"].get(today, {}).get(code, {})
                for tm, number in sorted(data.items()):
                    h, m = map(int, tm.split(":"))
                    # Solo mandar resultados del día que ya ocurrieron.
                    if h * 60 + m <= current.hour * 60 + current.minute:
                        send_individual_result(code, tm, number)

            time.sleep(30)
        except Exception as exc:
            log.exception("Error en scheduler: %s", exc)
            time.sleep(30)

# ============================================================
# ENDPOINTS HTTP
# ============================================================

@app.get("/")
def root():
    return jsonify({
        "status": "ok",
        "bot": "AG HAROLD JOSE BOT",
        "active_channel": ACTIVE_CHANNEL_ID,
        "main_reference": MAIN_CHANNEL_REFERENCE,
        "timezone": TIMEZONE,
    })

@app.get("/health")
def health():
    return jsonify({"status": "healthy", "time": now().isoformat()})

@app.get("/test/piramide")
def test_piramide():
    return app.response_class(pyramid_text(), mimetype="text/plain; charset=utf-8")

@app.get("/test/table/10")
def test_table_10():
    return app.response_class(build_table(10), mimetype="text/plain; charset=utf-8")

@app.get("/test/table/20")
def test_table_20():
    return app.response_class(build_table(20), mimetype="text/plain; charset=utf-8")

@app.get("/test/table/50")
def test_table_50():
    return app.response_class(build_table(50), mimetype="text/plain; charset=utf-8")

@app.get("/test/source/<code>")
def test_source(code):
    code = code.upper()
    if code not in LOTTERIES:
        return jsonify({"error": "Código no registrado", "valid": list(LOTTERIES)}), 404
    merged, sources = merge_source_results(code)
    return jsonify({
        "code": code,
        "name": LOTTERIES[code]["name"],
        "merged": merged,
        "sources": sources,
        "urls": source_urls(code),
    })

@app.get("/test/all-sources")
def test_all_sources():
    result = {}
    for code in LOTTERIES:
        try:
            merged, sources = merge_source_results(code)
            result[code] = {"merged": merged, "sources": sources}
        except Exception as exc:
            result[code] = {"error": str(exc)}
    return jsonify(result)

@app.get("/test/send/table/<int:block>")
def test_send_table(block):
    if block not in (10, 20, 50):
        return jsonify({"error": "Bloque debe ser 10, 20 o 50"}), 400
    msg = send_message(build_table(block))
    return jsonify({"sent": bool(msg), "channel": ACTIVE_CHANNEL_ID})

@app.get("/test/send/piramide")
def test_send_pyramid():
    msg = send_message(pyramid_text())
    return jsonify({"sent": bool(msg), "channel": ACTIVE_CHANNEL_ID})

# ============================================================
# COMANDOS TELEGRAM
# ============================================================

@bot.message_handler(commands=["start"])
def cmd_start(message):
    bot.reply_to(
        message,
        "🤖 <b>AG HAROLD JOSE BOT</b>\n"
        "Bot activo.\n"
        f"Canal de prueba: {ACTIVE_CHANNEL_ID}\n"
        "Usa /id para consultar el ID del chat."
    )

@bot.message_handler(commands=["id"])
def cmd_id(message):
    bot.reply_to(message, f"🆔 Chat ID: <code>{message.chat.id}</code>")

@bot.message_handler(commands=["test10"])
def cmd_test10(message):
    bot.send_message(message.chat.id, build_table(10), disable_web_page_preview=True)

@bot.message_handler(commands=["test20"])
def cmd_test20(message):
    bot.send_message(message.chat.id, build_table(20), disable_web_page_preview=True)

@bot.message_handler(commands=["test50"])
def cmd_test50(message):
    bot.send_message(message.chat.id, build_table(50), disable_web_page_preview=True)

@bot.message_handler(commands=["piramide"])
def cmd_piramide(message):
    bot.send_message(message.chat.id, pyramid_text(), disable_web_page_preview=True)

def run_flask():
    app.run(host="0.0.0.0", port=PORT, threaded=True)

def main():
    log.info("Iniciando AG HAROLD JOSE BOT")
    log.info("Canal de prueba/destino activo: %s", ACTIVE_CHANNEL_ID)
    log.info("Canal principal solo referencia: %s", MAIN_CHANNEL_REFERENCE)

    threading.Thread(target=run_flask, daemon=True).start()
    threading.Thread(target=scheduler_loop, daemon=True).start()

    while True:
        try:
            bot.infinity_polling(
                timeout=30,
                long_polling_timeout=30,
                allowed_updates=["message", "channel_post"],
            )
        except Exception as exc:
            log.exception("Polling detenido: %s", exc)
            time.sleep(10)

if __name__ == "__main__":
    main()
