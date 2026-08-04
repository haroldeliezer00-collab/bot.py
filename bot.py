import os
import re
import json
import time
import logging
import threading
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
from flask import Flask, jsonify
import telebot
from telebot.apihelper import ApiTelegramException

# ============================================================
# AG HAROLD JOSE BOT - VERSION OPTIMIZADA PARA RENDER
# ============================================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
TEST_CHANNEL_ID = os.getenv("TEST_CHANNEL_ID", "@pruebajsj").strip()
ACTIVE_CHANNEL_ID = os.getenv("ACTIVE_CHANNEL_ID", TEST_CHANNEL_ID).strip()
MAIN_CHANNEL_REFERENCE = os.getenv("MAIN_CHANNEL_REFERENCE", "@AGHAROLDJOSE_BOT").strip()
TIMEZONE = os.getenv("TIMEZONE", "America/Caracas").strip()
PORT = int(os.getenv("PORT", "10000"))
RESULTS_REFRESH_SECONDS = int(os.getenv("RESULTS_REFRESH_SECONDS", "60"))
SCHEDULER_SECONDS = int(os.getenv("SCHEDULER_SECONDS", "30"))
POLLING_CONFLICT_WAIT = int(os.getenv("POLLING_CONFLICT_WAIT", "60"))
STATE_RETENTION_DAYS = int(os.getenv("STATE_RETENTION_DAYS", "3"))

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

# ============================================================
# HTTP
# ============================================================

SESSION = requests.Session()
retry_strategy = Retry(
    total=3,
    connect=3,
    read=3,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=frozenset(["GET"]),
    raise_on_status=False,
)
adapter = HTTPAdapter(
    max_retries=retry_strategy,
    pool_connections=10,
    pool_maxsize=20,
)
SESSION.mount("https://", adapter)
SESSION.mount("http://", adapter)
SESSION.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/151.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-VE,es;q=0.9,en;q=0.8",
})

STATE_FILE = os.getenv("STATE_FILE", "bot_state.json")
state_lock = threading.RLock()
results_lock = threading.Lock()
send_lock = threading.Lock()

last_results_update = 0.0
last_results_date = ""

# ============================================================
# BANNER
# ============================================================

BANNER = """<b>AGENCIA HAROLD JOSE</b>
<b>SEGURIDAD Y CONFIANZA</b>
<b>RESULTADOS OFICIALES</b>

📲 JUEGA AQUI 👇👇
WHATSAPP: 04124489363

📢 CANAL DE RESULTADOS:
https://t.me/resultadosagharoldjose"""

PENDING = "⏳"
NO_DRAW = "🔕"

# ============================================================
# ANIMALITOS
# ============================================================

ANIMAL_EMOJI = {
    0: "🐬", 1: "🐏", 2: "🐂", 3: "🐛", 4: "🦂", 5: "🦁",
    6: "🐸", 7: "🦜", 8: "🐁", 9: "🦅", 10: "🐯", 11: "😺",
    12: "🐎", 13: "🐵", 14: "🕊️", 15: "🦊", 16: "🐻", 17: "🦃",
    18: "🫏", 19: "🐐", 20: "🐷", 21: "🐓", 22: "🐫", 23: "🦓",
    24: "🦎", 25: "🐔", 26: "🐮", 27: "🐶", 28: "🦇", 29: "🐘",
    30: "🐊", 31: "🐗", 32: "🐿️", 33: "🐠", 34: "🦌", 35: "🦒",
    36: "🐍",
}

# ============================================================
# FUENTES
# ============================================================

WINBIG_URL = "https://lotery.winbigvzla.com/resultados"

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

ALTERNATIVE = {
    "L.ACT": ["https://resultados365.com/resultados/lotto-activo"],
    "GRAJ": ["https://resultados365.com/resultados/la-granjita/"],
    "SELV": ["https://resultados365.com/resultados/selvaplus/"],
    "R.ACT": ["https://loteriadehoy.com/animalito/ruletaactiva/resultados/"],
}

# ============================================================
# LOTERIAS
# ============================================================

LOTTERIES = {
    "L.ACT": {"name": "Lotto Activo", "start": "08:00", "end": "19:00", "block": 10},
    "GRAJ": {"name": "La Granjita", "start": "08:00", "end": "19:00", "block": 10},
    "SELV": {"name": "Selva Plus", "start": "08:00", "end": "19:00", "block": 10},
    "G.ARO": {"name": "Guácharo Activo", "start": "08:00", "end": "19:00", "block": 10},
    "CHAIMA": {"name": "Loto Chaima", "start": "08:00", "end": "19:00", "block": 10},
    "TRIO": {"name": "Trío Activo 🇻🇪", "start": "08:00", "end": "19:00", "block": 10},
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

BLOCKS = {
    10: [
        ["GRAJ", "L.ACT", "SELV"],
        ["G.ARO", "CHAIMA", "TRIO"],
        ["MONJE", "L.ANIM", "L.PANT"],
        ["L.REAL", "L.RD", "CEN.A"],
        ["MEGA", "R.PER", "R.COL"],
        ["R.VEN", "COND", "FRUI"],
        ["TROP", "G.MIL", "ZOOL"],
        ["L.MAX", "C.ANI"],
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
    10: "📰 RESULTADOS ANIMALITOS 📰",
    20: "📰 RESULTADOS ANIMALITOS 📰",
    50: "📰 RESULTADOS ANIMALITOS 📰",
}

state = {
    "sent_results": {},
    "tables": {},
    "last_pyramid_date": "",
    "last_scheduled": {},
    "last_individual": {},
}

# ============================================================
# ESTADO
# ============================================================

def load_state():
    global state
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        if isinstance(loaded, dict):
            with state_lock:
                for key in state:
                    if key in loaded:
                        state[key] = loaded[key]
        log.info("Estado cargado correctamente.")
    except FileNotFoundError:
        log.info("No existe estado previo. Se iniciará uno nuevo.")
    except Exception as exc:
        log.warning("No se pudo cargar estado: %s", exc)


def save_state():
    tmp = STATE_FILE + ".tmp"
    try:
        with state_lock:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
            os.replace(tmp, STATE_FILE)
    except Exception as exc:
        log.exception("Error guardando estado: %s", exc)
    finally:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass


def cleanup_old_state():
    cutoff = now().date() - timedelta(days=STATE_RETENTION_DAYS)
    cutoff_str = cutoff.strftime("%Y-%m-%d")

    with state_lock:
        for date_key in list(state.get("tables", {}).keys()):
            if date_key < cutoff_str:
                state["tables"].pop(date_key, None)

        for key in list(state.get("sent_results", {}).keys()):
            date_part = key[:10]
            if len(date_part) == 10 and date_part < cutoff_str:
                state["sent_results"].pop(key, None)

        for key in list(state.get("last_scheduled", {}).keys()):
            match = re.search(r"(\d{4}-\d{2}-\d{2})", key)
            if match and match.group(1) < cutoff_str:
                state["last_scheduled"].pop(key, None)

    save_state()


load_state()

# ============================================================
# UTILIDADES
# ============================================================

def now():
    return datetime.now(TZ)


def norm_text(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def normalize_name(value):
    value = str(value or "").upper()
    value = value.replace("🇻🇪", " ")
    value = value.replace("TRÍO", "TRIO")
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
    "TRIO ACTIVO": "TRIO",
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
    normalized = normalize_name(name)
    if normalized in ALIASES:
        return ALIASES[normalized]
    if "TRIO ACTIVO" in normalized:
        return "TRIO"
    return None


# ============================================================
# RESULTADOS
# ============================================================

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
    return n if 0 <= n <= 99 else None


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
        minute = int(m.group(2)) if m.group(2).isdigit() else 0
        ampm = m.group(3) if len(m.groups()) >= 3 else None
        if ampm is None and len(m.groups()) >= 2 and m.group(2).isalpha():
            ampm = m.group(2)
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
    text = norm_text(text)
    candidates = []

    patterns = [
        r"\b(\d{1,2}):(\d{2})\b.{0,80}?\b(\d{1,2})\b",
        r"\b(\d{1,2}):(\d{2})\s+(\d{1,2})\b",
        r"\b(\d{1,2}):(\d{2})\s*(?:-|:|→|>)\s*(\d{1,2})\b",
    ]

    for pattern in patterns:
        for m in re.finditer(pattern, text):
            hh, mm, num = map(int, m.groups())
            if 0 <= hh <= 23 and 0 <= mm <= 59 and 0 <= num <= 99:
                candidates.append((hh, mm, num))

    seen = set()
    out = []
    for item in candidates:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


# ============================================================
# HTTP / EXTRACCION
# ============================================================

def fetch(url, timeout=15):
    response = SESSION.get(url, timeout=timeout, allow_redirects=True)
    if response.status_code == 403:
        log.warning("Fuente respondió 403 Forbidden: %s", url)
        return ""
    response.raise_for_status()
    return response.text


def extract_source_results(url, lottery_code=None):
    try:
        html = fetch(url)
        if not html:
            return {}
    except Exception as exc:
        log.warning("Fuente falló %s: %s", url, exc)
        return {}

    soup = BeautifulSoup(html, "html.parser")
    results = {}

    for tr in soup.find_all("tr"):
        cells = [
            norm_text(c.get_text(" ", strip=True))
            for c in tr.find_all(["td", "th"])
        ]
        if len(cells) < 2:
            continue
        for hh, mm, num in extract_candidates(" ".join(cells)):
            results[f"{hh:02d}:{mm:02d}"] = num

    for el in soup.find_all(["article", "div", "li", "section"]):
        txt = norm_text(el.get_text(" ", strip=True))
        if len(txt) > 300:
            continue
        for hh, mm, num in extract_candidates(txt):
            results[f"{hh:02d}:{mm:02d}"] = num

    for hh, mm, num in extract_candidates(soup.get_text(" ", strip=True)):
        results[f"{hh:02d}:{mm:02d}"] = num

    return results


def extract_winbig_for_code(code, html=None):
    try:
        if html is None:
            html = fetch(WINBIG_URL)
        if not html:
            return {}
    except Exception as exc:
        log.warning("Winbig falló: %s", exc)
        return {}

    soup = BeautifulSoup(html, "html.parser")
    target_name = normalize_name(LOTTERIES[code]["name"])
    results = {}

    for el in soup.find_all(["article", "div", "section", "li", "tr"]):
        txt = norm_text(el.get_text(" ", strip=True))
        normalized = normalize_name(txt)
        if target_name and target_name not in normalized:
            continue
        for hh, mm, num in extract_candidates(txt):
            results[f"{hh:02d}:{mm:02d}"] = num

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
        urls.append(("winbig", WINBIG_URL))

    seen = set()
    unique = []
    for label, url in urls:
        if (label, url) not in seen:
            seen.add((label, url))
            unique.append((label, url))
    return unique


def merge_source_results(code, winbig_html=None):
    by_source = {}

    for label, url in source_urls(code):
        if url == WINBIG_URL:
            data = extract_winbig_for_code(code, html=winbig_html)
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
        vals = {
            label: data[tm]
            for label, data in by_source.items()
            if tm in data
        }

        if not vals:
            continue

        if len(vals) == 1:
            only_label, only_val = next(iter(vals.items()))
            if only_label == "alternative" and "official" in by_source:
                continue
            merged[tm] = only_val
            continue

        unique = set(vals.values())
        if len(unique) == 1:
            merged[tm] = next(iter(unique))
            continue

        if "official" in vals:
            merged[tm] = vals["official"]

    return merged, by_source


# ============================================================
# HORARIOS
# ============================================================

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


def scheduled_times(code, block=None):
    cfg = LOTTERIES[code]
    times = []

    if "windows" in cfg:
        windows = cfg["windows"]
    else:
        windows = [(
            cfg.get("display_start", cfg["start"]),
            cfg["end"]
        )]

    for start, end in windows:
        sh, sm = map(int, start.split(":"))
        eh, em = map(int, end.split(":"))
        cur = sh * 60 + sm
        endm = eh * 60 + em

        while cur <= endm:
            times.append(f"{cur // 60:02d}:{cur % 60:02d}")
            cur += 60

    return times


def display_time(hhmm):
    h, m = map(int, hhmm.split(":"))
    suffix = "AM" if h < 12 else "PM"
    hour = h % 12 or 12
    return f"{hour:02d}:{m:02d} {suffix}"


# ============================================================
# ACTUALIZAR RESULTADOS CON CACHE
# ============================================================

def update_all_results(force=False):
    global last_results_update, last_results_date

    current = now()
    today = current.strftime("%Y-%m-%d")
    current_ts = time.time()

    with results_lock:
        if not force and today == last_results_date:
            if current_ts - last_results_update < RESULTS_REFRESH_SECONDS:
                with state_lock:
                    return {
                        code: state.get("tables", {}).get(today, {}).get(code, {})
                        for code in LOTTERIES
                    }

        log.info("Actualizando resultados. Fecha: %s", today)

        winbig_html = None
        if any(
            url == WINBIG_URL
            for code in LOTTERIES
            for _, url in source_urls(code)
        ):
            try:
                winbig_html = fetch(WINBIG_URL)
            except Exception as exc:
                log.warning("No se pudo cargar Winbig: %s", exc)

        all_data = {}

        for code in LOTTERIES:
            try:
                merged, _sources = merge_source_results(
                    code,
                    winbig_html=winbig_html
                )
                all_data[code] = merged

                with state_lock:
                    state.setdefault("tables", {}).setdefault(today, {}).setdefault(code, {})
                    for tm, n in merged.items():
                        state["tables"][today][code][tm] = n

            except Exception as exc:
                log.exception("Error actualizando %s: %s", code, exc)

        last_results_update = current_ts
        last_results_date = today
        save_state()

        return all_data


# ============================================================
# TABLAS
# ============================================================

def table_header(codes):
    return " HORA🎰" + "🪙".join(codes)


def table_cell(code, hhmm, results):
    if not lottery_is_active_at(code, hhmm):
        return NO_DRAW
    return result_display(results.get(hhmm))


def build_table(block, refresh=True):
    if refresh:
        update_all_results()

    today = now().strftime("%Y-%m-%d")

    lines = [
        BANNER,
        "",
        HEADERS[block],
        "➖" * 12
    ]

    for group in BLOCKS[block]:
        lines.append(table_header(group))
        all_times = set()

        for code in group:
            all_times.update(scheduled_times(code, block))

        current_minutes = now().hour * 60 + now().minute
        visible = []

        for tm in sorted(all_times):
            h, m = map(int, tm.split(":"))
            if h * 60 + m <= current_minutes:
                visible.append(tm)

        if block in (10, 20, 50) and current_minutes < 8 * 60 + 10:
            visible = []

        for tm in visible:
            row = [f"⏰{display_time(tm)}"]

            for code in group:
                with state_lock:
                    results = (
                        state.get("tables", {})
                        .get(today, {})
                        .get(code, {})
                    )
                    results = dict(results)

                row.append(table_cell(code, tm, results))

            lines.append("  ".join(row))

        lines.append("")

    lines.append("MUCHA SUERTE EN SUS JUGADAS")
    return "\n".join(lines)


# ============================================================
# TELEGRAM
# ============================================================

def send_message(text):
    try:
        with send_lock:
            return bot.send_message(
                ACTIVE_CHANNEL_ID,
                text,
                disable_web_page_preview=True
            )
    except Exception as exc:
        log.exception(
            "No se pudo enviar a %s: %s",
            ACTIVE_CHANNEL_ID,
            exc
        )
        return None


def send_individual_result(code, tm, number):
    today = now().strftime("%Y-%m-%d")
    key = f"{today}:{code}:{tm}:{number}"

    with state_lock:
        if state["sent_results"].get(key):
            return False

    cfg = LOTTERIES[code]
    text = (
        f"{BANNER}\n\n"
        f"🎰 <b>{cfg['name'].upper()}</b>\n"
        f"⏰ <b>{display_time(tm)}</b>\n"
        f"🎯 <b>Resultado: {number:02d}"
        f"{ANIMAL_EMOJI.get(number, '🎰')}</b>"
    )

    msg = send_message(text)

    if msg:
        with state_lock:
            state["sent_results"][key] = True
        save_state()
        return True

    return False


# ============================================================
# PIRAMIDE
# ============================================================

def pyramid_for_date(dt):
    seed = [int(x) for x in dt.strftime("%d%m")]
    digits = seed + [int(x) for x in dt.strftime("%Y")[:2]]
    top = digits[:8]

    rows = [top]
    current = top

    while len(current) > 1:
        current = [
            (current[i] + current[i + 1]) % 10
            for i in range(len(current) - 1)
        ]
        rows.append(current)

    candidates = []

    for row in rows:
        for i in range(0, len(row) - 1, 2):
            candidates.append(int(f"{row[i]}{row[i + 1]}"))

    valid = []

    for x in candidates:
        if x == 0:
            valid.append("00")
        elif 1 <= x <= 36:
            valid.append(f"{x:02d}")

    flat_sum = sum(top)

    for x in [
        flat_sum,
        sum(rows[-1]),
        sum(sum(r) for r in rows),
        abs(top[0] - top[-1]) * 3,
        (top[0] + top[-1]) * 2,
        rows[-1][0] if rows[-1] else 0,
    ]:
        x %= 37
        valid.append("00" if x == 0 else f"{x:02d}")

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
    rows, keys = pyramid_for_date(now())

    lines = [
        "<b>🔥 PIRÁMIDE NUMÉRICA DEL DÍA 🔥</b>",
        ""
    ]

    for row in rows:
        lines.append(
            "  " * (len(rows) - len(row))
            + " ".join(str(x) for x in row)
        )

    lines += [
        "",
        "🔥 <b>DATOS CLAVES PARA HOY:</b>",
        f"📌 {keys[0]}-{keys[1]}-{keys[2]}",
        f"📌 {keys[3]}-{keys[4]}-{keys[5]}",
    ]

    return "\n".join(lines)


# ============================================================
# SCHEDULER
# ============================================================

def scheduler_loop():
    log.info(
        "Scheduler iniciado. Destino activo: %s",
        ACTIVE_CHANNEL_ID
    )

    last_scheduler_minute = None

    while True:
        try:
            current = now()
            minute_key = current.strftime("%Y-%m-%d-%H-%M")
            is_new_minute = minute_key != last_scheduler_minute

            if is_new_minute:
                last_scheduler_minute = minute_key

                update_all_results()

                # PIRAMIDE
                if current.hour == 7 and current.minute == 0:
                    key = f"pyramid:{current.strftime('%Y-%m-%d')}"

                    with state_lock:
                        already_sent = state["last_scheduled"].get(key)

                    if not already_sent:
                        msg = send_message(pyramid_text())
                        if msg:
                            with state_lock:
                                state["last_scheduled"][key] = True
                            save_state()

                # TAQUILLA
                if 7 <= current.hour <= 18 and current.minute == 10:
                    key = (
                        f"taquilla:{current.strftime('%Y-%m-%d')}:"
                        f"{current.hour}"
                    )

                    with state_lock:
                        already_sent = state["last_scheduled"].get(key)

                    if not already_sent:
                        msg = send_message(
                            f"{BANNER}\n\n"
                            f"📢 <b>TAQUILLA ACTIVA</b>\n"
                            f"⏰ {current.strftime('%I:%M %p')}\n"
                            f"Envía tus jugadas y participa."
                        )

                        if msg:
                            with state_lock:
                                state["last_scheduled"][key] = True
                            save_state()

                # TABLAS
                for block, target_minute in [
                    (10, 10),
                    (20, 20),
                    (50, 50)
                ]:
                    if minute_key and current.minute == target_minute:
                        key = (
                            f"table:{current.strftime('%Y-%m-%d')}:"
                            f"{block}:{current.hour}"
                        )

                        with state_lock:
                            already_sent = state["last_scheduled"].get(key)

                        if not already_sent:
                            msg = send_message(
                                build_table(block, refresh=False)
                            )

                            if msg:
                                with state_lock:
                                    state["last_scheduled"][key] = True
                                save_state()

                # RESULTADOS INDIVIDUALES
                today = current.strftime("%Y-%m-%d")
                current_total = current.hour * 60 + current.minute

                with state_lock:
                    today_data = state.get("tables", {}).get(today, {})
                    snapshot = {
                        code: dict(today_data.get(code, {}))
                        for code in LOTTERIES
                    }

                for code in LOTTERIES:
                    for tm, number in sorted(snapshot.get(code, {}).items()):
                        h, m = map(int, tm.split(":"))

                        if h * 60 + m <= current_total:
                            send_individual_result(
                                code,
                                tm,
                                number
                            )

                if current.hour == 0 and current.minute == 5:
                    cleanup_old_state()

            time.sleep(SCHEDULER_SECONDS)

        except Exception as exc:
            log.exception("Error en scheduler: %s", exc)
            time.sleep(SCHEDULER_SECONDS)


# ============================================================
# ENDPOINTS
# ============================================================

@app.get("/")
def root():
    return jsonify({
        "status": "ok",
        "bot": "AG HAROLD JOSE BOT",
        "active_channel": ACTIVE_CHANNEL_ID,
        "main_reference": MAIN_CHANNEL_REFERENCE,
        "timezone": TIMEZONE,
        "trio_activo": "TRIO ACTIVO 🇻🇪",
    })


@app.get("/health")
def health():
    return jsonify({
        "status": "healthy",
        "time": now().isoformat()
    })


@app.get("/test/piramide")
def test_piramide():
    return app.response_class(
        pyramid_text(),
        mimetype="text/plain; charset=utf-8"
    )


@app.get("/test/table/10")
def test_table_10():
    return app.response_class(
        build_table(10),
        mimetype="text/plain; charset=utf-8"
    )


@app.get("/test/table/20")
def test_table_20():
    return app.response_class(
        build_table(20),
        mimetype="text/plain; charset=utf-8"
    )


@app.get("/test/table/50")
def test_table_50():
    return app.response_class(
        build_table(50),
        mimetype="text/plain; charset=utf-8"
    )


@app.get("/test/source/<code>")
def test_source(code):
    code = code.upper()

    if code not in LOTTERIES:
        return jsonify({
            "error": "Código no registrado",
            "valid": list(LOTTERIES)
        }), 404

    merged, sources = merge_source_results(code)

    return jsonify({
        "code": code,
        "name": LOTTERIES[code]["name"],
        "merged": merged,
        "sources": sources,
        "urls": source_urls(code)
    })


@app.get("/test/send/table/<int:block>")
def test_send_table(block):
    if block not in (10, 20, 50):
        return jsonify({
            "error": "Bloque debe ser 10, 20 o 50"
        }), 400

    msg = send_message(build_table(block))

    return jsonify({
        "sent": bool(msg),
        "channel": ACTIVE_CHANNEL_ID
    })


@app.get("/test/send/piramide")
def test_send_pyramid():
    msg = send_message(pyramid_text())

    return jsonify({
        "sent": bool(msg),
        "channel": ACTIVE_CHANNEL_ID
    })


@app.get("/test/update")
def test_update():
    data = update_all_results(force=True)

    return jsonify({
        "updated": True,
        "date": now().strftime("%Y-%m-%d"),
        "lotteries": len(data),
    })


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
    bot.reply_to(
        message,
        f"🆔 Chat ID: <code>{message.chat.id}</code>"
    )


@bot.message_handler(commands=["test10"])
def cmd_test10(message):
    bot.send_message(
        message.chat.id,
        build_table(10),
        disable_web_page_preview=True
    )


@bot.message_handler(commands=["test20"])
def cmd_test20(message):
    bot.send_message(
        message.chat.id,
        build_table(20),
        disable_web_page_preview=True
    )


@bot.message_handler(commands=["test50"])
def cmd_test50(message):
    bot.send_message(
        message.chat.id,
        build_table(50),
        disable_web_page_preview=True
    )


@bot.message_handler(commands=["piramide"])
def cmd_piramide(message):
    bot.send_message(
        message.chat.id,
        pyramid_text(),
        disable_web_page_preview=True
    )


# ============================================================
# FLASK
# ============================================================

def run_flask():
    app.run(
        host="0.0.0.0",
        port=PORT,
        threaded=True,
        use_reloader=False
    )


# ============================================================
# TELEGRAM POLLING
# ============================================================

def telegram_polling_loop():
    while True:
        try:
            log.info("Iniciando polling de Telegram...")

            bot.infinity_polling(
                timeout=30,
                long_polling_timeout=30,
                allowed_updates=[
                    "message",
                    "channel_post"
                ],
                skip_pending=True,
                restart_on_change=False
            )

            log.warning(
                "Polling terminó inesperadamente. "
                "Reintentando en 10 segundos."
            )
            time.sleep(10)

        except ApiTelegramException as exc:
            error_text = str(exc)

            if (
                getattr(exc, "error_code", None) == 409
                or "409" in error_text
                or "Conflict" in error_text
                or "terminated by other getUpdates" in error_text
            ):
                log.error(
                    "⚠️ TELEGRAM 409: otra instancia está usando "
                    "getUpdates con este BOT_TOKEN."
                )
                log.error(
                    "Esperando %s segundos antes de reintentar.",
                    POLLING_CONFLICT_WAIT
                )
                time.sleep(POLLING_CONFLICT_WAIT)
                continue

            log.exception("Error de Telegram: %s", exc)
            time.sleep(15)

        except Exception as exc:
            error_text = str(exc)

            if (
                "409" in error_text
                or "Conflict" in error_text
                or "terminated by other getUpdates" in error_text
            ):
                log.error(
                    "⚠️ Conflicto 409 detectado. "
                    "Esperando antes de reintentar."
                )
                time.sleep(POLLING_CONFLICT_WAIT)
                continue

            log.exception(
                "Error inesperado en polling: %s",
                exc
            )
            time.sleep(15)


# ============================================================
# MAIN
# ============================================================

def main():
    log.info("Iniciando AG HAROLD JOSE BOT")
    log.info("Canal activo: %s", ACTIVE_CHANNEL_ID)
    log.info("Canal principal referencia: %s", MAIN_CHANNEL_REFERENCE)
    log.info("TRIO ACTIVO 🇻🇪 integrado correctamente")
    log.info("Zona horaria: %s", TIMEZONE)
    log.info(
        "Actualización de resultados cada %s segundos.",
        RESULTS_REFRESH_SECONDS
    )

    threading.Thread(
        target=run_flask,
        name="FlaskServer",
        daemon=True
    ).start()

    threading.Thread(
        target=scheduler_loop,
        name="Scheduler",
        daemon=True
    ).start()

    # SOLO UNA instancia de polling dentro de este proceso.
    telegram_thread = threading.Thread(
        target=telegram_polling_loop,
        name="TelegramPolling",
        daemon=False
    )
    telegram_thread.start()
    telegram_thread.join()


cleanup_old_state()

if __name__ == "__main__":
    main()
