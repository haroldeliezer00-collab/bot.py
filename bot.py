import os
import json
import sqlite3
import logging
import re
import time
import urllib.request
import urllib.parse
import urllib.error
import threading
import datetime
from typing import Optional
from zoneinfo import ZoneInfo
from flask import Flask, request, jsonify

# =========================================================
# CONFIGURACION GENERAL Y ZONA HORARIA VENEZUELA
# =========================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("BotHaroldJose")

TZ_VE = ZoneInfo("America/Caracas")

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8510085156:AAGY9o4bP4V_6kR4g_M5X-r0N7y0w8p5E6o").strip()
CANAL_ID = os.environ.get("CANAL_ID", "@resultadosagharoldjose").strip()
WORKER_API_URL = os.environ.get("WORKER_API_URL", "https://api-resultados-harold.agharoldjose.workers.dev").strip()
TELEGRAM_PROXY_URL = os.environ.get("TELEGRAM_PROXY_URL", "https://telegram-harold.criptoanubis.workers.dev").strip()
WHATSAPP_URL = os.environ.get("WHATSAPP_URL", "https://wa.me/584124489363?text=Hola%20Agencia%20Harold%20Jos%C3%A9,%20quiero%20jugar").strip()
DB_PATH = os.environ.get("DB_PATH", "resultados_harold.db").strip()

# Las 9 loterias comerciales para el Radar de Atraccion en vivo
LOTERIAS_RADAR_COMERCIAL = {
    "LOTTO ACTIVO",
    "LA GRANJITA",
    "GUACA ACTIVA",
    "MEGA GUACA",
    "GUACHARO ACTIVO",
    "EL GUACHARITO MILLONARIO",
    "SELVA PLUS",
    "RULETA ACTIVA",
    "GRANJA MILLONARIA",
}

# =========================================================
# DICCIONARIO DE EMOJIS DE ANIMALITOS Y ALTERNATIVOS
# =========================================================
EMOJIS_ANIMALES = {
    # 38 tradicionales
    "DELFIN": "🐬", "DELFÍN": "🐬",
    "BALLENA": "🐳",
    "CARNERO": "🐏",
    "TORO": "🐂",
    "CIEMPIES": "🐛", "CIEMPIÉS": "🐛",
    "ALACRAN": "🦂", "ALACRÁN": "🦂",
    "LEON": "🦁", "LEÓN": "🦁",
    "RANA": "🐸",
    "PERICO": "🦜",
    "RATON": "🐭", "RATÓN": "🐭",
    "AGUILA": "🦅", "ÁGUILA": "🦅",
    "TIGRE": "🐯",
    "GATO": "🐱",
    "CABALLO": "🐴",
    "MONO": "🐵",
    "PALOMA": "🕊️",
    "ZORRO": "🦊",
    "OSO": "🐻",
    "PAVO": "🦃",
    "BURRO": "🫏",
    "CHIVO": "🐐",
    "COCHINO": "🐷",
    "GALLO": "🐓",
    "CAMELLO": "🐪",
    "CEBRA": "🦓",
    "IGUANA": "🦎",
    "GALLINA": "🐔",
    "VACA": "🐄",
    "PERRO": "🐶",
    "ZAMURO": "🦅",
    "ELEFANTE": "🐘",
    "CAIMAN": "🐊", "CAIMÁN": "🐊",
    "LAPA": "🐹",
    "ARDILLA": "🐿️",
    "PESCADO": "🐟",
    "VENADO": "🦌",
    "JIRAFA": "🦒",
    "CULEBRA": "🐍",

    # Extendidos (Monje Millonario, Mega Animal, Granjita Plus, Fruitagana, etc.)
    "CONEJO": "🐰",
    "TORTUGA": "🐢",
    "PINGUINO": "🐧", "PINGÜINO": "🐧",
    "TIBURON": "🦈", "TIBURÓN": "🦈",
    "PULPO": "🐙",
    "CANGREJO": "🦀",
    "LOBO": "🐺",
    "BUHO": "🦉", "BÚHO": "🦉",
    "RINOCERONTE": "🦏",
    "HIPOPOTAMO": "🦛", "HIPOPÓTAMO": "🦛",
    "COCODRILO": "🐊",
    "PANTERA": "🐆",
    "LEOPARDO": "🐆",
    "PANDA": "🐼",
    "KOALA": "🐨",
    "CANGURO": "🦘",
    "FLAMENCO": "🦩",
    "CISNE": "🦢",
    "PATO": "🦆",
    "ABEJA": "🐝",
    "MARIPOSA": "🦋",
    "HORMIGA": "🐜",
    "ARANA": "🕷️", "ARAÑA": "🕷️",
    "CARACOL": "🐌",
    "CAMARON": "🦐", "CAMARÓN": "🦐",
    "LANGOSTA": "🦞",
    "CALAMAR": "🦑",
    "FOCA": "🦭",
    "NUTRIA": "🦦",
    "CASTOR": "🦫",
    "ERIZO": "🦔",
    "MURCIELAGO": "🦇", "MURCIÉLAGO": "🦇",
    "GORILA": "🦍",
    "ORANGUTAN": "🦧", "ORANGUTÁN": "🦧",
    "MAPACHE": "🦝",
    "ZORRILLO": "🦨",
    "TEJON": "🦡", "TEJÓN": "🦡",
    "LLAMA": "🦙",
    "ALPACA": "🦙",
    "BUFALO": "🐃", "BÚFALO": "🐃",
    "BUEY": "🐂",
    "CERDO": "🐖",
    "OVEJA": "🐑",
    "CABRA": "🐐",
    "POLLO": "🐤",
    "POLLITO": "🐥",
    "PAVO REAL": "🦚",
    "LORO": "🦜",
    "GUACAMAYA": "🦜",
    "TUCAN": "🦜", "TUCÁN": "🦜",
    "HALCON": "🦅", "HALCÓN": "🦅",
    "GAVILAN": "🦅", "GAVILÁN": "🦅",
    "CONDOR": "🦅", "CÓNDOR": "🦅",
    "AVESTRUZ": "🦤",
    "PELICANO": "🦤", "PELÍCANO": "🦤",
    "GAVIOTA": "🕊️",
    "COLIBRI": "🐦", "COLIBRÍ": "🐦",
    "CANARIO": "🐤",
    "SAPO": "🐸",
    "CAMALEON": "🦎", "CAMALEÓN": "🦎",
    "LAGARTO": "🦎",
    "SERPIENTE": "🐍",
    "VIBORA": "🐍", "VÍBORA": "🐍",
    "COBRA": "🐍",
    "DRAGON": "🐉", "DRAGÓN": "🐉",
    "DINOSAURIO": "🦖",
    "T-REX": "🦖",
    "UNICORNIO": "🦄",
    "PEGASO": "🦄",
    "ESCORPION": "🦂", "ESCORPIÓN": "🦂",
    "TARANTULA": "🕷️", "TARÁNTULA": "🕷️",
    "MARIQUITA": "🐞",
    "GRILLO": "🦗",
    "SALTAMONTES": "🦗",
    "ESCARABAJO": "🪲",
    "CUCARACHA": "🪳",
    "MOSCA": "🪰",
    "MOSQUITO": "🦟",
    "GUSANO": "🪱",
    "ORUGA": "🐛",
    "MEDUSA": "🪼",
    "ESTRELLA DE MAR": "⭐",
    "CABALLITO DE MAR": "🐴",
    "PEZ": "🐟",
    "PEZ PAYASO": "🐠",
    "PEZ GLOBO": "🐡",
    "ORCA": "🐋",
    "MANATI": "🦭", "MANATÍ": "🦭",
    "MORSA": "🦭",
    "OSO POLAR": "🐻‍❄️",
    "OSO PARDO": "🐻",
    "PUMA": "🐆",
    "JAGUAR": "🐆",
    "GUEPARDO": "🐆",
    "LINCE": "🐈",
    "HIENA": "🐺",
    "CHACAL": "🐺",
    "COYOTE": "🐺",
    "PERRO CALIENTE": "🌭",
    "HAMBURGUESA": "🍔",
    "PIZZA": "🍕",
    "MANZANA": "🍎",
    "PERA": "🍐",
    "CAMBUR": "🍌",
    "BANANA": "🍌",
    "PLATANO": "🍌", "PLÁTANO": "🍌",
    "PATILLA": "🍉",
    "SANDIA": "🍉", "SANDÍA": "🍉",
    "UVA": "🍇",
    "UVAS": "🍇",
    "FRESA": "🍓",
    "PINA": "🍍", "PIÑA": "🍍",
    "MANGO": "🥭",
    "NARANJA": "🍊",
    "MANDARINA": "🍊",
    "LIMON": "🍋", "LIMÓN": "🍋",
    "CEREZA": "🍒",
    "CEREZAS": "🍒",
    "DURAZNO": "🍑",
    "MELOCOTON": "🍑", "MELOCOTÓN": "🍑",
    "COCO": "🥥",
    "KIWI": "🥝",
    "AGUACATE": "🥑",
    "TOMATE": "🍅",
    "MAIZ": "🌽", "MAÍZ": "🌽",
    "ZANAHORIA": "🥕",
    "PAPA": "🥔",
    "CEBOLLA": "🧅",
    "AJO": "🧄",
    "BROCOLI": "🥦", "BRÓCOLI": "🥦",
    "LECHUGA": "🥬",
    "PEPINO": "🥒",
    "PIMENTON": "🫑", "PIMENTÓN": "🫑",
    "AJI": "🌶️", "AJÍ": "🌶️",
    "BERENJENA": "🍆",
    "HONGO": "🍄",
    "CHAMPIÑON": "🍄",
    "MANI": "🥜", "MANÍ": "🥜",
    "CASTANA": "🌰", "CASTAÑA": "🌰",
    "PAN": "🍞",
    "QUESO": "🧀",
    "HUEVO": "🥚",
    "HELADO": "🍨",
    "TORTA": "🎂",
    "PASTEL": "🍰",
    "CARAMELO": "🍬",
    "CHOCOLATE": "🍫",
    "DONA": "🍩",
    "GALLETA": "🍪",
    "CAFE": "☕", "CAFÉ": "☕",
    "CERVEZA": "🍺",
    "VINO": "🍷",
    "CORONA": "👑",
    "DIAMANTE": "💎",
    "TREBOL": "🍀", "TRÉBOL": "🍀",
    "HERRADURA": "🧲",
    "CAMPANA": "🔔",
    "ESTRELLA": "⭐",
    "SOL": "☀️",
    "LUNA": "🌙",
    "RAYO": "⚡",
    "FUEGO": "🔥",
    "CORAZON": "❤️", "CORAZÓN": "❤️",
    "DINERO": "💰",
    "BOLSA": "💰",
    "MONEDA": "🪙",
    "DADO": "🎲",
    "DADOS": "🎲",
    "CARTA": "🃏",
    "JOKER": "🃏",
    "COMODIN": "🃏", "COMODÍN": "🃏",
    "REY": "🤴",
    "REINA": "👸",
    "PRINCIPE": "🤴", "PRÍNCIPE": "🤴",
    "PRINCESA": "👸",
    "MONJE": "🧙‍♂️",
    "MAGO": "🧙‍♂️",
    "BRUJA": "🧙‍♀️",
    "ANGEL": "👼", "ÁNGEL": "👼",
    "DIABLO": "😈",
    "FANTASMA": "👻",
    "CALAVERA": "💀",
    "ROBOT": "🤖",
    "EXTRATERRESTRE": "👽",
    "ALIEN": "👽",
    "COHETE": "🚀",
    "AVION": "✈️", "AVIÓN": "✈️",
    "BARCO": "🚢",
    "CARRO": "🚗",
    "MOTO": "🏍️",
    "BICICLETA": "🚲",
    "TREN": "🚂",
    "CASA": "🏠",
    "CASTILLO": "🏰",
    "RELOJ": "⌚",
    "LLAVE": "🔑",
    "CANDADO": "🔒",
    "ANILLO": "💍",
    "SOMBRERO": "🎩",
    "ZAPATO": "👟",
    "BALON": "⚽", "BALÓN": "⚽",
    "PELOTA": "⚾",
    "GUITARRA": "🎸",
    "TAMBOR": "🥁",
    "MICROFONO": "🎤", "MICRÓFONO": "🎤",
    "CAMARA": "📷", "CÁMARA": "📷",
    "TELEFONO": "📱", "TELÉFONO": "📱",
    "COMPUTADORA": "💻",
    "LIBRO": "📚",
    "LAPIZ": "✏️", "LÁPIZ": "✏️",
    "TIJERA": "✂️",
    "MARTILLO": "🔨",
    "HACHA": "🪓",
    "ESPADA": "⚔️",
    "ESCUDO": "🛡️",
    "BANDERA": "🏁",
    "TROFEO": "🏆",
    "MEDALLA": "🏅",
}


def obtener_emoji_animal(animal: str, loteria: str = "") -> str:
    if not animal:
        return "💮" if "FRUIT" in loteria.upper() else "🐾"
    ani_clean = re.sub(r"[^A-ZÁÉÍÓÚÑ0-9\s-]", "", animal.upper()).strip()
    if ani_clean in EMOJIS_ANIMALES:
        return EMOJIS_ANIMALES[ani_clean].strip()
    for k, v in EMOJIS_ANIMALES.items():
        if len(k) >= 4 and k in ani_clean:
            return v.strip()
    if "FRUIT" in loteria.upper() or "FRUTA" in loteria.upper():
        return "💮"
    return "🐾"


# =========================================================
# MAPA DE ABREVIATURAS Y COLUMNAS PARA TABLAS RESUMEN
# =========================================================
ABREVIATURAS_TABLA = {
    "LOTTO ACTIVO": "L.ACT",
    "LA GRANJITA": "GRJ",
    "GUACHARO ACTIVO": "GCH",
    "EL GUACHARITO MILLONARIO": "GCHT",
    "SELVA PLUS": "SLV",
    "GUACA ACTIVA": "GCA",
    "MEGA GUACA": "MG.G",
    "RULETA ACTIVA": "R.ACT",
    "GRANJA MILLONARIA": "G.MIL",
    "LOTTO CHAIMA": "CHM",
    "CONDOR GANA": "CND",
    "RULETA ROYAL": "RYL",
    "CENTENA ANIMAL": "CNT",
    "CENTENA PLUS": "CNT+",
    "CAZALOTON": "CZL",
    "CHANCE ANIMAL": "CHN.A",
    "LA RICACHONA": "RCH",
    "TROPIGANA": "TRP",
    "FRUITAGANA": "FRUI",
    "GRANJITA PLUS": "G.PLUS",
    "GRANJAZO": "GRZ",
    "PANDA PLUS": "PND",
    "MEGA ANIMAL": "MG.A",
    "MONJE MILLONARIO": "MONJE",
    "LOTTO GATO": "L.GAT",
    "GATAZO": "GTZ",
    "ZOOLOGICO ACTIVO": "ZOO",
    "LOTOANIMALITO": "L.ANI",
    "LOTTO PANTERA": "PNT",
    "LOTTO REAL": "L.RL",
    "LOTTO LA QUINTA": "L.5TA",
    "RULETON PERU": "R.PER",
    "LOTTOMAX": "L.MAX",
    "RULETON COLOMBIA": "R.COL",
    "RULETON VENEZUELA": "R.VEN",
    "CALAMAR A": "CAL.A",
    "CALAMAR B": "CAL.B",
    "LOTTO REY": "L.REY",
    "LOTTO RD": "L.RD",
}

HORAS_ESTANDAR_TABLA = [
    "8:00 AM", "8:15 AM", "8:30 AM", "9:00 AM", "10:00 AM", "11:00 AM",
    "12:00 PM", "1:00 PM", "2:00 PM", "3:00 PM", "4:00 PM", "5:00 PM",
    "6:00 PM", "7:00 PM", "8:00 PM"
]


# =========================================================
# BASE DE DATOS SQLITE PERSISTENTE
# =========================================================
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS resultados_publicados (
            fecha TEXT,
            loteria TEXT,
            hora TEXT,
            numero TEXT,
            animal TEXT,
            PRIMARY KEY (fecha, loteria, hora)
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS config_bot (
            clave TEXT PRIMARY KEY,
            valor TEXT
        )
    """)
    conn.commit()
    conn.close()


def get_config(clave: str, default: str = "") -> str:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT valor FROM config_bot WHERE clave = ?", (clave,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else default


def set_config(clave: str, valor: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO config_bot (clave, valor) VALUES (?, ?)", (clave, valor))
    conn.commit()
    conn.close()


def ya_fue_publicado(fecha: str, loteria: str, hora: str) -> bool:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "SELECT 1 FROM resultados_publicados WHERE fecha = ? AND loteria = ? AND hora = ?",
        (fecha, loteria, hora),
    )
    row = c.fetchone()
    conn.close()
    return row is not None


def guardar_resultado_db(fecha: str, loteria: str, hora: str, numero: str, animal: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT OR REPLACE INTO resultados_publicados (fecha, loteria, hora, numero, animal) VALUES (?, ?, ?, ?, ?)",
        (fecha, loteria, hora, numero, animal),
    )
    conn.commit()
    conn.close()


def obtener_resultados_dia_db(fecha: str) -> dict:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "SELECT loteria, hora, numero, animal FROM resultados_publicados WHERE fecha = ?",
        (fecha,),
    )
    rows = c.fetchall()
    conn.close()
    data = {}
    for lot, hr, num, ani in rows:
        data.setdefault(lot, {})[hr] = {"numero": num, "animal": ani}
    return data


# =========================================================
# COMUNICACION CON TELEGRAM (VIA PUENTE CLOUDFLARE WORKER)
# =========================================================
def telegram_api_call(method: str, payload: dict) -> Optional[dict]:
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN no configurado.")
        return None

    base = TELEGRAM_PROXY_URL.rstrip("/") if TELEGRAM_PROXY_URL else "https://api.telegram.org"
    url = f"{base}/bot{BOT_TOKEN}/{method}"

    data_bytes = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data_bytes,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "AgenciaHaroldJoseBot/2.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode("utf-8", errors="ignore")
            return json.loads(raw)
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="ignore")
        logger.error(f"Telegram HTTP {e.code} en {method}: {err_body}")
        return None
    except Exception as e:
        logger.error(f"Error de red en Telegram ({method}): {e}")
        return None


def enviar_mensaje_canal(texto: str, incluir_boton_ws: bool = True) -> Optional[dict]:
    payload = {
        "chat_id": CANAL_ID,
        "text": texto,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    if incluir_boton_ws and WHATSAPP_URL:
        payload["reply_markup"] = {
            "inline_keyboard": [
                [{"text": "📲 ESCRIBENOS AL WHATSAPP", "url": WHATSAPP_URL}]
            ]
        }
    return telegram_api_call("sendMessage", payload)


def enviar_foto_canal(photo_file_id_or_url: str, caption: str, incluir_boton_ws: bool = True) -> Optional[dict]:
    payload = {
        "chat_id": CANAL_ID,
        "photo": photo_file_id_or_url,
        "caption": caption,
        "parse_mode": "HTML",
    }
    if incluir_boton_ws and WHATSAPP_URL:
        payload["reply_markup"] = {
            "inline_keyboard": [
                [{"text": "📲 ESCRIBENOS AL WHATSAPP", "url": WHATSAPP_URL}]
            ]
        }
    return telegram_api_call("sendPhoto", payload)


# =========================================================
# CONSULTA DE RESULTADOS Y RADAR DE ATRACCION EN VIVO
# =========================================================
def fetch_json(url: str, timeout: int = 18) -> Optional[dict]:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "AgenciaHaroldJoseBot/2.0", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="ignore")
            return json.loads(raw)
    except Exception as e:
        logger.warning(f"Error consultando {url}: {e}")
        return None


def publicar_radar_atraccion_en_vivo(loteria: str, hora_sorteo: str, numero_salido: str, animal_salido: str):
    """
    Consulta en tiempo real la Gaceta Oficial del Worker para extraer los 3 animalitos
    del Radar de Atraccion (Jala Ahora) de la loteria recien jugada y lo publica en texto.
    """
    lot_upper = loteria.strip().upper()
    if lot_upper not in LOTERIAS_RADAR_COMERCIAL:
        return

    hoy_ve = datetime.datetime.now(TZ_VE).strftime("%Y-%m-%d")
    url = f"{WORKER_API_URL.rstrip('/')}/gaceta?loteria={urllib.parse.quote(lot_upper)}&fecha={hoy_ve}"
    data = fetch_json(url, timeout=18)
    if not data or not isinstance(data.get("radar"), list) or len(data["radar"]) == 0:
        logger.warning(f"No se pudo obtener Radar de Atraccion para {lot_upper}")
        return

    radar_items = data["radar"][:3]
    emoji_salido = obtener_emoji_animal(animal_salido, lot_upper)

    lineas_radar = []
    for item in radar_items:
        num_r = str(item.get("numero", "")).strip()
        ani_r = str(item.get("animal", "")).strip().upper()
        if not num_r or not ani_r:
            continue
        em_r = obtener_emoji_animal(ani_r, lot_upper)
        lineas_radar.append(f"🎯 <b>{num_r} - {ani_r}</b> {em_r}")

    if not lineas_radar:
        return

    bloque_radar = "\n".join(lineas_radar)
    mensaje = (
        f"🧲 <b>RADAR DE ATRACCIÓN • {lot_upper}</b>\n"
        f"🕒 Tras salir el <b>{numero_salido} - {animal_salido}</b> {emoji_salido} ({hora_sorteo})\n\n"
        f"🔥 <b>JALA AHORA PARA EL PRÓXIMO SORTEO:</b>\n"
        f"{bloque_radar}\n\n"
        f"🍀 <i>Datos en vivo • Centro de Apuestas Harold José</i>"
    )
    enviar_mensaje_canal(mensaje, incluir_boton_ws=True)
    logger.info(f"Radar de Atraccion publicado para {lot_upper} ({hora_sorteo})")


def formatear_mensaje_individual(loteria: str, hora: str, numero: str, animal: str) -> str:
    emoji = obtener_emoji_animal(animal, loteria)
    hoy_str = datetime.datetime.now(TZ_VE).strftime("%d/%m/%Y")
    return (
        f"🎰 <b>{loteria.upper()}</b>\n"
        f"🕒 Hora: <b>{hora}</b> | 📅 {hoy_str}\n"
        f"🏆 Resultado: <b>{numero} - {animal.upper()}</b> {emoji}\n\n"
        f"✅ <i>Centro de Apuestas Harold José • ¡Juega y cobra al instante!</i>"
    )


def verificar_resultados():
    ahora_ve = datetime.datetime.now(TZ_VE)
    hoy_iso = ahora_ve.strftime("%Y-%m-%d")

    data = fetch_json(f"{WORKER_API_URL.rstrip('/')}/", timeout=20)
    if not data or not data.get("ok") or not isinstance(data.get("loterias"), list):
        return

    nuevos_detectados = []
    for lot in data["loterias"]:
        nombre_lot = str(lot.get("nombre", "")).strip().upper()
        if not nombre_lot:
            continue
        for s in lot.get("sorteos", []):
            hora = str(s.get("hora", "")).strip().upper()
            numero = str(s.get("numero", "")).strip()
            animal = str(s.get("animal", "")).strip().upper()

            if not hora or not numero or numero == "--" or not animal or animal == "PENDIENTE":
                continue

            if not ya_fue_publicado(hoy_iso, nombre_lot, hora):
                guardar_resultado_db(hoy_iso, nombre_lot, hora, numero, animal)
                nuevos_detectados.append((nombre_lot, hora, numero, animal))

    for nombre_lot, hora, numero, animal in nuevos_detectados:
        msg = formatear_mensaje_individual(nombre_lot, hora, numero, animal)
        enviar_mensaje_canal(msg, incluir_boton_ws=True)
        logger.info(f"Publicado resultado individual: {nombre_lot} {hora} -> {numero} {animal}")
        time.sleep(0.7)
        if nombre_lot in LOTERIAS_RADAR_COMERCIAL:
            publicar_radar_atraccion_en_vivo(nombre_lot, hora, numero, animal)
            time.sleep(0.7)


# =========================================================
# TABLAS RESUMENES AUTOMATICAS (MINUTOS 10 Y 50)
# =========================================================
def normalizar_hora_clave(hora_str: str) -> str:
    h = hora_str.strip().upper().replace("  ", " ")
    m = re.match(r"^0?(\d{1,2}:\d{2}\s*[AP]M)$", h)
    return m.group(1) if m else h


def construir_bloque_tabla(titulo: str, lista_loterias: list, datos_dia: dict) -> str:
    ahora_ve = datetime.datetime.now(TZ_VE)
    fecha_txt = ahora_ve.strftime("%d/%m/%Y")
    hora_txt = ahora_ve.strftime("%I:%M %p")

    horas_con_datos = []
    for hr in HORAS_ESTANDAR_TABLA:
        tiene = False
        for lot in lista_loterias:
            res_lot = datos_dia.get(lot, {})
            for k_hr in res_lot:
                if normalizar_hora_clave(k_hr) == hr:
                    tiene = True
                    break
            if tiene:
                break
        if tiene:
            horas_con_datos.append(hr)

    if not horas_con_datos:
        return ""

    encabezados = [ABREVIATURAS_TABLA.get(l, l[:5]) for l in lista_loterias]
    header_line = "HORA  | " + " | ".join(f"{h:<5}" for h in encabezados)
    sep_line = "-" * len(header_line)

    filas = [header_line, sep_line]
    for hr in horas_con_datos:
        hr_corta = hr.replace(" AM", "a").replace(" PM", "p")
        celdas = []
        for lot in lista_loterias:
            res_lot = datos_dia.get(lot, {})
            val = "###"
            for k_hr, info in res_lot.items():
                if normalizar_hora_clave(k_hr) == hr:
                    num_raw = str(info.get("numero", "###"))
                    val = num_raw.zfill(2) if num_raw != "0" else "0"
                    break
            celdas.append(f"{val:<5}")
        filas.append(f"{hr_corta:<6}| " + " | ".join(celdas))

    tabla_mono = "\n".join(filas)
    return (
        f"📊 <b>{titulo}</b>\n"
        f"📅 {fecha_txt} • 🕒 Corte: {hora_txt}\n\n"
        f"<pre>{tabla_mono}</pre>\n"
        f"🏆 <i>Centro de Apuestas Harold José</i>"
    )


def publicar_tablas_resumen():
    ahora_ve = datetime.datetime.now(TZ_VE)
    hoy_iso = ahora_ve.strftime("%Y-%m-%d")
    datos_dia = obtener_resultados_dia_db(hoy_iso)
    if not datos_dia:
        return

    grupos = [
        ("RESUMEN TRADICIONALES • BLOQUE 1", ["LOTTO ACTIVO", "LA GRANJITA", "GUACHARO ACTIVO", "EL GUACHARITO MILLONARIO", "SELVA PLUS"]),
        ("RESUMEN ESPECIALES • BLOQUE 2", ["GUACA ACTIVA", "MEGA GUACA", "RULETA ACTIVA", "GRANJA MILLONARIA", "LOTTO CHAIMA"]),
        ("RESUMEN INTERNACIONAL Y PLUS • BLOQUE 3", ["RULETA ROYAL", "CONDOR GANA", "CHANCE ANIMAL", "FRUITAGANA", "GRANJITA PLUS"]),
        ("RESUMEN VIP • BLOQUE 4", ["MEGA ANIMAL", "MONJE MILLONARIO", "LOTTO REY", "LOTTOMAX", "RULETON VENEZUELA"]),
    ]

    for titulo, lots in grupos:
        msg = construir_bloque_tabla(titulo, lots, datos_dia)
        if msg:
            enviar_mensaje_canal(msg, incluir_boton_ws=True)
            time.sleep(1.0)


# =========================================================
# TASA BCV DIARIA
# =========================================================
def publicar_tasa_bcv():
    ahora_ve = datetime.datetime.now(TZ_VE)
    hoy_iso = ahora_ve.strftime("%Y-%m-%d")
    if get_config("ultima_bcv_fecha") == hoy_iso:
        return

    data = fetch_json("https://ve.dolarapi.com/v1/dolares/oficial", timeout=15)
    if not data or not data.get("promedio"):
        return

    tasa = float(data["promedio"])
    tasa_fmt = f"{tasa:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    fecha_txt = ahora_ve.strftime("%d/%m/%Y")

    msg = (
        f"💵 <b>TASA OFICIAL BCV DEL DÍA</b>\n"
        f"📅 Fecha: <b>{fecha_txt}</b>\n\n"
        f"🇺🇸 <b>1 USD = {tasa_fmt} Bs.</b>\n\n"
        f"🏦 <i>Referencia oficial para recargas y pagos • Centro de Apuestas Harold José</i>"
    )
    res = enviar_mensaje_canal(msg, incluir_boton_ws=True)
    if res and res.get("ok"):
        set_config("ultima_bcv_fecha", hoy_iso)
        logger.info(f"Tasa BCV publicada: {tasa_fmt} Bs.")


# =========================================================
# BUCLE PRINCIPAL EN SEGUNDO PLANO
# =========================================================
def worker_loop():
    logger.info("Hilo de monitoreo iniciado (Resultados + Radar + Tablas min 10/50 + BCV).")
    while True:
        try:
            ahora_ve = datetime.datetime.now(TZ_VE)
            minuto = ahora_ve.minute
            hora = ahora_ve.hour
            clave_minuto = ahora_ve.strftime("%Y-%m-%d %H:%M")

            # 1. Verificar nuevos resultados y publicar Radar de Atraccion en vivo
            verificar_resultados()

            # 2. Tablas resumen en minutos 10 y 50 entre las 8:00 AM y 8:55 PM
            if 8 <= hora <= 20 and minuto in (10, 50):
                if get_config("ultimo_resumen_minuto") != clave_minuto:
                    set_config("ultimo_resumen_minuto", clave_minuto)
                    publicar_tablas_resumen()

            # 3. Tasa BCV a partir de las 9:05 AM
            if hora >= 9 and minuto >= 5:
                publicar_tasa_bcv()

        except Exception as e:
            logger.error(f"Error en ciclo principal: {e}")

        time.sleep(25)


# =========================================================
# APLICACION WEB FLASK (KEEP-ALIVE + ENDPOINTS DE PRUEBA)
# =========================================================
init_db()
app = Flask(__name__)


@app.route("/", methods=["GET"])
def health():
    ahora_ve = datetime.datetime.now(TZ_VE).strftime("%Y-%m-%d %H:%M:%S")
    return jsonify({
        "ok": True,
        "servicio": "Bot Telegram Centro de Apuestas Harold Jose",
        "hora_venezuela": ahora_ve,
        "canal": CANAL_ID,
    })


@app.route("/test/radar", methods=["GET"])
def test_radar():
    lot = request.args.get("loteria", "LOTTO ACTIVO").upper()
    publicar_radar_atraccion_en_vivo(lot, "PRUEBA", "05", "LEÓN")
    return jsonify({"ok": True, "loteria": lot})


@app.route("/test/resumen", methods=["GET"])
def test_resumen():
    publicar_tablas_resumen()
    return jsonify({"ok": True})


# Iniciar hilo daemon al cargar el modulo (compatible con gunicorn y python directo)
threading.Thread(target=worker_loop, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
