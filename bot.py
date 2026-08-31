from datetime import datetime
import json
import os
import random
import re
from threading import Thread
import time
import traceback
from apscheduler.schedulers.background import BackgroundScheduler
from bs4 import BeautifulSoup
from flask import Flask
import requests
import telebot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup
import urllib3

# Forzar la zona horaria de Venezuela de forma segura
os.environ["TZ"] = "America/Caracas"
try:
    time.tzset()
except Exception as e:
    print(f"⚠️ Nota sobre tzset: {e}")

# Desactivar advertencias de certificados SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Credenciales y canal principal configurado
TOKEN = "8728747633:AAHakMFznhlpK6QbkZinctgbl131wE2hIeI"
CANAL = "@resultadosagharoldjose"  # Canal oficial de producción indicado
ENLACE_CANAL = "https://t.me/resultadosagharoldjose"
ENLACE_POLLAS = "https://t.me/pollasydupletas"
NUMERO_WHATSAPP = "584124489363"
TELEGRAM_PRIVADO = "https://t.me/ag_haroldjose"

bot = telebot.TeleBot(TOKEN)
scheduler = BackgroundScheduler(timezone="America/Caracas")

URL_LOTERIA = "https://lotery.winbigvzla.com/resultados"
URL_BCV = "https://www.bcv.org.ve/"
STATE_FILE = "bot_state.json"

# Control estricto anti-duplicados y memoria
horarios_enviados_hoy = set()
primera_ejecucion = True
ultima_hora_polla = None

taquilla_activa_hoy = False
imagen_taquilla_file_id = None
regalos_hoy = []

ANIMALITOS_DICT = {
    "0": "Delfín",
    "00": "Ballena",
    "1": "Carnero",
    "2": "Toro",
    "3": "Ciempiés",
    "4": "Alacrán",
    "5": "León",
    "6": "Rana",
    "7": "Perico",
    "8": "Ratón",
    "9": "Águila",
    "10": "Tigre",
    "11": "Gato",
    "12": "Caballo",
    "13": "Mono",
    "14": "Paloma",
    "15": "Zorro",
    "16": "Oso",
    "17": "Pavo",
    "18": "Burro",
    "19": "Chivo",
    "20": "Cochino",
    "21": "Gallo",
    "22": "Camello",
    "23": "Cebra",
    "24": "Iguana",
    "25": "Gallina",
    "26": "Vaca",
    "27": "Perro",
    "28": "Samuro",
    "29": "Elefante",
    "30": "Caimán",
    "31": "Lapa",
    "32": "Ardilla",
    "33": "Pescado",
    "34": "Venado",
    "35": "Jirafa",
    "36": "Culebra",
}


def cargar_estado_disco():
    global horarios_enviados_hoy, primera_ejecucion, ultima_hora_polla, taquilla_activa_hoy, regalos_hoy
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                data = json.load(f)
                hoy_str = datetime.now().strftime("%Y-%m-%d")
                if data.get("fecha") == hoy_str:
                    horarios_enviados_hoy = set(tuple(x) for x in data.get("enviados", []))
                    primera_ejecucion = data.get("primera_ejecucion", False)
                    if data.get("ultima_polla_hora"):
                        h_data = data.get("ultima_polla_hora")
                        ultima_hora_polla = (
                            datetime.strptime(h_data[0], "%Y-%m-%d").date(),
                            h_data[1],
                        )
                    taquilla_activa_hoy = data.get("taquilla_activa", False)
                    regalos_hoy = data.get("regalos_hoy", [])
                    print(f"📂 Estado cargado desde disco. Slots bloqueados: {len(horarios_enviados_hoy)}")
                    return
        except Exception as e:
            print(f"⚠️ Error cargando estado: {e}")
    horarios_enviados_hoy = set()
    primera_ejecucion = True
    ultima_hora_polla = None
    taquilla_activa_hoy = False
    regalos_hoy = []


def guardar_estado_disco():
    try:
        hoy_str = datetime.now().strftime("%Y-%m-%d")
        polla_serializable = None
        if ultima_hora_polla:
            polla_serializable = [
                str(ultima_hora_polla[0]),
                ultima_hora_polla[1],
            ]
        data = {
            "fecha": hoy_str,
            "enviados": list(list(x) for x in horarios_enviados_hoy),
            "primera_ejecucion": primera_ejecucion,
            "ultima_polla_hora": polla_serializable,
            "taquilla_activa": taquilla_activa_hoy,
            "regalos_hoy": regalos_hoy,
        }
        with open(STATE_FILE, "w") as f:
            json.dump(data, f)
    except Exception as e:
        print(f"⚠️ Error guardando estado: {e}")


# Cargar estado inicial al arrancar
cargar_estado_disco()

caption_taquilla = (
    "✅ AGENCIA HAROLD JOSÉ ACTIVA ✅\n"
    "Ya estamos operativos brindando la mejor atención. Calidad, respaldo y rapidez en cada una de todas tus solicitudes.\n\n"
    "📲 Envía tus jugadas:\n"
    "(Comprobante de pago / Lotería / monto / Hora)\n\n"
    "📖 Consulta nuestro reglamento aquí:\n"
    "https://wa.me/p/33319103291071105/584124489363\n"
    "🚀 Agiliza tu proceso aquí: https://wa.me/p/24724650613899486/584124489363\n\n"
    "RESULTADOS AUTOMÁTICOS\n"
    f"{ENLACE_CANAL}\n\n"
    "¡Mucho éxito en la jornada de hoy! 🍀✨"
)

TEXTO_PUBLICITARIO = (
    "🔥 ¡NUEVO EN AGENCIA HAROLD JOSÉ! 🔥\n"
    "💥 ¡AHORA TENEMOS CASHEA! 💥\n"
    "🎰 TODAS TUS LOTERÍAS EN UN SOLO LUGAR\n"
    "💰 Ruletas • Triples • Tripletas • Pollas • Bingos\n"
    "🛡 6 AÑOS DE CONFIANZA EN TODA VENEZUELA\n"
    "💳 Pago Móvil y Transferencias\n"
    "🚀 Cupos altos para jugar en grande\n"
    "👇 REVISA TODO LO QUE TENEMOS DISPONIBLE 👇\n"
    "‎➖➖➖➖➖➖➖➖➖➖\n"
    "🎰 RULETAS DISPONIBLES 🎰\n"
    "• Lotto Activo\n"
    "• La Granjita\n"
    "• Selva Plus\n"
    "• Guácharo Activo\n"
    "• Loto Chaima\n"
    "• Monje Millonario\n"
    "• Lotto Inter\n"
    "• Cazaloton\n"
    "• Mega Animal\n"
    "• Centena Animalitos\n"
    "• Centena Plus\n"
    "• Guacharito Millonario\n"
    "• Ruleta Activa\n"
    "• Granjita Plus\n"
    "• La Ricachona\n"
    "• Guaca Activa 37\n"
    "• Mega Guaca\n"
    "• Lotto Max\n"
    "• Tropi Gana\n"
    "• Cóndor Gana\n"
    "• Granja Millonaria\n"
    "• Fruti Gana\n"
    "• Granjazo\n"
    "• Lotto Gato\n"
    "• Gatazo\n"
    "• Calamar Millonario\n"
    "• Ruleta Activa ESP\n"
    "‎➖➖➖➖➖➖➖➖➖➖\n"
    "🔢 TRIPLES Y TERMINALES 🔢\n"
    "• Trio Activo\n"
    "• Triple Fácil\n"
    "• Triple Chance\n"
    "• Triple Caliente\n"
    "• Triple Zulia\n"
    "• Triple Táchira\n"
    "• Triple Caracas\n"
    "• Triple Zamorano\n"
    "• Triple Gana\n"
    "• Triple Napa\n"
    "• Ricachona\n"
    "• Triple Centena\n"
    "• Triple Dorado\n"
    "• La Ruca\n"
    "‎➖➖➖➖➖➖➖➖➖➖\n"
    "🎰 TRIPLETAS DISPONIBLES 🎰\n"
    "⚠️ SÓLO SE SELLA HASTA LAS 8:50 AM\n"
    "🚫 NO VENDO BASES\n"
    "• Lotto Activo | La Granjita | Selva Plus\n"
    "• Guácharo Activo | Lotto Inter | Cazaloton\n"
    "• Guacharito Millonario | Monje Millonario | Tropi Gana | Cóndor Gana | Granja Millonaria | Fruti Gana | Granjazo | Lotto Max | Ruleta Activa | Guaca37....\n"
    "‎➖➖➖➖➖➖➖➖➖➖\n"
    "🎊 POLLAS Y DUPLETAS 🎊\n"
    "• Polla Animaniacs | Mini Polla\n"
    "• Pozo Millonario | Super Polla\n"
    "• Super Seven | Micro Polla\n"
    "• Sumatoria Niño de Oro\n"
    "• Polla por Puntos | Dupletas y más...\n"
    "‎➖➖➖➖➖➖➖➖➖➖\n"
    "🌐 BINGOS DISPONIBLES 🌐\n"
    "• BINGO MILLONARIO PLUS\n"
    "‎➖➖➖➖➖➖➖➖➖➖\n"
    "📢 ÚNETE A NUESTRA COMUNIDAD OFICIAL 🎲🔥\n"
    "📲 Entra a nuestro canal de Telegram y consulta todos los resultados:\n"
    f"👉 {ENLACE_CANAL}\n"
    "🔥 AGENCIA HAROLD JOSÉ 🔥\n"
    "💰 JUEGA CON CONFIANZA"
)

TEXTO_CASHEA = (
    "✨ ¡Tu jugada favorita ahora con facilidades de pago! 💜🔥\n\n"
    "En la AGENCIA HAROLD JOSÉ te ayudamos a ganar: juega hoy, paga después con Cashea y llévate ese premio que tanto esperas. 💸\n\n"
    "📲 Activa tu jugada escribiendo al WhatsApp: 04124489363. ¡Atención rápida y segura! ⚡"
)

HEADER_RESULTADOS = (
    "CENTRO DE APUESTAS HAROLD JOSÉ\n"
    "SEGURIDAD Y CONFIANZA\n"
    "RESULTADOS OFICIALES\n"
    "📲JUEGA AQUI👇👇\n"
    "WHATSAPP: 04124489363\n\n"
    f"📢 CANAL DE RESULTADOS:\n{ENLACE_CANAL}"
)

app = Flask("")


@app.route("/")
def home():
    estado_tag = (
        "ACTIVADA 🟢 (Trabajando hoy)"
        if taquilla_activa_hoy
        else "DESACTIVADA 🔴 (No laborando)"
    )
    return (
        f"¡El bot de resultados de la AGENCIA HAROLD JOSÉ está activo en el canal oficial {CANAL}!<br><br>"
        f"<b>Estado del aviso de taquilla de hoy:</b> {estado_tag}<br><br>"
        "<b>Enlaces de prueba rápida (Test de cada opción):</b><br>"
        "👉 <a href='/test/madrugada'>Probar Saludo de Madrugada (6:30 AM)</a><br>"
        "👉 <a href='/test/piramide'>Probar Pirámide Numérica con Sumas por Fila (6:31 AM)</a><br>"
        "👉 <a href='/test/regalos'>Probar Regalos de la Agencia (6:45 AM)</a><br>"
        "👉 <a href='/test/saludo'>Probar Saludo Matutino (7:00 AM)</a><br>"
        "👉 <a href='/test/publicidad'>Probar Aviso Publicitario (7am/3pm/6pm)</a><br>"
        "👉 <a href='/test/cashea'>Probar Aviso con Botones Cashea (9am/10:30am/12:30pm)</a><br>"
        "👉 <a href='/test/tiempocumplido'>Probar Tiempo Cumplido (Minuto 55)</a><br>"
        "👉 <a href='/test/bcv'>Probar Tasa Oficial BCV</a><br>"
        "👉 <a href='/test/taquilla_manual'>Probar Envío Manual de Taquilla Activa</a><br>"
        "👉 <a href='/test/pollas'>Probar Aviso de Pollas (Minuto 10)</a><br>"
        "👉 <a href='/test/resultados'>Forzar Revisión de Resultados Individuales</a><br>"
        "👉 <a href='/test/cierre'>Probar Mensaje de Cierre (9:10 PM)</a>"
    )


@app.route("/test/madrugada")
def test_madrugada():
    enviar_saludo_madrugada()
    return "Prueba de Saludo de Madrugada ejecutada."


@app.route("/test/piramide")
def test_piramide():
    enviar_piramide_diaria()
    return "Prueba de Pirámide Numérica con Sumas ejecutada."


@app.route("/test/regalos")
def test_regalos():
    enviar_regalos_agencia()
    return "Prueba de Regalos de la Agencia ejecutada."


@app.route("/test/saludo")
def test_saludo():
    enviar_saludo_matutino()
    return "Prueba de Saludo Matutino ejecutada."


@app.route("/test/publicidad")
def test_publicidad():
    enviar_anuncio_publicitario()
    return "Prueba de Aviso Publicitario ejecutada."


@app.route("/test/cashea")
def test_cashea():
    enviar_anuncio_cashea()
    return "Prueba de Aviso con Botones Cashea ejecutada."


@app.route("/test/tiempocumplido")
def test_tiempocumplido():
    enviar_aviso_tiempo_cumplido()
    return "Prueba de Aviso de Tiempo Cumplido ejecutada."


@app.route("/test/bcv")
def test_bcv():
    enviar_tasa_dolar()
    return "Prueba de Tasa BCV ejecutada."


@app.route("/test/taquilla_manual")
def test_taquilla_manual():
    global taquilla_activa_hoy, imagen_taquilla_file_id
    taquilla_activa_hoy = True
    guardar_estado_disco()
    if imagen_taquilla_file_id:
        enviar_telegram_foto(imagen_taquilla_file_id, caption_taquilla)
    else:
        enviar_telegram(caption_taquilla, disable_web_preview=True)
    return "Prueba de Taquilla Activa ejecutada (y estado marcado como activado)."


@app.route("/test/pollas")
def test_pollas():
    tarea_minuto_diez()
    return "Prueba de Aviso de Pollas ejecutada."


@app.route("/test/resultados")
def test_resultados():
    verificar_resultados()
    return "Prueba de Verificación de Resultados ejecutada."


@app.route("/test/cierre")
def test_cierre():
    enviar_mensaje_cierre()
    return "Prueba de Cierre de Jornada ejecutada."


def limpiar_texto(texto):
    return " ".join(texto.split())


def enviar_telegram(mensaje, disable_web_preview=True):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CANAL,
        "text": mensaje,
        "parse_mode": "Markdown",
        "disable_web_page_preview": disable_web_preview,
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code != 200:
            print(f"⚠️ Error al enviar al canal: {response.text}")
    except Exception as e:
        print(f"⚠️ Excepción de conexión con Telegram: {e}")


def enviar_telegram_con_botones(mensaje):
    markup = InlineKeyboardMarkup()
    url_jugar = f"https://wa.me/{NUMERO_WHATSAPP}?text=Hola%2C%20quiero%20jugar%20en%20Agencia%20Harold%20Jos%C3%A9."
    markup.add(
        InlineKeyboardButton("🎯 JUEGA AQUÍ (WhatsApp)", url=url_jugar),
        InlineKeyboardButton("💬 ESCRIBIR A PRIVADO", url=TELEGRAM_PRIVADO),
    )
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CANAL,
        "text": mensaje,
        "parse_mode": "Markdown",
        "reply_markup": markup.to_dict(),
        "disable_web_page_preview": True,
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code != 200:
            print(f"⚠️ Error al enviar al canal con botones: {response.text}")
    except Exception as e:
        print(f"⚠️ Excepción de conexión con Telegram: {e}")


def enviar_telegram_foto(photo_id, caption):
    url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
    payload = {
        "chat_id": CANAL,
        "photo": photo_id,
        "caption": caption,
        "parse_mode": "Markdown",
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code != 200:
            print(f"⚠️ Error al enviar foto al canal: {response.text}")
            enviar_telegram(caption, disable_web_preview=True)
    except Exception as e:
        print(f"⚠️ Excepción de conexión con Telegram al enviar foto: {e}")
        enviar_telegram(caption, disable_web_preview=True)


def limpiar_memoria_diaria():
    global horarios_enviados_hoy, primera_ejecucion, taquilla_activa_hoy, imagen_taquilla_file_id, ultima_hora_polla, regalos_hoy
    horarios_enviados_hoy.clear()
    primera_ejecucion = True
    taquilla_activa_hoy = False
    imagen_taquilla_file_id = None
    ultima_hora_polla = None
    regalos_hoy = []
    if os.path.exists(STATE_FILE):
        os.remove(STATE_FILE)
    print("🧹 Memoria y archivo de disco limpiados para el nuevo día.")


def enviar_saludo_madrugada():
    enviar_telegram(
        "🎯 CENTRO DE APUESTAS HAROLD JOSÉ 🎯\n\n"
        "🌅 ¡Despertando con la mejor energía y listos para ganar! 🌅\n\n"
        "Comenzamos este nuevo día activos y enfocados. ¡Que la suerte esté de nuestro lado! 🍀🔥",
        disable_web_preview=True,
    )


def generar_piramide():
    ahora = datetime.now()
    fecha_str = ahora.strftime("%d/%m/%Y")
    digitos = [int(c) for c in fecha_str if c.isdigit()]
    filas = [digitos]
    while len(filas[-1]) > 1:
        actual = filas[-1]
        siguiente = [(actual[i] + actual[i + 1]) % 10 for i in range(len(actual) - 1)]
        filas.append(siguiente)

    lineas_formateadas = []
    sumas_filas_texto = []
    sufijos_filas = ["1RA", "2DA", "3RA", "4TA", "5TA", "6RA", "7RA", "8RA"]

    for i, f in enumerate(filas):
        nums_str = "  ".join(str(d) for d in f)
        dots_count = 3 + (i * 2)
        lineas_formateadas.append(f"{'.' * dots_count}  {nums_str}  {'.' * dots_count}")

        suma_fila = sum(f)
        nombre_fila = sufijos_filas[i] if i < len(sufijos_filas) else f"{i+1}TA"
        sumas_filas_texto.append(f"• {nombre_fila} FILA: {suma_fila}")

    cuerpo_piramide = "\n".join(lineas_formateadas)
    bloque_sumas = "\n".join(sumas_filas_texto)

    seed_val = (
        int(ahora.strftime("%Y%m%d"))
        + ahora.hour * 100
        + ahora.minute
        + random.randint(100, 999)
    )
    rnd = random.Random(seed_val)

    candidates = []
    for f in filas:
        for idx in range(len(f) - 1):
            val = (f[idx] * 10 + f[idx + 1] + rnd.randint(1, 15)) % 37
            candidates.append(f"{val:02d}" if val != 0 else "0")
            candidates.append("00")
        for num in f:
            val = (num * 7 + rnd.randint(1, 15)) % 37
            candidates.append(f"{val:02d}" if val != 0 else "0")
            candidates.append("00")

    unique_candidates = []
    for c in candidates:
        if c not in unique_candidates:
            unique_candidates.append(c)

    rnd.shuffle(unique_candidates)

    while len(unique_candidates) < 6:
        r_val = rnd.randint(0, 36)
        c_rand = f"{r_val:02d}" if r_val != 0 else ("0" if rnd.random() > 0.5 else "00")
        if c_rand not in unique_candidates:
            unique_candidates.append(c_rand)

    d1 = f"{unique_candidates[0]}-{unique_candidates[1]}-{unique_candidates[2]}"
    d2 = f"{unique_candidates[3]}-{unique_candidates[4]}-{unique_candidates[5]}"

    return (
        "🎯 CENTRO DE APUESTAS HAROLD JOSÉ 🎯\n"
        "📢 REPORTE TÁCTICO - LA PIRÁMIDE 📢\n\n"
        f"📅 Fecha: {fecha_str}\n"
        "Análisis matemático actualizado y listo para la jugada. ¡A asegurar posición:\n\n"
        f"{cuerpo_piramide}\n\n"
        "📊 SUMA POR FILA:\n"
        f"{bloque_sumas}\n\n"
        "🔥 DATOS CLAVES PARA HOY:\n"
        f"📌 {d1}\n"
        f"📌 {d2}\n\n"
        "⚡ ¡La precisión y los números hablan por sí solos! ¡Juega con confianza y gana con nosotros! 🍀 💰"
    )


def enviar_piramide_diaria():
    enviar_telegram(generar_piramide(), disable_web_preview=True)


def generar_regalos_agencia():
    global regalos_hoy
    ahora = datetime.now()
    fecha_str = ahora.strftime("%d/%m/%Y")
    seed_val = int(ahora.strftime("%Y%m%d"))
    rnd = random.Random(seed_val)

    nums_disponibles = list(range(37))
    rnd.shuffle(nums_disponibles)

    regalos_hoy = []
    seleccionados = nums_disponibles[:3]
    for num in seleccionados:
        num_str = f"{num:02d}" if num != 0 else ("0" if rnd.random() > 0.5 else "00")
        if num == 0:
            num_str = "0"
        animal = ANIMALITOS_DICT.get(num_str, ANIMALITOS_DICT.get(str(num), "Animal"))
        regalos_hoy.append((num_str, animal))

    guardar_estado_disco()

    r1 = f"{regalos_hoy[0][0]} - {regalos_hoy[0][1]}"
    r2 = f"{regalos_hoy[1][0]} - {regalos_hoy[1][1]}"
    r3 = f"{regalos_hoy[2][0]} - {regalos_hoy[2][1]}"

    return (
        "🎁 LOS REGALOS DE LA AGENCIA HAROLD JOSÉ 🎁\n"
        f"📅 Fecha: {fecha_str}\n\n"
        "¡Los fijos recomendados para reventar la banca hoy:\n\n"
        f"⭐ 1er Regalo: {r1}\n"
        f"⭐ 2do Regalo: {r2}\n"
        f"⭐ 3er Regalo: {r3}\n\n"
        f"📲 WHATSAPP: {NUMERO_WHATSAPP}\n"
        f"{ENLACE_CANAL}\n\n"
        "¡Mucha suerte en sus jugadas! 🍀✨"
    )


def enviar_regalos_agencia():
    enviar_telegram(generar_regalos_agencia(), disable_web_preview=True)


def enviar_saludo_matutino():
    enviar_telegram(
        "🎯 CENTRO DE APUESTAS HAROLD JOSÉ 🎯\n\n"
        "🌅 ¡Buenos días a todos! 🌅\n\n"
        "Ya arrancamos un nuevo día con la mejor energía. Por estaremos compartiendo todos los resultados de los animalitos a medida que vayan saliendo.\n\n"
        "📢 Nuestros canales oficiales:\n"
        f"🎟️ Catálogo y WhatsApp: https://wa.me/c/{NUMERO_WHATSAPP}\n"
        "📸 Instagram: https://www.instagram.com/agharold.jose (@agharold.jose)\n"
        "💬 Canal de WhatsApp: https://whatsapp.com/channel/0029Vaza7YIGzzKJq7as7s1T\n\n"
        "¡Mucha suerte en sus jugadas el día de hoy y a ganar! 🍀🔥",
        disable_web_preview=True,
    )


def enviar_anuncio_publicitario():
    enviar_telegram(TEXTO_PUBLICITARIO, disable_web_preview=True)


def enviar_anuncio_cashea():
    markup = InlineKeyboardMarkup()
    url_jugar = f"https://wa.me/{NUMERO_WHATSAPP}?text=Hola%2C%20quiero%20jugar%20con%20Cashea%20en%20Agencia%20Harold%20Jos%C3%A9."
    url_consultar = f"https://wa.me/{NUMERO_WHATSAPP}?text=Hola%2C%20quiero%20consultar%20mis%20cuotas%20de%20Cashea%20en%20Agencia%20Harold%20Jos%C3%A9."

    markup.add(
        InlineKeyboardButton("🎯 JUGAR CON CASHEA", url=url_jugar),
        InlineKeyboardButton("💳 CONSULTAR CASHEA", url=url_consultar),
    )

    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CANAL,
        "text": TEXTO_CASHEA,
        "parse_mode": "Markdown",
        "reply_markup": markup.to_dict(),
        "disable_web_page_preview": True,
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code != 200:
            print(f"⚠️ Error al enviar anuncio de Cashea: {response.text}")
    except Exception as e:
        print(f"⚠️ Excepción al enviar anuncio de Cashea: {e}")


def enviar_aviso_tiempo_cumplido():
    enviar_telegram(
        "⏰ ¡Tiempo cumplido! Han finalizado las jugadas para este sorteo en la AGENCIA HAROLD JOSÉ. ¡Muy atentos a los resultados y que la suerte esté de tu lado! 🍀✨",
        disable_web_preview=True,
    )


def enviar_tasa_dolar():
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(URL_BCV, headers=headers, timeout=15, verify=False)
        precio_dolar = "756,71"
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            dolar_div = soup.find("div", id="dolar")
            if dolar_div and dolar_div.find("strong"):
                raw_precio = dolar_div.find("strong").get_text(strip=True)
                cleaned = re.sub(r"[^\d,\.]", "", raw_precio)
                cleaned = cleaned.replace(".", ",")
                parts = cleaned.split(",")
                if len(parts) >= 2:
                    integers = parts[0]
                    decimals = parts[1][:2]
                    precio_dolar = f"{integers},{decimals}"
                elif len(parts) == 1 and parts[0]:
                    precio_dolar = parts[0]

        enviar_telegram(
            "💵 TASA OFICIAL BCV 💵\n\n"
            "🏦 Moneda: Dólar Estadounidense\n"
            f"📈 Precio Oficial: Bs. {precio_dolar}\n\n"
            "🔗 Fuente: Banco Central de Venezuela",
            disable_web_preview=True,
        )
    except Exception as e:
        print(f"Error BCV: {e}")


def tarea_envio_programado_taquilla():
    global taquilla_activa_hoy, imagen_taquilla_file_id
    if taquilla_activa_hoy:
        if imagen_taquilla_file_id:
            enviar_telegram_foto(imagen_taquilla_file_id, caption_taquilla)
            print("✅ Taquilla activa reenviada automáticamente a las 3:00 PM.")
        else:
            enviar_telegram(caption_taquilla, disable_web_preview=True)
            print("✅ Taquilla activa reenviada por texto a las 3:00 PM.")
    else:
        print("ℹ️ A las 3:00 PM la taquilla no fue activada en la mañana, se omite el envío.")


def tarea_minuto_diez():
    global ultima_hora_polla
    ahora = datetime.now()
    if (
        (ahora.hour == 7 and ahora.minute >= 10)
        or (7 < ahora.hour < 17)
        or (ahora.hour == 17 and ahora.minute == 0)
    ):
        clave_hora = (ahora.date(), ahora.hour)
        if ultima_hora_polla != clave_hora:
            ultima_hora_polla = clave_hora
            guardar_estado_disco()
            enviar_telegram(
                "🎯 CENTRO DE APUESTAS HAROLD JOSÉ 🎯\n\n"
                "📢 ¡Pollas actualizadas!\n"
                "Puedes verlas aquí 👇🏻\n"
                f"{ENLACE_POLLAS}\n\n"
                "¡Mucho éxito! 🍀",
                disable_web_preview=False,
            )


def enviar_mensaje_cierre():
    global taquilla_activa_hoy, imagen_taquilla_file_id, ultima_hora_polla, regalos_hoy
    enviar_telegram(
        "🎯 CENTRO DE APUESTAS HAROLD JOSÉ 🎯\n\n"
        "🌙 ¡FINAL DE JORNADA! 🌙\n\n"
        "Estos fueron todos los resultados del día de hoy. ¡Gracias por jugar con nosotros! Los esperamos el día de mañana con mucha más suerte y energía. 🍀✨",
        disable_web_preview=True,
    )
    taquilla_activa_hoy = False
    imagen_taquilla_file_id = None
    ultima_hora_polla = None
    regalos_hoy = []
    guardar_estado_disco()


def verificar_resultados():
    global horarios_enviados_hoy, primera_ejecucion, regalos_hoy
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
        }
        respuesta = requests.get(URL_LOTERIA, headers=headers, timeout=15)
        if respuesta.status_code != 200:
            print(f"⚠️ Error al conectar con la web de lotería: {respuesta.status_code}")
            return

        soup = BeautifulSoup(respuesta.text, "html.parser")
        tarjetas = soup.find_all(
            ["div", "article", "section"],
            class_=re.compile(r"card|box|item|lotto|result", re.IGNORECASE),
        )
        if not tarjetas:
            tarjetas = soup.find_all(["div", "section"])

        nuevos_encontrados = []

        for tarjeta in tarjetas:
            texto_tarjeta = tarjeta.get_text(" ", strip=True).upper()
            if "PENDIENTE" in texto_tarjeta:
                continue

            match_h = re.search(r"(\d{1,2}:\d{2}\s*(?:AM|PM))", texto_tarjeta)
            if not match_h:
                continue
            hora = match_h.group(1).upper()

            nombre_loteria = "RULETA ACTIVA"
            posibles_titulos = tarjeta.find_all(
                ["h1", "h2", "h3", "h4", "h5", "span", "div", "strong", "b"],
                class_=re.compile(r"title|header|name|lotto|text", re.IGNORECASE),
            )
            for pt in posibles_titulos:
                t_text = pt.get_text(" ", strip=True).upper()
                if (
                    t_text
                    and len(t_text) > 2
                    and not re.search(r"\d{1,2}:\d{2}", t_text)
                    and "PENDIENTE" not in t_text
                    and "SORTEADO" not in t_text
                ):
                    if t_text not in ["WINBIG", "RESULTADOS"]:
                        nombre_loteria = t_text
                        break

            matches_res = re.findall(
                r"(\d{1,2})\s*[-–]?\s*([A-ZÁÉÍÓÚÑa-zñáéíóú]+(?:\s+[A-ZÁÉÍÓÚÑa-zñáéíóú]+)?)",
                texto_tarjeta,
            )

            animales_encontrados = []
            for num_str, nom_str in matches_res:
                num_limpio = num_str.strip()
                nom_limpio = limpiar_texto(nom_str).upper()
                if (
                    num_limpio.isdigit()
                    and 0 <= int(num_limpio) <= 36
                    and nom_limpio not in ["AM", "PM", "SORTEADO", "PENDIENTE"]
                ):
                    animal_nombre = ANIMALITOS_DICT.get(
                        num_limpio.lstrip("0") if num_limpio != "00" else "00",
                        nom_limpio,
                    )
                    if num_limpio == "0":
                        animal_nombre = "Delfín"
                    elif num_limpio == "00":
                        animal_nombre = "Ballena"

                    par = (num_limpio, animal_nombre)
                    if par not in animales_encontrados:
                        animales_encontrados.append(par)

            # Determinar si es la lotería especial multi-resultado (Ruleta Activa ESP) o estándar
            es_especial = "ESP" in nombre_loteria.upper() or "ESPECIAL" in nombre_loteria.upper()

            if es_especial:
                if len(animales_encontrados) >= 4:
                    a = animales_encontrados[0]
                    b = animales_encontrados[1]
                    c = animales_encontrados[2]
                    d = animales_encontrados[3]

                    clave_slot = (nombre_loteria.upper().strip(), hora.upper().strip())

                    if primera_ejecucion:
                        horarios_enviados_hoy.add(clave_slot)
                    else:
                        if clave_slot not in horarios_enviados_hoy:
                            item_dict = {
                                "tipo": "especial",
                                "loteria": nombre_loteria,
                                "hora": hora,
                                "a": a,
                                "b": b,
                                "c": c,
                                "d": d,
                            }
                            if item_dict not in nuevos_encontrados:
                                nuevos_encontrados.append(item_dict)
                                horarios_enviados_hoy.add(clave_slot)
                                guardar_estado_disco()
                                print(f"✨ Nuevo resultado especial A-B-C-D detectado: {nombre_loteria} - {hora}")

                                if regalos_hoy:
                                    for item_animal in [a, b, c, d]:
                                        num_limpio = item_animal[0]
                                        for r_num, r_animal in regalos_hoy:
                                            if (
                                                num_limpio.lstrip("0") == r_num.lstrip("0")
                                                or num_limpio == r_num
                                            ):
                                                mensaje_acierto = (
                                                    "🎉🎉 ¡ACERTAMOS! 🎉🎉\n\n"
                                                    "✅ 🎁 Regalo del Día\n\n"
                                                    f"🎯 {num_limpio} - {item_animal[1]}\n"
                                                    f"🎲 🎰 {nombre_loteria}\n"
                                                    f"🕒 {hora}\n\n"
                                                    "🍀 ¡Felicidades a todos los que confiaron en Agencia Harold José!"
                                                )
                                                enviar_telegram_con_botones(mensaje_acierto)
                                                break
            else:
                if len(animales_encontrados) >= 1:
                    a = animales_encontrados[0]
                    clave_slot = (nombre_loteria.upper().strip(), hora.upper().strip())

                    if primera_ejecucion:
                        horarios_enviados_hoy.add(clave_slot)
                    else:
                        if clave_slot not in horarios_enviados_hoy:
                            item_dict = {
                                "tipo": "normal",
                                "loteria": nombre_loteria,
                                "hora": hora,
                                "a": a,
                            }
                            if item_dict not in nuevos_encontrados:
                                nuevos_encontrados.append(item_dict)
                                horarios_enviados_hoy.add(clave_slot)
                                guardar_estado_disco()
                                print(f"✨ Nuevo resultado estándar detectado: {nombre_loteria} - {hora} -> {a[0]} - {a[1]}")

                                if regalos_hoy:
                                    num_limpio = a[0]
                                    for r_num, r_animal in regalos_hoy:
                                        if (
                                            num_limpio.lstrip("0") == r_num.lstrip("0")
                                            or num_limpio == r_num
                                        ):
                                            mensaje_acierto = (
                                                "🎉🎉 ¡ACERTAMOS! 🎉🎉\n\n"
                                                "✅ 🎁 Regalo del Día\n\n"
                                                f"🎯 {num_limpio} - {a[1]}\n"
                                                f"🎲 🎰 {nombre_loteria}\n"
                                                f"🕒 {hora}\n\n"
                                                "🍀 ¡Felicidades a todos los que confiaron en Agencia Harold José!"
                                            )
                                            enviar_telegram_con_botones(mensaje_acierto)
                                            break

        if primera_ejecucion:
            primera_ejecucion = False
            guardar_estado_disco()
            print(f"✅ Sincronización inicial completada. Slots bloqueados en memoria: {len(horarios_enviados_hoy)}")
            return

        if nuevos_encontrados:
            for item_nuevo in nuevos_encontrados:
                if item_nuevo.get("tipo") == "especial":
                    mensaje = (
                        "🎯 CENTRO DE APUESTAS HAROLD JOSÉ 🎯\n"
                        f"🎰 {item_nuevo['loteria']}\n"
                        f"🕒 {item_nuevo['hora']}  \n"
                        f"A-{item_nuevo['a'][0]} - {item_nuevo['a'][1]}\n"
                        f"B-{item_nuevo['b'][0]} - {item_nuevo['b'][1]}\n"
                        f"C-{item_nuevo['c'][0]} - {item_nuevo['c'][1]}\n"
                        f"D-{item_nuevo['d'][0]} - {item_nuevo['d'][1]}\n"
                        f"{ENLACE_CANAL}"
                    )
                else:
                    mensaje = (
                        "🎯 CENTRO DE APUESTAS HAROLD JOSÉ 🎯\n"
                        f"🎰 {item_nuevo['loteria']}\n"
                        f"🕒 {item_nuevo['hora']}\n"
                        f"🎯 {item_nuevo['a'][0]} - {item_nuevo['a'][1]}\n"
                        f"{ENLACE_CANAL}"
                    )
                enviar_telegram_con_botones(mensaje)
                time.sleep(2)

    except Exception as e:
        print(f"⚠️ Error detallado en verificación de resultados: {e}")
        traceback.print_exc()


def procesar_activacion_taquilla(message):
    global taquilla_activa_hoy, imagen_taquilla_file_id
    caption = message.caption or message.text or ""
    if "taquilla activa" in caption.lower():
        if message.photo:
            taquilla_activa_hoy = True
            imagen_taquilla_file_id = message.photo[-1].file_id
            guardar_estado_disco()
            enviar_telegram_foto(imagen_taquilla_file_id, caption_taquilla)
            print("✅ Taquilla activada y publicada con la imagen adjunta.")
        else:
            taquilla_activa_hoy = True
            guardar_estado_disco()
            enviar_telegram(caption_taquilla, disable_web_preview=True)
            print("✅ Taquilla activada por texto.")


@bot.message_handler(content_types=["photo"])
def handle_photos(message):
    procesar_activacion_taquilla(message)


@bot.channel_post_handler(content_types=["photo"])
def handle_channel_photos(message):
    procesar_activacion_taquilla(message)


@bot.message_handler(func=lambda msg: True, content_types=["text"])
def handle_text_messages(message):
    if "taquilla activa" in (message.text or "").lower():
        global taquilla_activa_hoy
        taquilla_activa_hoy = True
        guardar_estado_disco()
        if imagen_taquilla_file_id:
            enviar_telegram_foto(imagen_taquilla_file_id, caption_taquilla)
        else:
            enviar_telegram(caption_taquilla, disable_web_preview=True)
        print("✅ Taquilla activada por texto.")


def procesar_limpieza_y_envio_animalitos(text):
    texto_lower = text.lower()
    if (
        "resultado programado" in texto_lower
        or "resultados animalitos" in texto_lower
    ):
        clave_corte = (
            "resultados animalitos"
            if "resultados animalitos" in texto_lower
            else "resultado programado"
        )
        pos = texto_lower.find(clave_corte)
        texto_limpio = text[pos:].strip()
        mensaje_completo = f"{HEADER_RESULTADOS}\n\n{texto_limpio}"
        enviar_telegram_con_botones(mensaje_completo)
        print("✅ Mensaje programado / animalitos enviado con éxito.")
        return True
    return False


@bot.channel_post_handler(func=lambda message: True)
def handle_channel_posts(message):
    text = message.text or message.caption or ""
    procesar_limpieza_y_envio_animalitos(text)


@bot.message_handler(func=lambda message: True, content_types=["text"])
def handle_direct_messages_animalitos(message):
    text = message.text or ""
    procesar_limpieza_y_envio_animalitos(text)


def iniciar_scheduler():
    scheduler.add_job(limpiar_memoria_diaria, "cron", hour=0, minute=0)
    scheduler.add_job(enviar_saludo_madrugada, "cron", hour=6, minute=30)
    scheduler.add_job(enviar_piramide_diaria, "cron", hour=6, minute=31)
    scheduler.add_job(enviar_regalos_agencia, "cron", hour=6, minute=45)
    scheduler.add_job(enviar_saludo_matutino, "cron", hour=7, minute=0)
    scheduler.add_job(enviar_tasa_dolar, "cron", hour=6, minute=30)
    scheduler.add_job(enviar_tasa_dolar, "cron", hour=18, minute=30)

    scheduler.add_job(enviar_anuncio_publicitario, "cron", hour=7, minute=0)
    scheduler.add_job(enviar_anuncio_publicitario, "cron", hour=15, minute=0)
    scheduler.add_job(enviar_anuncio_publicitario, "cron", hour=18, minute=0)

    scheduler.add_job(enviar_anuncio_cashea, "cron", hour=9, minute=0)
    scheduler.add_job(enviar_anuncio_cashea, "cron", hour=10, minute=30)
    scheduler.add_job(enviar_anuncio_cashea, "cron", hour=12, minute=30)

    scheduler.add_job(enviar_aviso_tiempo_cumplido, "cron", hour="7-19", minute=55)

    scheduler.add_job(tarea_envio_programado_taquilla, "cron", hour=15, minute=0)

    scheduler.add_job(tarea_minuto_diez, "cron", hour="7-17", minute=10)
    scheduler.add_job(enviar_mensaje_cierre, "cron", hour=21, minute=10)
    scheduler.add_job(verificar_resultados, "interval", seconds=30)

    scheduler.start()
    verificar_resultados()


def iniciar_polling_bot():
    while True:
        try:
            bot.infinity_polling(
                skip_pending=True,
                interval=3,
                timeout=20,
                allowed_updates=[
                    "message",
                    "edited_message",
                    "channel_post",
                    "edited_channel_post",
                ],
            )
        except Exception as e:
            print(f"⚠️ Error en polling: {e}")
            time.sleep(5)


if __name__ == "__main__":
    try:
        print("🚀 Iniciando aplicación principal...")
        t_schedule = Thread(target=iniciar_scheduler)
        t_schedule.daemon = True
        t_schedule.start()

        t_bot = Thread(target=iniciar_polling_bot)
        t_bot.daemon = True
        t_bot.start()
        print("✅ Hilos iniciados correctamente.")

        port = int(os.environ.get("PORT", 5000))
        app.run(host="0.0.0.0", port=port, use_reloader=False)
    except Exception as e:
        print(f"❌ Error crítico en ejecución principal: {e}")
        traceback.print_exc()
