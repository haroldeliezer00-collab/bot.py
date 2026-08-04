import os
import re
import json
import time
import logging
import threading
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup
from flask import Flask, jsonify
import telebot

# ============================================================
# AG HAROLD JOSE BOT - VERSION CORREGIDA
# TRIO ACTIVO 🇻🇪 INTEGRADO
# ============================================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
TEST_CHANNEL_ID = os.getenv("TEST_CHANNEL_ID", "@pruebajsj").strip()
ACTIVE_CHANNEL_ID = os.getenv("ACTIVE_CHANNEL_ID", TEST_CHANNEL_ID).strip()
MAIN_CHANNEL_REFERENCE = os.getenv(
    "MAIN_CHANNEL_REFERENCE",
    "@AGHAROLDJOSE_BOT"
).strip()

TIMEZONE = os.getenv("TIMEZONE", "America/Caracas").strip()
PORT = int(os.getenv("PORT", "10000"))

if not BOT_TOKEN:
    raise RuntimeError(
        "Falta la variable de entorno BOT_TOKEN en Render."
    )

TZ = ZoneInfo(TIMEZONE)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

log = logging.getLogger("ag_harold_jose_bot")

bot = telebot.TeleBot(
    BOT_TOKEN,
    parse_mode="HTML"
)

app = Flask(__name__)

SESSION = requests.Session()

SESSION.headers.update({
    "User-Agent":
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/151.0 Safari/537.36"
})

STATE_FILE = "bot_state.json"

state_lock = threading.Lock()

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
# EMOJIS ANIMALITOS
# ============================================================

ANIMAL_EMOJI = {
    0: "🐬",
    1: "🐏",
    2: "🐂",
    3: "🐛",
    4: "🦂",
    5: "🦁",
    6: "🐸",
    7: "🦜",
    8: "🐁",
    9: "🦅",
    10: "🐯",
    11: "😺",
    12: "🐎",
    13: "🐵",
    14: "🕊️",
    15: "🦊",
    16: "🐻",
    17: "🦃",
    18: "🫏",
    19: "🐐",
    20: "🐷",
    21: "🐓",
    22: "🐫",
    23: "🦓",
    24: "🦎",
    25: "🐔",
    26: "🐮",
    27: "🐶",
    28: "🦇",
    29: "🐘",
    30: "🐊",
    31: "🐗",
    32: "🐿️",
    33: "🐠",
    34: "🦌",
    35: "🦒",
    36: "🐍",
}

# ============================================================
# FUENTES
# ============================================================

WINBIG_URL = "https://lotery.winbigvzla.com/resultados"

OFFICIAL = {
    "L.ACT":
        "https://www.lottoactivo.com/resultados/lotto_activo/",

    "G.ARO":
        "https://www.guacharoactivo.com.ve/resultados",

    "CHAIMA":
        "https://lotochaima.com/",

    "GRAJ":
        "https://lagranjitaonline.com/",

    "SELV":
        "https://www.selvaplus.com/resultados",

    "MONJE":
        "https://www.lottoactivo.com/resultados/"
        "lottoactivo2(monjemillonario)/",

    "L.RD":
        "https://www.lottoactivo.com/resultados/"
        "lotto_activo_internacional/",

    "GUACA":
        WINBIG_URL,

    "M.GUAC":
        WINBIG_URL,

    "G.ITO":
        "https://elguacharitomillonario.com/",

    # ========================================================
    # TRIO ACTIVO
    # La página muestra:
    # Trío Activo 🇻🇪
    # ========================================================

    "TRIO":
        "https://www.lottoactivo.com/resultados/trio_activo/",

    "P.PLUS":
        "https://www.guacaactiva.com/",
}

ALTERNATIVE = {
    "L.ACT": [
        "https://resultados365.com/resultados/lotto-activo"
    ],

    "GRAJ": [
        "https://resultados365.com/resultados/la-granjita/"
    ],

    "SELV": [
        "https://resultados365.com/resultados/selvaplus/"
    ],

    "R.ACT": [
        "https://loteriadehoy.com/animalito/"
        "ruletaactiva/resultados/"
    ],
}

# ============================================================
# LOTERIAS
# ============================================================

LOTTERIES = {

    "L.ACT": {
        "name": "Lotto Activo",
        "start": "08:00",
        "end": "19:00",
        "block": 10
    },

    "GRAJ": {
        "name": "La Granjita",
        "start": "08:00",
        "end": "19:00",
        "block": 10
    },

    "SELV": {
        "name": "Selva Plus",
        "start": "08:00",
        "end": "19:00",
        "block": 10
    },

    "G.ARO": {
        "name": "Guácharo Activo",
        "start": "08:00",
        "end": "19:00",
        "block": 10
    },

    "CHAIMA": {
        "name": "Loto Chaima",
        "start": "08:00",
        "end": "19:00",
        "block": 10
    },

    # ========================================================
    # TRIO ACTIVO 🇻🇪
    # ========================================================

    "TRIO": {
        "name": "Trío Activo 🇻🇪",
        "start": "08:00",
        "end": "19:00",
        "block": 10
    },

    "R.PER": {
        "name": "Ruleton Perú",
        "start": "08:00",
        "end": "20:00",
        "block": 10
    },

    "R.COL": {
        "name": "Ruleton Colombia",
        "start": "08:00",
        "end": "20:00",
        "block": 10
    },

    "R.VEN": {
        "name": "Ruleton Venezuela",
        "start": "09:00",
        "end": "21:00",
        "block": 10
    },

    "TROP": {
        "name": "Tropi Gana",
        "start": "08:00",
        "end": "19:00",
        "block": 10
    },

    "COND": {
        "name": "Cóndor Gana",
        "start": "08:00",
        "end": "19:00",
        "block": 10
    },

    "FRUI": {
        "name": "Fruti Gana",
        "start": "08:00",
        "end": "19:00",
        "block": 10
    },

    "G.MIL": {
        "name": "Granja Millonaria",
        "windows": [
            ("09:00", "13:00"),
            ("16:00", "20:00")
        ],
        "block": 10
    },

    "ZOOL": {
        "name": "Zoológico Activo",
        "start": "08:00",
        "end": "19:00",
        "block": 10
    },

    "L.MAX": {
        "name": "Lotto Max",
        "start": "09:00",
        "end": "19:00",
        "block": 10
    },

    "CEN.A": {
        "name": "Centena Animalitos",
        "start": "08:00",
        "end": "20:00",
        "block": 10
    },

    "L.RD": {
        "name": "Lotto Rd",
        "start": "08:00",
        "end": "19:00",
        "block": 10
    },

    "MONJE": {
        "name": "Monje Millonario",
        "start": "08:05",
        "end": "19:05",
        "block": 10
    },

    "L.ANIM": {
        "name": "Lotto Animalito",
        "start": "08:00",
        "end": "19:00",
        "block": 10
    },

    "L.PANT": {
        "name": "Lotto Pantera",
        "start": "08:00",
        "end": "19:00",
        "block": 10
    },

    "L.REAL": {
        "name": "Lotto Real",
        "start": "08:00",
        "end": "19:00",
        "block": 10
    },

    "MEGA": {
        "name": "Mega Animal",
        "start": "09:00",
        "end": "20:00",
        "block": 10
    },

    "C.ANI": {
        "name": "Chance Animal",
        "start": "09:00",
        "end": "19:00",
        "block": 10
    },

    "C.PLUS": {
        "name": "Centena Plus",
        "start": "08:15",
        "end": "20:15",
        "block": 20,
        "table_minute": 15
    },

    "G.PLUS": {
        "name": "Granjita Plus",
        "start": "08:10",
        "end": "19:10",
        "block": 20,
        "table_minute": 15
    },

    "RICAC": {
        "name": "La Ricachona",
        "start": "08:10",
        "end": "19:10",
        "block": 20,
        "table_minute": 15
    },

    "CAZAL": {
        "name": "Cazaloton",
        "start": "09:00",
        "end": "19:00",
        "block": 20
    },

    "R.ACT": {
        "name": "Ruleta Activa",
        "start": "09:00",
        "end": "19:00",
        "block": 20
    },

    "L.GATO": {
        "name": "Lotto Gato",
        "start": "09:00",
        "end": "19:00",
        "block": 20
    },

    "G.ITO": {
        "name": "Guacharito Millonario",
        "start": "08:30",
        "end": "19:30",
        "block": 50
    },

    "L.INT": {
        "name": "Lotto Inter",
        "start": "08:30",
        "end": "19:30",
        "block": 50
    },

    "GUACA": {
        "name": "Guaca Activa 37",
        "start": "08:30",
        "end": "19:30",
        "block": 50
    },

    "G.AZO": {
        "name": "Granjazo",
        "start": "09:30",
        "end": "20:30",
        "block": 50
    },

    "P.PLUS": {
        "name": "Panda Plus",
        "start": "09:30",
        "end": "19:30",
        "block": 50
    },

    "GATAZO": {
        "name": "Gatazo",
        "start": "09:40",
        "end": "19:40",
        "block": 50,
        "display_start": "09:30"
    },

    "M.GUAC": {
        "name": "Mega Guaca",
        "start": "07:30",
        "end": "19:30",
        "block": 50
    },
}

# ============================================================
# ORDEN DE TABLAS
# ============================================================

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

# ============================================================
# ESTADO
# ============================================================

state = {
    "sent_results": {},
    "tables": {},
    "last_pyramid_date": "",
    "last_scheduled": {},
    "last_individual": {},
}

# ============================================================
# CARGAR / GUARDAR ESTADO
# ============================================================

def load_state():

    global state

    try:

        with open(
            STATE_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            loaded = json.load(f)

        if isinstance(loaded, dict):
            state.update(loaded)

    except FileNotFoundError:
        pass

    except Exception as exc:
        log.warning(
            "No se pudo cargar estado: %s",
            exc
        )


def save_state():

    tmp = STATE_FILE + ".tmp"

    with state_lock:

        with open(
            tmp,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                state,
                f,
                ensure_ascii=False,
                indent=2
            )

        os.replace(
            tmp,
            STATE_FILE
        )


load_state()

# ============================================================
# UTILIDADES
# ============================================================

def now():
    return datetime.now(TZ)


def norm_text(value):

    return re.sub(
        r"\s+",
        " ",
        str(value or "")
    ).strip()


def normalize_name(value):

    value = str(value or "").upper()

    # ========================================================
    # CORRECCIÓN CLAVE:
    # Elimina la bandera de Venezuela 🇻🇪 y emojis antes
    # de comparar el nombre de la lotería.
    # ========================================================

    value = value.replace(
        "🇻🇪",
        " "
    )

    # Variaciones de Trío
    value = value.replace(
        "TRÍO",
        "TRIO"
    )

    value = re.sub(
        r"[^A-Z0-9ÁÉÍÓÚÜÑ ]",
        " ",
        value
    )

    return re.sub(
        r"\s+",
        " ",
        value
    ).strip()


# ============================================================
# ALIAS
# ============================================================

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

    # ========================================================
    # TRIO ACTIVO
    # Se contemplan las diferentes formas en que puede venir
    # desde la página.
    # ========================================================

    "TRIO ACTIVO": "TRIO",
    "TRÍO ACTIVO": "TRIO",
    "TRIO ACTIVO 🇻🇪": "TRIO",
    "TRÍO ACTIVO 🇻🇪": "TRIO",

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

    # Primero intenta coincidencia exacta.
    if normalized in ALIASES:
        return ALIASES[normalized]

    # ========================================================
    # CORRECCIÓN ESPECÍFICA PARA TRÍO ACTIVO 🇻🇪
    # ========================================================

    if (
        "TRIO ACTIVO" in normalized
        or "TRÍO ACTIVO" in normalized
    ):
        return "TRIO"

    return None


# ============================================================
# RESULTADOS
# ============================================================

def parse_number(raw):

    if raw is None:
        return None

    s = str(raw).strip().upper()

    if s in {
        "",
        "-",
        "...",
        "....",
        "FALSE",
        "NONE",
        "NULL"
    }:
        return None

    m = re.search(
        r"(?<!\d)(\d{1,2})(?!\d)",
        s
    )

    if not m:
        return None

    n = int(m.group(1))

    if 0 <= n <= 99:
        return n

    return None


def result_display(n):

    if n is None:
        return PENDING

    return (
        f"{n:02d}"
        f"{ANIMAL_EMOJI.get(n, '🎰')}"
    )


def parse_time_from_text(text):

    text = text.replace(
        ".",
        ":"
    )

    patterns = [

        r"\b([01]?\d):([0-5]\d)\s*(AM|PM)?\b",

        r"\b([01]?\d)\s*(AM|PM)\b",
    ]

    for pat in patterns:

        m = re.search(
            pat,
            text,
            re.I
        )

        if not m:
            continue

        hour = int(
            m.group(1)
        )

        if (
            len(m.groups()) >= 2
            and m.group(2).isdigit()
        ):
            minute = int(
                m.group(2)
            )
        else:
            minute = 0

        ampm = None

        if len(m.groups()) >= 3:
            ampm = m.group(3)

        elif (
            len(m.groups()) >= 2
            and m.group(2).isalpha()
        ):
            ampm = m.group(2)

        if ampm:

            ampm = ampm.upper()

            if (
                ampm == "PM"
                and hour < 12
            ):
                hour += 12

            if (
                ampm == "AM"
                and hour == 12
            ):
                hour = 0

        if (
            0 <= hour <= 23
            and 0 <= minute <= 59
        ):
            return hour, minute

    return None


def extract_candidates(text):

    text = norm_text(text)

    candidates = []

    # 08:00 ... 14
    for m in re.finditer(
        r"\b(\d{1,2}):(\d{2})\b.{0,80}?\b(\d{1,2})\b",
        text
    ):

        hh = int(m.group(1))
        mm = int(m.group(2))
        num = int(m.group(3))

        if (
            0 <= hh <= 23
            and 0 <= mm <= 59
            and 0 <= num <= 99
        ):

            candidates.append(
                (hh, mm, num)
            )

    # 08:00 14
    for m in re.finditer(
        r"\b(\d{1,2}):(\d{2})\s+(\d{1,2})\b",
        text
    ):

        candidates.append(
            (
                int(m.group(1)),
                int(m.group(2)),
                int(m.group(3))
            )
        )

    # 08:00 -> 14
    for m in re.finditer(
        r"\b(\d{1,2}):(\d{2})\s*(?:-|:|→|>)\s*(\d{1,2})\b",
        text
    ):

        candidates.append(
            (
                int(m.group(1)),
                int(m.group(2)),
                int(m.group(3))
            )
        )

    seen = set()
    out = []

    for item in candidates:

        if item not in seen:

            seen.add(item)
            out.append(item)

    return out


# ============================================================
# HTTP
# ============================================================

def fetch(
    url,
    timeout=15
):

    response = SESSION.get(
        url,
        timeout=timeout,
        allow_redirects=True
    )

    response.raise_for_status()

    return response.text


# ============================================================
# EXTRACCION DE FUENTE
# ============================================================

def extract_source_results(
    url,
    lottery_code=None
):

    try:

        html = fetch(url)

    except Exception as exc:

        log.warning(
            "Fuente falló %s: %s",
            url,
            exc
        )

        return {}

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    results = {}

    # ========================================================
    # TABLAS HTML
    # ========================================================

    for tr in soup.find_all("tr"):

        cells = [

            norm_text(
                c.get_text(
                    " ",
                    strip=True
                )
            )

            for c in tr.find_all(
                ["td", "th"]
            )
        ]

        if len(cells) < 2:
            continue

        row = " ".join(cells)

        for hh, mm, num in extract_candidates(row):

            results[
                f"{hh:02d}:{mm:02d}"
            ] = num

    # ========================================================
    # CARDS
    # ========================================================

    for el in soup.find_all(
        [
            "article",
            "div",
            "li",
            "section"
        ]
    ):

        txt = norm_text(
            el.get_text(
                " ",
                strip=True
            )
        )

        if len(txt) > 300:
            continue

        for hh, mm, num in extract_candidates(txt):

            results[
                f"{hh:02d}:{mm:02d}"
            ] = num

    # ========================================================
    # TEXTO COMPLETO
    # ========================================================

    text = soup.get_text(
        " ",
        strip=True
    )

    for hh, mm, num in extract_candidates(text):

        results[
            f"{hh:02d}:{mm:02d}"
        ] = num

    return results


# ============================================================
# WINBIG
# ============================================================

def extract_winbig_for_code(code):

    try:

        html = fetch(
            WINBIG_URL
        )

    except Exception as exc:

        log.warning(
            "Winbig falló: %s",
            exc
        )

        return {}

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    target_name = normalize_name(
        LOTTERIES[code]["name"]
    )

    results = {}

    for el in soup.find_all(
        [
            "article",
            "div",
            "section",
            "li",
            "tr"
        ]
    ):

        txt = norm_text(
            el.get_text(
                " ",
                strip=True
            )
        )

        normalized = normalize_name(
            txt
        )

        if (
            target_name
            and target_name not in normalized
        ):
            continue

        for hh, mm, num in extract_candidates(txt):

            results[
                f"{hh:02d}:{mm:02d}"
            ] = num

    return results


# ============================================================
# URLS
# ============================================================

def source_urls(code):

    urls = []

    if code in OFFICIAL:

        urls.append(
            (
                "official",
                OFFICIAL[code]
            )
        )

    for u in ALTERNATIVE.get(
        code,
        []
    ):

        urls.append(
            (
                "alternative",
                u
            )
        )

    if (
        code not in OFFICIAL
        or OFFICIAL.get(code) == WINBIG_URL
    ):

        urls.append(
            (
                "winbig",
                WINBIG_URL
            )
        )

    elif code not in ALTERNATIVE:

        urls.append(
            (
                "winbig",
                WINBIG_URL
            )
        )

    return urls


# ============================================================
# COMBINAR RESULTADOS
# ============================================================

def merge_source_results(code):

    by_source = {}

    urls = source_urls(
        code
    )

    for label, url in urls:

        if url == WINBIG_URL:

            data = extract_winbig_for_code(
                code
            )

            if not data:

                data = extract_source_results(
                    url,
                    code
                )

        else:

            data = extract_source_results(
                url,
                code
            )

        by_source[label] = data

    all_times = set()

    for data in by_source.values():

        all_times.update(
            data.keys()
        )

    merged = {}

    for tm in sorted(all_times):

        vals = {
            label: data[tm]

            for label, data
            in by_source.items()

            if tm in data
        }

        if not vals:
            continue

        if len(vals) == 1:

            only_label, only_val = next(
                iter(vals.items())
            )

            if (
                only_label == "alternative"
                and "official" in by_source
            ):
                continue

            merged[tm] = only_val

            continue

        unique = set(
            vals.values()
        )

        if len(unique) == 1:

            merged[tm] = next(
                iter(unique)
            )

            continue

        if "official" in vals:

            merged[tm] = vals[
                "official"
            ]

    return merged, by_source


# ============================================================
# HORARIOS
# ============================================================

def lottery_is_active_at(
    code,
    hhmm
):

    cfg = LOTTERIES[code]

    h, m = map(
        int,
        hhmm.split(":")
    )

    minutes = (
        h * 60
        + m
    )

    if "windows" in cfg:

        for start, end in cfg["windows"]:

            sh, sm = map(
                int,
                start.split(":")
            )

            eh, em = map(
                int,
                end.split(":")
            )

            if (
                sh * 60 + sm
                <= minutes
                <= eh * 60 + em
            ):
                return True

        return False

    sh, sm = map(
        int,
        cfg["start"].split(":")
    )

    eh, em = map(
        int,
        cfg["end"].split(":")
    )

    return (
        sh * 60 + sm
        <= minutes
        <= eh * 60 + em
    )


def scheduled_times(
    code,
    block
):

    cfg = LOTTERIES[code]

    start = cfg.get(
        "display_start",
        cfg.get("start")
    )

    end = cfg["end"]

    sh, sm = map(
        int,
        start.split(":")
    )

    eh, em = map(
        int,
        end.split(":")
    )

    times = []

    cur = (
        sh * 60
        + sm
    )

    endm = (
        eh * 60
        + em
    )

    while cur <= endm:

        hhmm = (
            f"{cur // 60:02d}:"
            f"{cur % 60:02d}"
        )

        times.append(
            hhmm
        )

        cur += 60

    return times


def display_time(hhmm):

    h, m = map(
        int,
        hhmm.split(":")
    )

    suffix = (
        "AM"
        if h < 12
        else "PM"
    )

    hour = h % 12 or 12

    return (
        f"{hour:02d}:"
        f"{m:02d} "
        f"{suffix}"
    )


# ============================================================
# ACTUALIZAR RESULTADOS
# ============================================================

def update_all_results():

    today = now().strftime(
        "%Y-%m-%d"
    )

    all_data = {}

    for code in LOTTERIES:

        try:

            merged, sources = merge_source_results(
                code
            )

            all_data[code] = merged

            state[
                "tables"
            ].setdefault(
                today,
                {}
            ).setdefault(
                code,
                {}
            )

            for tm, n in merged.items():

                state[
                    "tables"
                ][today][code][tm] = n

        except Exception as exc:

            log.exception(
                "Error actualizando %s: %s",
                code,
                exc
            )

    save_state()

    return all_data


# ============================================================
# TABLAS
# ============================================================

def table_header(codes):

    return (
        " HORA🎰"
        + "🪙".join(codes)
    )


def table_cell(
    code,
    hhmm,
    results
):

    if (
        not lottery_is_active_at(
            code,
            hhmm
        )
    ):

        return NO_DRAW

    n = results.get(
        hhmm
    )

    return result_display(
        n
    )


def build_table(
    block,
    refresh=True
):

    today = now().strftime(
        "%Y-%m-%d"
    )

    if refresh:

        update_all_results()

    lines = [

        BANNER,

        "",

        HEADERS[block],

        "➖" * 12
    ]

    for group in BLOCKS[block]:

        lines.append(
            table_header(
                group
            )
        )

        all_times = set()

        for code in group:

            all_times.update(
                scheduled_times(
                    code,
                    block
                )
            )

        current_minutes = (
            now().hour * 60
            + now().minute
        )

        visible = []

        for tm in sorted(
            all_times
        ):

            h, m = map(
                int,
                tm.split(":")
            )

            if (
                h * 60 + m
                <= current_minutes
            ):

                visible.append(
                    tm
                )

        if (
            block in (
                10,
                20,
                50
            )
            and current_minutes
            < 8 * 60 + 10
        ):

            visible = []

        for tm in visible:

            row = [
                f"⏰{display_time(tm)}"
            ]

            for code in group:

                results = state[
                    "tables"
                ].get(
                    today,
                    {}
                ).get(
                    code,
                    {}
                )

                row.append(
                    table_cell(
                        code,
                        tm,
                        results
                    )
                )

            lines.append(
                "  ".join(row)
            )

        lines.append("")

    lines.append(
        "MUCHA SUERTE EN SUS JUGADAS"
    )

    return "\n".join(
        lines
    )


# ============================================================
# TELEGRAM
# ============================================================

def send_message(text):

    try:

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


def send_individual_result(
    code,
    tm,
    number
):

    key = (
        f"{now().strftime('%Y-%m-%d')}:"
        f"{code}:"
        f"{tm}:"
        f"{number}"
    )

    if state[
        "sent_results"
    ].get(key):

        return False

    cfg = LOTTERIES[
        code
    ]

    text = (

        f"{BANNER}\n\n"

        f"🎰 <b>"
        f"{cfg['name'].upper()}"
        f"</b>\n"

        f"⏰ <b>"
        f"{display_time(tm)}"
        f"</b>\n"

        f"🎯 <b>Resultado: "
        f"{number:02d}"
        f"{ANIMAL_EMOJI.get(number, '🎰')}"
        f"</b>"
    )

    msg = send_message(
        text
    )

    if msg:

        state[
            "sent_results"
        ][key] = True

        save_state()

        return True

    return False


# ============================================================
# PIRAMIDE
# ============================================================

def pyramid_for_date(dt):

    seed = [
        int(x)
        for x in dt.strftime(
            "%d%m"
        )
    ]

    digits = (
        seed
        + [
            int(x)
            for x in dt.strftime(
                "%Y"
            )[:2]
        ]
    )

    top = digits[:8]

    rows = [
        top
    ]

    current = top

    while len(current) > 1:

        nxt = [

            (
                current[i]
                + current[i + 1]
            ) % 10

            for i in range(
                len(current) - 1
            )
        ]

        rows.append(
            nxt
        )

        current = nxt

    candidates = []

    for row in rows:

        for i in range(
            0,
            len(row) - 1,
            2
        ):

            pair = int(
                f"{row[i]}"
                f"{row[i + 1]}"
            )

            candidates.append(
                pair
            )

    valid = []

    for x in candidates:

        if x == 0:

            valid.append(
                "00"
            )

        elif 1 <= x <= 36:

            valid.append(
                f"{x:02d}"
            )

    flat_sum = sum(
        top
    )

    for x in [

        flat_sum,

        sum(
            rows[-1]
        ),

        sum(
            sum(r)
            for r in rows
        ),

        abs(
            top[0]
            - top[-1]
        ) * 3,

        (
            top[0]
            + top[-1]
        ) * 2,

        (
            rows[-1][0]
            if rows[-1]
            else 0
        ),

    ]:

        x = x % 37

        if x == 0:

            valid.append(
                "00"
            )

        else:

            valid.append(
                f"{x:02d}"
            )

    out = []

    for x in valid:

        if x not in out:

            out.append(
                x
            )

        if len(out) == 6:

            break

    while len(out) < 6:

        out.append(
            "00"
            if len(out) % 2 == 0
            else "01"
        )

    return rows, out[:6]


def pyramid_text():

    dt = now()

    rows, keys = pyramid_for_date(
        dt
    )

    lines = [

        "<b>🔥 PIRÁMIDE NUMÉRICA DEL DÍA 🔥</b>",

        ""
    ]

    for row in rows:

        lines.append(

            "  "
            * (
                len(rows)
                - len(row)
            )
            + " ".join(
                str(x)
                for x in row
            )
        )

    lines += [

        "",

        "🔥 <b>DATOS CLAVES PARA HOY:</b>",

        f"📌 {keys[0]}-{keys[1]}-{keys[2]}",

        f"📌 {keys[3]}-{keys[4]}-{keys[5]}",
    ]

    return "\n".join(
        lines
    )


# ============================================================
# SCHEDULER
# ============================================================

def scheduler_loop():

    log.info(
        "Scheduler iniciado. Destino activo: %s",
        ACTIVE_CHANNEL_ID
    )

    while True:

        try:

            current = now()

            minute = current.minute

            update_all_results()

            # -----------------------------------------------
            # PIRAMIDE
            # -----------------------------------------------

            if (
                current.hour == 7
                and minute == 0
            ):

                key = (
                    f"pyramid:"
                    f"{current.strftime('%Y-%m-%d')}"
                )

                if not state[
                    "last_scheduled"
                ].get(key):

                    send_message(
                        pyramid_text()
                    )

                    state[
                        "last_scheduled"
                    ][key] = True

                    save_state()

            # -----------------------------------------------
            # TAQUILLA
            # -----------------------------------------------

            if (
                7 <= current.hour <= 18
                and minute == 10
            ):

                key = (

                    f"taquilla:"
                    f"{current.strftime('%Y-%m-%d')}:"
                    f"{current.hour}"
                )

                if not state[
                    "last_scheduled"
                ].get(key):

                    send_message(

                        f"{BANNER}\n\n"

                        f"📢 <b>TAQUILLA ACTIVA</b>\n"

                        f"⏰ "
                        f"{current.strftime('%I:%M %p')}\n"

                        f"Envía tus jugadas y participa."
                    )

                    state[
                        "last_scheduled"
                    ][key] = True

                    save_state()

            # -----------------------------------------------
            # TABLAS
            # -----------------------------------------------

            for block, target_minute in [

                (10, 10),

                (20, 20),

                (50, 50)

            ]:

                if minute == target_minute:

                    key = (

                        f"table:"
                        f"{current.strftime('%Y-%m-%d')}:"
                        f"{block}:"
                        f"{current.hour}"
                    )

                    if not state[
                        "last_scheduled"
                    ].get(key):

                        send_message(
                            build_table(
                                block,
                                refresh=True
                            )
                        )

                        state[
                            "last_scheduled"
                        ][key] = True

                        save_state()

            # -----------------------------------------------
            # RESULTADOS INDIVIDUALES
            # -----------------------------------------------

            today = current.strftime(
                "%Y-%m-%d"
            )

            current_total = (
                current.hour * 60
                + current.minute
            )

            for code in LOTTERIES:

                data = state[
                    "tables"
                ].get(
                    today,
                    {}
                ).get(
                    code,
                    {}
                )

                for tm, number in sorted(
                    data.items()
                ):

                    h, m = map(
                        int,
                        tm.split(":")
                    )

                    if (
                        h * 60 + m
                        <= current_total
                    ):

                        send_individual_result(
                            code,
                            tm,
                            number
                        )

            time.sleep(
                30
            )

        except Exception as exc:

            log.exception(
                "Error en scheduler: %s",
                exc
            )

            time.sleep(
                30
            )


# ============================================================
# ENDPOINTS
# ============================================================

@app.get("/")
def root():

    return jsonify({

        "status": "ok",

        "bot":
            "AG HAROLD JOSE BOT",

        "active_channel":
            ACTIVE_CHANNEL_ID,

        "main_reference":
            MAIN_CHANNEL_REFERENCE,

        "timezone":
            TIMEZONE,

        "trio_activo":
            "TRIO ACTIVO 🇻🇪",

    })


@app.get("/health")
def health():

    return jsonify({

        "status":
            "healthy",

        "time":
            now().isoformat()

    })


@app.get("/test/piramide")
def test_piramide():

    return app.response_class(

        pyramid_text(),

        mimetype=
            "text/plain; charset=utf-8"
    )


@app.get("/test/table/10")
def test_table_10():

    return app.response_class(

        build_table(10),

        mimetype=
            "text/plain; charset=utf-8"
    )


@app.get("/test/table/20")
def test_table_20():

    return app.response_class(

        build_table(20),

        mimetype=
            "text/plain; charset=utf-8"
    )


@app.get("/test/table/50")
def test_table_50():

    return app.response_class(

        build_table(50),

        mimetype=
            "text/plain; charset=utf-8"
    )


@app.get("/test/source/<code>")
def test_source(code):

    code = code.upper()

    if code not in LOTTERIES:

        return jsonify({

            "error":
                "Código no registrado",

            "valid":
                list(LOTTERIES)

        }), 404

    merged, sources = merge_source_results(
        code
    )

    return jsonify({

        "code":
            code,

        "name":
            LOTTERIES[code]["name"],

        "merged":
            merged,

        "sources":
            sources,

        "urls":
            source_urls(code)

    })


@app.get("/test/send/table/<int:block>")
def test_send_table(block):

    if block not in (
        10,
        20,
        50
    ):

        return jsonify({

            "error":
                "Bloque debe ser 10, 20 o 50"

        }), 400

    msg = send_message(

        build_table(
            block
        )
    )

    return jsonify({

        "sent":
            bool(msg),

        "channel":
            ACTIVE_CHANNEL_ID

    })


@app.get("/test/send/piramide")
def test_send_pyramid():

    msg = send_message(
        pyramid_text()
    )

    return jsonify({

        "sent":
            bool(msg),

        "channel":
            ACTIVE_CHANNEL_ID

    })


# ============================================================
# COMANDOS TELEGRAM
# ============================================================

@bot.message_handler(
    commands=["start"]
)
def cmd_start(message):

    bot.reply_to(

        message,

        "🤖 <b>AG HAROLD JOSE BOT</b>\n"

        "Bot activo.\n"

        f"Canal de prueba: "
        f"{ACTIVE_CHANNEL_ID}\n"

        "Usa /id para consultar "
        "el ID del chat."

    )


@bot.message_handler(
    commands=["id"]
)
def cmd_id(message):

    bot.reply_to(

        message,

        f"🆔 Chat ID: "
        f"<code>{message.chat.id}</code>"

    )


@bot.message_handler(
    commands=["test10"]
)
def cmd_test10(message):

    bot.send_message(

        message.chat.id,

        build_table(
            10
        ),

        disable_web_page_preview=True

    )


@bot.message_handler(
    commands=["test20"]
)
def cmd_test20(message):

    bot.send_message(

        message.chat.id,

        build_table(
            20
        ),

        disable_web_page_preview=True

    )


@bot.message_handler(
    commands=["test50"]
)
def cmd_test50(message):

    bot.send_message(

        message.chat.id,

        build_table(
            50
        ),

        disable_web_page_preview=True

    )


@bot.message_handler(
    commands=["piramide"]
)
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

        threaded=True

    )


# ============================================================
# MAIN
# ============================================================

def main():

    log.info(
        "Iniciando AG HAROLD JOSE BOT"
    )

    log.info(
        "Canal activo: %s",
        ACTIVE_CHANNEL_ID
    )

    log.info(
        "Canal principal referencia: %s",
        MAIN_CHANNEL_REFERENCE
    )

    log.info(
        "TRIO ACTIVO 🇻🇪 integrado correctamente"
    )

    threading.Thread(

        target=run_flask,

        daemon=True

    ).start()

    threading.Thread(

        target=scheduler_loop,

        daemon=True

    ).start()

    while True:

        try:

            bot.infinity_polling(

                timeout=30,

                long_polling_timeout=30,

                allowed_updates=[
                    "message",
                    "channel_post"
                ]

            )

        except Exception as exc:

            log.exception(

                "Polling detenido: %s",

                exc

            )

            time.sleep(
                10
            )


if __name__ == "__main__":

    main()
