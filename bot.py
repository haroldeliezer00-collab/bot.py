from datetime import datetime
import json
import logging
import os
import random
import re
import socket
import sqlite3
from threading import Thread
import time
import traceback
from apscheduler.schedulers.background import BackgroundScheduler
from bs4 import BeautifulSoup
from flask import Flask, request
import requests
import urllib3.util.connection as urllib3_cn


# Forzar IPv4 en toda la aplicación
def allowed_gai_family():
  return socket.AF_INET


urllib3_cn.allowed_gai_family = allowed_gai_family

import telebot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup
import urllib3

# Configuración de logging profesional para Render
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)

logging.getLogger("TeleBot").setLevel(logging.CRITICAL)

# Forzar la zona horaria de Venezuela de forma segura
os.environ["TZ"] = "America/Caracas"
try:
  time.tzset()
except Exception as e:
  logging.warning(f"⚠️ Nota sobre tzset: {e}")

# Desactivar advertencias de certificados SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Credenciales, Puente Cloudflare y canal principal configurado
TOKEN = os.environ.get(
    "TELEGRAM_TOKEN", "8733552499:AAHt-U4OjLBH4mSNU0E4CXEYpz4gnSbVYak"
)
TG_API_BASE = "https://telegram-harold.criptoanubis.workers.dev"
CANAL = "@resultadosagharoldjose"
ENLACE_CANAL = "https://t.me/resultadosagharoldjose"
ENLACE_POLLAS = "https://t.me/pollasydupletas"

bot = telebot.TeleBot(TOKEN, threaded=False)
scheduler = BackgroundScheduler(timezone="America/Caracas")

URL_LOTERIA = "https://lotery.winbigvzla.com/resultados"
URL_BCV = "https://www.bcv.org.ve/"
STATE_FILE = "bot_state.json"
DB_FILE = "bot_results.db"

# Sesión HTTP optimizada para reuso de conexiones
http_session = requests.Session()
http_session.headers.update(
    {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"}
)

# Control estricto anti-duplicados y memoria
primera_ejecucion = True
ultima_hora_polla = None
servicios_iniciados = False

taquilla_activa_hoy = False
imagen_taquilla_file_id = None
imagen_cashea_file_id = None
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


def inicializar_db():
  """Inicializa la base de datos SQLite persistente para control de duplicados."""
  try:
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
            CREATE TABLE IF NOT EXISTS sent_results (
                result_id TEXT PRIMARY KEY,
                fecha TEXT,
                agencia TEXT,
                loteria TEXT,
                hora TEXT,
                resultado TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    conn.commit()
    conn.close()
    logging.info("🗄️ Base de datos SQLite inicializada correctamente.")
  except Exception as e:
    logging.error(f"❌ Error inicializando base de datos SQLite: {e}")


def verificar_y_registrar_resultado(
    fecha, agencia, loteria, hora, resultado
):
  """Función central atómica para evitar duplicados mediante ID único y SQLite."""
  f_norm = limpiar_texto(str(fecha)).upper()
  ag_norm = normalizar_nombre(str(agencia))
  lot_norm = normalizar_nombre(str(loteria))
  h_norm = limpiar_texto(str(hora)).upper()
  res_norm = limpiar_texto(str(resultado)).upper()

  result_id = f"{f_norm}_{ag_norm}_{lot_norm}_{h_norm}_{res_norm}"

  try:
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        """
            INSERT OR IGNORE INTO sent_results (result_id, fecha, agencia, loteria, hora, resultado)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
        (result_id, f_norm, ag_norm, lot_norm, h_norm, res_norm),
    )
    conn.commit()

    if cursor.rowcount > 0:
      logging.info(
          f"[NEW RESULT] Resultado nuevo detectado: {lot_norm} | {h_norm} |"
          f" {res_norm}"
      )
      return True
    return False
  except Exception as e:
    logging.error(f"[RESULT ERROR] Error SQLite: {e}")
    return False
  finally:
    if "conn" in locals() and conn:
      conn.close()


def es_hora_actual_valida(hora_sorteo_str, tolerancia_minutos=45):
  """Solo permite publicar resultados de la hora actual en Venezuela (evita resultados viejos tras reinicios)."""
  try:
    ahora = datetime.now()
    hora_limpia = re.sub(r"\s+", " ", hora_sorteo_str.strip().upper())
    dt_sorteo = datetime.strptime(hora_limpia, "%I:%M %p").replace(
        year=ahora.year, month=ahora.month, day=ahora.day
    )
    diferencia_minutos = (ahora - dt_sorteo).total_seconds() / 60.0
    return -5 <= diferencia_minutos <= tolerancia_minutos
  except Exception:
    return False


def guardar_respaldo_en_telegram(clave, file_id):
  """Guarda los file_id en la nube de Telegram para que sobrevivan a los reinicios de Render."""
  for _ in range(2):
    try:
      url_get = f"{TG_API_BASE}/bot{TOKEN}/getMyCommands"
      resp = http_session.get(url_get, timeout=8).json()
      comandos_actuales = resp.get("result", [])

      nuevos_comandos = [
          c for c in comandos_actuales if not c["command"].startswith("img_")
      ]

      cashea_id = file_id if clave == "cashea" else imagen_cashea_file_id
      taquilla_id = file_id if clave == "taquilla" else imagen_taquilla_file_id

      if cashea_id:
        nuevos_comandos.append(
            {"command": "img_cashea", "description": cashea_id}
        )
      if taquilla_id:
        hoy_tag = datetime.now().strftime("%Y%m%d")
        nuevos_comandos.append({
            "command": "img_taquilla",
            "description": f"{hoy_tag}|{taquilla_id}",
        })

      url_set = f"{TG_API_BASE}/bot{TOKEN}/setMyCommands"
      r_set = http_session.post(
          url_set, json={"commands": nuevos_comandos}, timeout=8
      )
      if r_set.status_code == 200:
        logging.info(f"☁️ Respaldo en nube de Telegram actualizado: {clave}")
        return True
    except Exception:
      time.sleep(1)
  return False


def recuperar_respaldo_de_telegram():
  """Recupera automáticamente las fotos guardadas desde Telegram al iniciar Render."""
  global imagen_cashea_file_id, imagen_taquilla_file_id, taquilla_activa_hoy
  try:
    url_get = f"{TG_API_BASE}/bot{TOKEN}/getMyCommands"
    resp = http_session.get(url_get, timeout=8).json()
    if not resp.get("ok"):
      return
    comandos = resp.get("result", [])
    hoy_tag = datetime.now().strftime("%Y%m%d")

    for c in comandos:
      if c["command"] == "img_cashea" and c.get("description"):
        imagen_cashea_file_id = c["description"].strip()
        logging.info("☁️ Imagen de Cashea recuperada desde Telegram.")
      elif c["command"] == "img_taquilla" and c.get("description"):
        partes = c["description"].strip().split("|", 1)
        if len(partes) == 2 and partes[0] == hoy_tag:
          imagen_taquilla_file_id = partes[1]
          taquilla_activa_hoy = True
          logging.info("☁️ Imagen de Taquilla Activa recuperada desde Telegram.")
  except Exception as e:
    logging.warning(f"⚠️ Nota recuperando respaldo de Telegram: {e}")


def cargar_estado_disco():
  global primera_ejecucion, ultima_hora_polla, taquilla_activa_hoy, imagen_taquilla_file_id, imagen_cashea_file_id, regalos_hoy
  recuperar_respaldo_de_telegram()

  if os.path.exists(STATE_FILE):
    try:
      with open(STATE_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        saved_cashea = data.get("imagen_cashea", None)
        if saved_cashea and not imagen_cashea_file_id:
          imagen_cashea_file_id = saved_cashea

        hoy_str = datetime.now().strftime("%Y-%m-%d")
        if data.get("fecha") == hoy_str:
          primera_ejecucion = data.get("primera_ejecucion", False)
          if data.get("ultima_polla_hora"):
            h_data = data.get("ultima_polla_hora")
            ultima_hora_polla = (
                datetime.strptime(h_data[0], "%Y-%m-%d").date(),
                h_data[1],
            )
          if data.get("taquilla_activa"):
            taquilla_activa_hoy = True
          if data.get("imagen_taquilla"):
            imagen_taquilla_file_id = data.get("imagen_taquilla")
          regalos_hoy = data.get("regalos_hoy", [])
          return
    except Exception:
      pass
  primera_ejecucion = True
  ultima_hora_polla = None
  regalos_hoy = []


def guardar_estado_disco():
  try:
    hoy_str = datetime.now().strftime("%Y-%m-%d")
    polla_serializable = None
    if ultima_hora_polla:
      polla_serializable = [str(ultima_hora_polla[0]), ultima_hora_polla[1]]

    data = {
        "fecha": hoy_str,
        "primera_ejecucion": primera_ejecucion,
        "ultima_polla_hora": polla_serializable,
        "taquilla_activa": taquilla_activa_hoy,
        "imagen_taquilla": imagen_taquilla_file_id,
        "imagen_cashea": imagen_cashea_file_id,
        "regalos_hoy": regalos_hoy,
    }
    with open(STATE_FILE, "w", encoding="utf-8") as f:
      json.dump(data, f, ensure_ascii=False, indent=2)
  except Exception:
    pass


inicializar_db()
cargar_estado_disco()

caption_taquilla = (
    "✅ AGENCIA HAROLD JOSÉ ACTIVA ✅\n"
    "Ya estamos operativos brindando la mejor atención. Calidad, respaldo y"
    " rapidez en cada una de todas tus solicitudes.\n\n"
    "📲 Envía tus jugadas:\n"
    "(Comprobante de pago / Lotería / monto / Hora)\n\n"
    "📖 Consulta nuestro reglamento aquí:\n"
    "https://wa.me/p/33319103291071105/584124489363\n"
    "🚀 Agiliza tu proceso aquí:"
    " https://wa.me/p/24724650613899486/584124489363\n\n"
    "RESULTADOS AUTOMÁTICOS\n"
    f"{ENLACE_CANAL}\n\n"
    "¡Mucho éxito en la jornada de hoy! 🍀✨"
)

TEXTO_PUBLICITARIO = (
    "🔥 ¡NUEVO EN AGENCIA HAROLD JOSÉ! 🔥\n"
    "💥 ¡AHORA TENEMOS CACHÉA! 💥\n"
    "🎰 TODAS TUS LOTERÍAS EN UN SOLO LUGAR\n"
    "💰 Ruletas • Triples • Tripletas • Pollas • Bingos\n"
    "🛡 6 AÑOS DE CONFIANZA EN TODA VENEZUELA\n"
    "💳 Pago Móvil y Transferencias\n"
    "🚀 Cupos altos para jugar en grande\n"
    "👇 REVISA TODO LO QUE TENEMOS DISPONIBLE 👇\n"
    "➖➖➖➖➖➖➖➖➖➖\n"
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
    "• Calamar Millonario A-B\n"
    "• Lotto Pantera\n"
    "• Loto Animalito\n"
    "➖➖➖➖➖➖➖➖➖➖\n"
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
    "➖➖➖➖➖➖➖➖➖➖\n"
    "🎰 TRIPLETAS DISPONIBLES 🎰\n"
    "⚠️ SÓLO SE SELLA HASTA LAS 8:50 AM\n"
    "🚫 NO VENDO BASES\n"
    "• Lotto Activo | La Granjita | Selva Plus\n"
    "• Guácharo Activo | Lotto Inter | Cazaloton\n"
    "• Guacharito Millonario | Monje Millonario | Tropi Gana | Cóndor Gana |"
    " Granja Millonaria | Fruti Gana | Granjazo | Lotto Max | Ruleta Activa |"
    " Guaca37....\n"
    "➖➖➖➖➖➖➖➖➖➖\n"
    "🎊 POLLAS Y DUPLETAS 🎊\n"
    "• Polla Animaniacs | Mini Polla\n"
    "• Pozo Millonario | Super Polla\n"
    "• Super Seven | Micro Polla\n"
    "• Sumatoria Niño de Oro\n"
    "• Polla por Puntos | Dupletas y más...\n"
    "➖➖➖➖➖➖➖➖➖➖\n"
    "🌐 BINGOS DISPONIBLES 🌐\n"
    "• BINGO MILLONARIO PLUS\n"
    "➖➖➖➖➖➖➖➖➖➖\n"
    "📢 ÚNETE A NUESTRA COMUNIDAD OFICIAL 🎲🔥\n"
    "📲 Entra a nuestro canal de Telegram y consulta todos los resultados:\n"
    f"👉 {ENLACE_CANAL}\n"
    "🔥 AGENCIA HAROLD JOSÉ 🔥\n"
    "💰 JUEGA CON CONFIANZA"
)

TEXTO_CASHEA = (
    "✨ ¡Tu jugada favorita ahora con facilidades de pago! 💜🔥\n\n"
    "En la AGENCIA HAROLD JOSÉ te ayudamos a ganar: juega hoy, paga después con"
    " Cashea y llévate ese premio que tanto esperas. 💸\n\n"
    "📲 Activa tu jugada escribiendo al WhatsApp: 04124489363. ¡Atención rápida y"
    " segura! ⚡"
)

HEADER_RESULTADOS = (
    "AGENCIA HAROLD JOSÉ\n"
    "SEGURIDAD Y CONFIANZA\n"
    "RESULTADOS OFICIALES\n"
    "📲JUEGA AQUI👇👇\n"
    "WHATSAPP: 04124489363\n\n"
    f"📢 CANAL DE RESULTADOS:\n{ENLACE_CANAL}"
)

app = Flask("")


def probar_conexion_telegram():
  try:
    r = http_session.get(
        f"{TG_API_BASE}/bot{TOKEN}/getMe", timeout=6
    )
    if r.status_code == 200 and r.json().get("ok"):
      return "CONECTADO 🟢 (Vía Cloudflare Worker ultrarrápido)"
    return f"ERROR 🔴 (Código {r.status_code}: {r.text[:60]})"
  except Exception as e:
    return f"TIMEOUT 🔴 ({e})"


@app.route("/")
def home():
  estado_tag = (
      "ACTIVADA 🟢 (Trabajando hoy)"
      if taquilla_activa_hoy
      else "DESACTIVADA 🔴 (No laborando)"
  )
  cashea_tag = (
      "CONFIGURADA 🟢 (Guardada en nube Telegram)"
      if imagen_cashea_file_id
      else "SOLO TEXTO 🟡 (Sin imagen aún)"
  )
  tg_status = probar_conexion_telegram()

  return (
      f"¡El bot de resultados de la AGENCIA HAROLD JOSÉ está activo en el canal"
      f" oficial {CANAL}!<br><br>"
      f"<b>Conexión Render ↔ Telegram:</b> {tg_status}<br>"
      f"<b>Estado del aviso de taquilla de hoy:</b> {estado_tag}<br>"
      f"<b>Estado de la imagen de Cashea:</b> {cashea_tag}<br><br>"
      "<b>Subir Imagen Directa:</b><br>"
      "<form action='/subir_imagen' method='post' enctype='multipart/form-data'>"
      "<select name='tipo'><option value='cashea'>Imagen Cashea (Permanente)</option>"
      "<option value='taquilla'>Imagen Taquilla Activa (Hoy + 3PM)</option></select> "
      "<input type='file' name='foto' accept='image/*' required> "
      "<button type='submit'>Guardar y Publicar</button></form><br>"
      "<b>Enlaces de prueba rápida (Test instantáneo):</b><br>"
      "👉 <a href='/test/madrugada'>Probar Saludo de Madrugada (6:30 AM)</a><br>"
      "👉 <a href='/test/piramide'>Probar Pirámide Numérica con Sumas por Fila (6:31 AM)</a><br>"
      "👉 <a href='/test/regalos'>Probar Regalos de la Agencia (6:45 AM)</a><br>"
      "👉 <a href='/test/saludo'>Probar Saludo Matutino (7:00 AM)</a><br>"
      "👉 <a href='/test/publicidad'>Probar Aviso Publicitario (7am/3pm/6pm)</a><br>"
      "👉 <a href='/test/cashea'>Probar Aviso con Botones Cashea (9am a 4:30 pm)</a><br>"
      "👉 <a href='/test/tiempocumplido'>Probar Tiempo Cumplido (Minuto 55)</a><br>"
      "👉 <a href='/test/bcv'>Probar Tasa Oficial BCV</a><br>"
      "👉 <a href='/test/taquilla_manual'>Probar Envío Manual de Taquilla Activa</a><br>"
      "👉 <a href='/test/pollas'>Probar Aviso de Pollas (Minuto 10)</a><br>"
      "👉 <a href='/test/resultados'>Forzar Revisión de Resultados Individuales</a><br>"
      "👉 <a href='/test/cierre'>Probar Mensaje de Cierre (9:10 PM)</a>"
  )


@app.route("/subir_imagen", methods=["POST"])
def subir_imagen():
  global imagen_cashea_file_id, imagen_taquilla_file_id, taquilla_activa_hoy
  tipo = request.form.get("tipo")
  foto = request.files.get("foto")
  if not foto:
    return "No seleccionaste ninguna imagen.", 400

  try:
    url = f"{TG_API_BASE}/bot{TOKEN}/sendPhoto"
    caption_tmp = (
        caption_taquilla if tipo == "taquilla" else "Actualizando imagen Cashea..."
    )
    files = {"photo": (foto.filename, foto.read(), foto.content_type)}
    data = {"chat_id": CANAL, "caption": caption_tmp}

    resp = http_session.post(url, data=data, files=files, timeout=15).json()
    if not resp.get("ok"):
      return f"Error subiendo a Telegram: {resp}. <a href='/'>Volver</a>", 500

    file_id = resp["result"]["photo"][-1]["file_id"]
    msg_id = resp["result"]["message_id"]

    if tipo == "cashea":
      imagen_cashea_file_id = file_id
      guardar_estado_disco()
      guardar_respaldo_en_telegram("cashea", file_id)
      http_session.post(
          f"{TG_API_BASE}/bot{TOKEN}/deleteMessage",
          json={"chat_id": CANAL, "message_id": msg_id},
          timeout=8,
      )
      return "✅ ¡Imagen de Cashea guardada permanentemente en la nube! <a href='/'>Volver</a>"
    else:
      taquilla_activa_hoy = True
      imagen_taquilla_file_id = file_id
      guardar_estado_disco()
      guardar_respaldo_en_telegram("taquilla", file_id)
      return "✅ ¡Taquilla Activa publicada en el canal y programada para las 3:00 PM! <a href='/'>Volver</a>"
  except Exception as e:
    return f"❌ Error subiendo imagen: {e}. <a href='/'>Volver</a>", 504


def ejecutar_en_segundo_plano(func):
  Thread(target=func, daemon=True).start()
  return "✅ Orden enviada al bot (revisa tu canal de Telegram en 2 segundos). <a href='/'>Volver</a>"


@app.route("/test/madrugada")
def test_madrugada():
  return ejecutar_en_segundo_plano(enviar_saludo_madrugada)


@app.route("/test/piramide")
def test_piramide():
  return ejecutar_en_segundo_plano(enviar_piramide_diaria)


@app.route("/test/regalos")
def test_regalos():
  return ejecutar_en_segundo_plano(enviar_regalos_agencia)


@app.route("/test/saludo")
def test_saludo():
  return ejecutar_en_segundo_plano(enviar_saludo_matutino)


@app.route("/test/publicidad")
def test_publicidad():
  return ejecutar_en_segundo_plano(enviar_anuncio_publicitario)


@app.route("/test/cashea")
def test_cashea():
  return ejecutar_en_segundo_plano(enviar_anuncio_cashea)


@app.route("/test/tiempocumplido")
def test_tiempocumplido():
  return ejecutar_en_segundo_plano(enviar_aviso_tiempo_cumplido)


@app.route("/test/bcv")
def test_bcv():
  return ejecutar_en_segundo_plano(enviar_tasa_dolar)


@app.route("/test/taquilla_manual")
def test_taquilla_manual():
  def _run():
    global taquilla_activa_hoy, imagen_taquilla_file_id
    taquilla_activa_hoy = True
    guardar_estado_disco()
    if imagen_taquilla_file_id:
      enviar_telegram_foto(imagen_taquilla_file_id, caption_taquilla)
    else:
      enviar_telegram(caption_taquilla, disable_web_preview=True)

  return ejecutar_en_segundo_plano(_run)


@app.route("/test/pollas")
def test_pollas():
  return ejecutar_en_segundo_plano(tarea_minuto_diez)


@app.route("/test/resultados")
def test_resultados():
  return ejecutar_en_segundo_plano(verificar_resultados)


@app.route("/test/cierre")
def test_cierre():
  return ejecutar_en_segundo_plano(enviar_mensaje_cierre)


def limpiar_texto(texto):
  return " ".join(texto.split())


def normalizar_nombre(texto):
  return re.sub(r"[^A-Z0-9]", "", texto.upper())


def enviar_telegram(mensaje, disable_web_preview=True):
  url = f"{TG_API_BASE}/bot{TOKEN}/sendMessage"
  payload = {
      "chat_id": CANAL,
      "text": mensaje,
      "parse_mode": "Markdown",
      "disable_web_page_preview": disable_web_preview,
  }
  for intento in range(1, 3):
    try:
      response = http_session.post(url, json=payload, timeout=10)
      if response.status_code == 200:
        logging.info("✅ Mensaje enviado correctamente al canal.")
        return True
      logging.warning(
          f"⚠️ Error al enviar al canal (intento {intento}/2): {response.text}"
      )
    except Exception as e:
      logging.warning(
          f"⚠️ Excepción de conexión con Telegram (intento {intento}/2): {e}"
      )
    time.sleep(1)
  return False


def enviar_telegram_con_botones(mensaje, reply_markup_dict):
  url = f"{TG_API_BASE}/bot{TOKEN}/sendMessage"
  payload = {
      "chat_id": CANAL,
      "text": mensaje,
      "parse_mode": "Markdown",
      "reply_markup": reply_markup_dict,
      "disable_web_page_preview": True,
  }
  for intento in range(1, 3):
    try:
      response = http_session.post(url, json=payload, timeout=10)
      if response.status_code == 200:
        return True
      logging.warning(
          f"⚠️ Error al enviar mensaje con botones (intento {intento}/2):"
          f" {response.text}"
      )
    except Exception as e:
      logging.warning(
          f"⚠️ Excepción al enviar mensaje con botones (intento {intento}/2): {e}"
      )
    time.sleep(1)
  return False


def enviar_telegram_foto(photo_id, caption):
  url = f"{TG_API_BASE}/bot{TOKEN}/sendPhoto"
  payload = {
      "chat_id": CANAL,
      "photo": photo_id,
      "caption": caption,
      "parse_mode": "Markdown",
  }
  for intento in range(1, 3):
    try:
      response = http_session.post(url, json=payload, timeout=12)
      if response.status_code == 200:
        return True
      logging.warning(
          f"⚠️ Error al enviar foto al canal (intento {intento}/2):"
          f" {response.text}"
      )
    except Exception as e:
      logging.warning(
          f"⚠️ Excepción al enviar foto (intento {intento}/2): {e}"
      )
    time.sleep(1)
  return False


def enviar_telegram_foto_con_botones(photo_id, caption, reply_markup_dict=None):
  url = f"{TG_API_BASE}/bot{TOKEN}/sendPhoto"
  payload = {
      "chat_id": CANAL,
      "photo": photo_id,
      "caption": caption,
      "parse_mode": "Markdown",
  }
  if reply_markup_dict:
    payload["reply_markup"] = reply_markup_dict
  for intento in range(1, 3):
    try:
      response = http_session.post(url, json=payload, timeout=12)
      if response.status_code == 200:
        return True
      logging.warning(
          f"⚠️ Error al enviar foto con botones (intento {intento}/2):"
          f" {response.text}"
      )
    except Exception as e:
      logging.warning(
          f"⚠️ Excepción al enviar foto con botones (intento {intento}/2): {e}"
      )
    time.sleep(1)
  return False


def limpiar_memoria_diaria():
  global primera_ejecucion, taquilla_activa_hoy, imagen_taquilla_file_id, ultima_hora_polla, regalos_hoy
  primera_ejecucion = True
  taquilla_activa_hoy = False
  imagen_taquilla_file_id = None
  ultima_hora_polla = None
  regalos_hoy = []
  guardar_estado_disco()
  guardar_respaldo_en_telegram("cashea", imagen_cashea_file_id)
  logging.info(
      "🧹 Memoria diaria limpiada. La imagen de Cashea se mantiene en la nube."
  )


def enviar_saludo_madrugada():
  enviar_telegram(
      "🎯 AGENCIA HAROLD JOSÉ 🎯\n\n🌅 ¡Despertando con la mejor energía y"
      " listos para ganar! 🌅\n\nComenzamos este nuevo día activos y"
      " enfocados. ¡Que la suerte esté de nuestro lado! 🍀🔥",
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
    c_rand = (
        f"{r_val:02d}" if r_val != 0 else ("0" if rnd.random() > 0.5 else "00")
    )
    if c_rand not in unique_candidates:
      unique_candidates.append(c_rand)

  d1 = f"{unique_candidates[0]}-{unique_candidates[1]}-{unique_candidates[2]}"
  d2 = f"{unique_candidates[3]}-{unique_candidates[4]}-{unique_candidates[5]}"

  return (
      "🎯 AGENCIA HAROLD JOSÉ 🎯\n📢 REPORTE TÁCTICO - LA PIRÁMIDE 📢\n\n"
      f"📅 Fecha: {fecha_str}\nAnálisis matemático actualizado y listo para"
      f" la jugada. ¡A asegurar posición:\n\n{cuerpo_piramide}\n\n📊 SUMA POR"
      f" FILA:\n{bloque_sumas}\n\n🔥 DATOS CLAVES PARA HOY:\n📌"
      f" {d1}\n📌 {d2}\n\n⚡ ¡La precisión y los números hablan por sí"
      " solos! ¡Juega con confianza y gana con nosotros! 🍀 💰"
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
    num_str = (
        f"{num:02d}" if num != 0 else ("0" if rnd.random() > 0.5 else "00")
    )
    if num == 0:
      num_str = "0"
    animal = ANIMALITOS_DICT.get(
        num_str, ANIMALITOS_DICT.get(str(num), "Animal")
    )
    regalos_hoy.append((num_str, animal))

  guardar_estado_disco()

  r1 = f"{regalos_hoy[0][0]} - {regalos_hoy[0][1]}"
  r2 = f"{regalos_hoy[1][0]} - {regalos_hoy[1][1]}"
  r3 = f"{regalos_hoy[2][0]} - {regalos_hoy[2][1]}"

  return (
      "🎁 LOS REGALOS DE LA AGENCIA HAROLD JOSÉ 🎁\n"
      f"📅 Fecha: {fecha_str}\n\n¡Los fijos recomendados para reventar la"
      f" banca hoy:\n\n⭐ 1er Regalo: {r1}\n⭐ 2do Regalo: {r2}\n⭐ 3er Regalo:"
      f" {r3}\n\n📲 WHATSAPP: 04124489363\n{ENLACE_CANAL}\n\n¡Mucha suerte en"
      " sus jugadas! 🍀✨"
  )


def enviar_regalos_agencia():
  enviar_telegram(generar_regalos_agencia(), disable_web_preview=True)


def enviar_saludo_matutino():
  enviar_telegram(
      "🎯 AGENCIA HAROLD JOSÉ 🎯\n\n🌅 ¡Buenos días a todos! 🌅\n\nYa arrancamos"
      " un nuevo día con la mejor energía. Estaremos compartiendo todos los"
      " resultados de los animalitos a medida que vayan saliendo.\n\n📢 Nuestros"
      " canales oficiales:\n🎟️ Catálogo y WhatsApp:"
      " https://wa.me/c/584124489363\n📸 Instagram:"
      " https://www.instagram.com/agenciaharoldjose (@agenciaharoldjose)\n📘"
      " Facebook: https://www.facebook.com/agharoldjosee\n💬 Canal de WhatsApp:"
      " https://whatsapp.com/channel/0029Vaza7YIGzzKJq7as7s1T\n\n¡Mucha suerte"
      " en sus jugadas el día de hoy y a ganar! 🍀🔥",
      disable_web_preview=True,
  )


def enviar_anuncio_publicitario():
  enviar_telegram(TEXTO_PUBLICITARIO, disable_web_preview=True)


def enviar_anuncio_cashea():
  global imagen_cashea_file_id
  if not imagen_cashea_file_id:
    recuperar_respaldo_de_telegram()

  markup = InlineKeyboardMarkup()
  url_jugar = "https://wa.me/584124489363?text=Hola%2C%20quiero%20jugar%20con%20Cashea%20en%20Agencia%20Harold%20Jos%C3%A9."
  url_consultar = "https://wa.me/584124489363?text=Hola%2C%20quiero%20consultar%20mis%20cuotas%20de%20Cashea%20en%20Agencia%20Harold%20Jos%C3%A9."

  markup.add(
      InlineKeyboardButton("🎯 JUGAR CON CASHEA", url=url_jugar),
      InlineKeyboardButton("💳 CONSULTAR CASHEA", url=url_consultar),
  )
  markup_dict = markup.to_dict()

  if imagen_cashea_file_id:
    enviar_telegram_foto_con_botones(
        imagen_cashea_file_id, TEXTO_CASHEA, markup_dict
    )
  else:
    enviar_telegram_con_botones(TEXTO_CASHEA, markup_dict)


def enviar_aviso_tiempo_cumplido():
  enviar_telegram(
      "⏰ ¡Tiempo cumplido! Han finalizado las jugadas para este sorteo en la"
      " AGENCIA HAROLD JOSÉ. ¡Muy atentos a los resultados y que la suerte esté"
      " de tu lado! 🍀✨",
      disable_web_preview=True,
  )


def enviar_tasa_dolar():
  try:
    response = http_session.get(URL_BCV, timeout=10, verify=False)
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
        "💵 TASA OFICIAL BCV 💵\n\n🏦 Moneda: Dólar Estadounidense\n📈 Precio"
        f" Oficial: Bs. {precio_dolar}\n\n🔗 Fuente: Banco Central de"
        " Venezuela",
        disable_web_preview=True,
    )
  except Exception as e:
    logging.error(f"Error BCV: {e}")


def tarea_envio_programado_taquilla():
  global taquilla_activa_hoy, imagen_taquilla_file_id
  if not taquilla_activa_hoy:
    recuperar_respaldo_de_telegram()

  if taquilla_activa_hoy:
    if imagen_taquilla_file_id:
      enviar_telegram_foto(imagen_taquilla_file_id, caption_taquilla)
      logging.info("✅ Taquilla activa reenviada automáticamente a las 3:00 PM.")
    else:
      enviar_telegram(caption_taquilla, disable_web_preview=True)
      logging.info("✅ Taquilla activa reenviada por texto a las 3:00 PM.")
  else:
    logging.info(
        "ℹ️ A las 3:00 PM la taquilla no fue activada en la mañana, se omite el"
        " envío."
    )


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
          "🎯 AGENCIA HAROLD JOSÉ 🎯\n\n📢 ¡Pollas actualizadas!\nPuedes verlas"
          f" aquí 👇🏻\n{ENLACE_POLLAS}\n\n¡Mucho éxito! 🍀",
          disable_web_preview=False,
      )


def enviar_mensaje_cierre():
  global taquilla_activa_hoy, imagen_taquilla_file_id, ultima_hora_polla, regalos_hoy
  enviar_telegram(
      "🎯 AGENCIA HAROLD JOSÉ 🎯\n\n🌙 ¡FINAL DE JORNADA! 🌙\n\nEstos fueron"
      " todos los resultados del día de hoy. ¡Gracias por jugar con nosotros!"
      " Los esperamos el día de mañana con mucha más suerte y energía. 🍀✨",
      disable_web_preview=True,
  )
  taquilla_activa_hoy = False
  imagen_taquilla_file_id = None
  ultima_hora_polla = None
  regalos_hoy = []
  guardar_estado_disco()


def verificar_resultados():
  global primera_ejecucion, regalos_hoy
  try:
    respuesta = http_session.get(URL_LOTERIA, timeout=12)
    if respuesta.status_code != 200:
      logging.warning(
          "⚠️ Error al conectar con la web de lotería:"
          f" {respuesta.status_code}"
      )
      return

    soup = BeautifulSoup(respuesta.text, "html.parser")

    tarjetas = soup.find_all(
        ["div", "article", "section"],
        class_=re.compile(r"card|box|item|lotto|result", re.IGNORECASE),
    )
    if not tarjetas:
      tarjetas = soup.find_all(["div", "section"])

    fecha_actual_str = datetime.now().strftime("%Y-%m-%d")
    agencia_nombre = "AGENCIA HAROLD JOSÉ"
    procesados_en_esta_corrida = set()

    for tarjeta in tarjetas:
      texto_completo_tarjeta = tarjeta.get_text(" ", strip=True).upper()

      if (
          "RESULTADOS DE HOY" in texto_completo_tarjeta
          or "ÚLTIMOS SALIDOS" in texto_completo_tarjeta
          or "ULTIMOS SALIDOS" in texto_completo_tarjeta
      ):
        continue

      nombre_loteria = ""
      posibles_titulos = tarjeta.find_all(
          ["h1", "h2", "h3", "h4", "h5", "span", "div", "strong", "b"],
          class_=re.compile(r"title|header|name|lotto|text", re.IGNORECASE),
      )

      for pt in posibles_titulos:
        t_text = limpiar_texto(pt.get_text(" ", strip=True)).upper()
        if (
            t_text
            and len(t_text) > 2
            and any(c.isalpha() for c in t_text)
            and not re.search(r"\d{1,2}:\d{2}", t_text)
            and "PENDIENTE" not in t_text
            and "RESULTADOS" not in t_text
            and "WINBIG" not in t_text
            and "HOY" not in t_text
        ):
          nombre_loteria = t_text
          break

      if not nombre_loteria or len(nombre_loteria) > 40:
        continue

      nombre_loteria = limpiar_texto(
          re.sub(r"^[^a-zA-ZáéíóúÁÉÍÓÚñÑ0-9]+", "", nombre_loteria)
      ).upper()
      if not nombre_loteria:
        continue

      slots_sorteo = tarjeta.find_all(
          ["div", "li", "span", "tr"],
          class_=re.compile(r"item|slot|draw|row|col", re.IGNORECASE),
      )
      if not slots_sorteo:
        slots_sorteo = [tarjeta]

      for slot in slots_sorteo:
        texto_slot = limpiar_texto(slot.get_text(" ", strip=True)).upper()
        if "PENDIENTE" in texto_slot:
          continue

        match_h = re.search(r"(\d{1,2}:\d{2}\s*(?:AM|PM))", texto_slot)
        if not match_h:
          continue
        hora = limpiar_texto(match_h.group(1)).upper()

        match_res = re.search(
            r"(\d{1,2}\s-\s[A-ZÁÉÍÓÚÑa-zñáéíóú]+(?:\s+[A-ZÁÉÍÓÚÑa-zñáéíóú]+)?)",
            texto_slot,
        )
        if not match_res:
          continue

        resultado_final = limpiar_texto(match_res.group(1)).upper()

        clave_slot = (normalizar_nombre(nombre_loteria), hora)
        if clave_slot in procesados_en_esta_corrida:
          continue
        procesados_en_esta_corrida.add(clave_slot)

        es_nuevo = verificar_y_registrar_resultado(
            fecha_actual_str,
            agencia_nombre,
            nombre_loteria,
            hora,
            resultado_final,
        )

        if primera_ejecucion or not es_nuevo:
          continue

        if not es_hora_actual_valida(hora, tolerancia_minutos=45):
          continue

        markup_wa = InlineKeyboardMarkup()
        markup_wa.add(
            InlineKeyboardButton(
                "📲 ESCRIBENOS AL WHATSAPP", url="https://wa.me/584124489363"
            )
        )
        markup_dict = markup_wa.to_dict()

        mensaje_res = (
            "🎯 AGENCIA HAROLD JOSÉ 🎯\n"
            "•••••••••••••••••••••••••••••••••••\n"
            f"🎰 {nombre_loteria}\n"
            f"🕒 {hora}  {resultado_final}\n"
            "•••••••••••••••••••••••••••••••••••\n"
            "📲 WHATSAPP: 04124489363"
        )
        enviado = enviar_telegram_con_botones(mensaje_res, markup_dict)
        if enviado:
          logging.info(
              f"[RESULT SENT] Resultado enviado a Telegram: {nombre_loteria} |"
              f" {hora} | {resultado_final}"
          )
        else:
          logging.error(
              f"[RESULT ERROR] Falló envío a Telegram: {nombre_loteria} | {hora}"
          )

        time.sleep(1)

        num_match = re.search(r"^(\d{1,2})", resultado_final)
        if num_match and regalos_hoy:
          num_limpio = num_match.group(1)
          for r_num, r_animal in regalos_hoy:
            if (
                num_limpio.lstrip("0") == r_num.lstrip("0")
                or num_limpio == r_num
            ):
              mensaje_acierto = (
                  "🎉🎉 ¡ACERTAMOS! 🎉🎉\n\n✅ 🎁 Regalo del Día\n\n"
                  f"🎯 {resultado_final}\n"
                  f"🎲 🎰 {nombre_loteria}\n"
                  f"🕒 {hora}\n\n📲 WHATSAPP: 04124489363\n\n🍀 ¡Felicidades"
                  " a todos los que confiaron en Agencia Harold José!"
              )
              if enviar_telegram_con_botones(mensaje_acierto, markup_dict):
                logging.info(
                    "[RESULT SENT] Mensaje de acierto enviado a Telegram:"
                    f" {nombre_loteria} | {hora}"
                )
              time.sleep(1)
              break

    if primera_ejecucion:
      primera_ejecucion = False
      guardar_estado_disco()
      logging.info(
          "✅ Sincronización inicial completada con base de datos SQLite."
      )

  except Exception as e:
    logging.error(f"⚠️ Error detallado en verificación de resultados: {e}")
    traceback.print_exc()


def enviar_respuesta_privada(chat_id, text):
  try:
    http_session.post(
        f"{TG_API_BASE}/bot{TOKEN}/sendMessage",
        json={"chat_id": chat_id, "text": text},
        timeout=8,
    )
  except Exception:
    pass


def procesar_mensajes_privados(message):
  global taquilla_activa_hoy, imagen_taquilla_file_id, imagen_cashea_file_id
  caption = message.caption or message.text or ""
  caption_lower = caption.lower()

  if "taquilla activa" in caption_lower:
    if message.photo:
      taquilla_activa_hoy = True
      imagen_taquilla_file_id = message.photo[-1].file_id
      guardar_estado_disco()
      guardar_respaldo_en_telegram("taquilla", imagen_taquilla_file_id)
      enviar_telegram_foto(imagen_taquilla_file_id, caption_taquilla)
      logging.info("✅ Taquilla activada y publicada con la imagen adjunta.")
      enviar_respuesta_privada(
          message.chat.id,
          "✅ ¡Taquilla activada y publicada en el canal! Se reenviará"
          " automáticamente a las 3:00 PM.",
      )
    else:
      taquilla_activa_hoy = True
      guardar_estado_disco()
      enviar_telegram(caption_taquilla, disable_web_preview=True)
      logging.info("✅ Taquilla activada por texto.")

  elif "cashea" in caption_lower:
    if message.photo:
      imagen_cashea_file_id = message.photo[-1].file_id
      guardar_estado_disco()
      guardar_respaldo_en_telegram("cashea", imagen_cashea_file_id)
      enviar_respuesta_privada(
          message.chat.id,
          "✅ ¡Imagen de Cashea guardada en la nube de Telegram! Ya no se"
          " borrará aunque Render se reinicie mañana.",
      )
      logging.info(
          f"✅ Imagen de Cashea registrada en nube: {imagen_cashea_file_id}"
      )
    else:
      enviar_respuesta_privada(
          message.chat.id,
          "ℹ️ Por favor adjunta la imagen con la palabra 'cashea' para"
          " actualizarla correctamente.",
      )


@bot.message_handler(content_types=["photo"])
def handle_photos(message):
  procesar_mensajes_privados(message)


@bot.channel_post_handler(content_types=["photo"])
def handle_channel_posts_photos(message):
  procesar_mensajes_privados(message)


@bot.message_handler(func=lambda msg: True, content_types=["text"])
def handle_text_messages(message):
  procesar_mensajes_privados(message)


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
    enviar_telegram(mensaje_completo, disable_web_preview=True)
    logging.info("✅ Mensaje programado / animalitos enviado con éxito.")
    return True
  return False


@bot.channel_post_handler(func=lambda message: True)
def handle_channel_posts(message):
  text = message.text or message.caption or ""
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

  scheduler.add_job(enviar_anuncio_cashea, "cron", hour="9-16", minute=0)
  scheduler.add_job(enviar_anuncio_cashea, "cron", hour=16, minute=30)

  scheduler.add_job(enviar_aviso_tiempo_cumplido, "cron", hour="7-19", minute=55)
  scheduler.add_job(tarea_envio_programado_taquilla, "cron", hour=15, minute=0)
  scheduler.add_job(tarea_minuto_diez, "cron", hour="7-17", minute=10)
  scheduler.add_job(enviar_mensaje_cierre, "cron", hour=21, minute=10)
  scheduler.add_job(
      verificar_resultados, "interval", seconds=30, max_instances=1
  )

  scheduler.start()
  logging.info("✅ Scheduler iniciado correctamente.")
  verificar_resultados()


def iniciar_polling():
  offset = 0
  logging.info("📡 Escuchando mensajes y fotos vía Cloudflare Worker...")
  while True:
    try:
      url = f"{TG_API_BASE}/bot{TOKEN}/getUpdates"
      resp = http_session.get(
          url, params={"offset": offset, "timeout": 15}, timeout=20
      )
      if resp.status_code == 200:
        data = resp.json()
        if data.get("ok"):
          updates = [
              telebot.types.Update.de_json(u) for u in data.get("result", [])
          ]
          if updates:
            offset = updates[-1].update_id + 1
            bot.process_new_updates(updates)
      else:
        time.sleep(5)
    except Exception:
      time.sleep(5)


def arrancar_servicios_fondo():
  global servicios_iniciados
  if servicios_iniciados:
    return
  servicios_iniciados = True
  logging.info("🚀 Inicializando servicios de Agencia Harold José...")
  Thread(target=iniciar_scheduler, daemon=True).start()
  Thread(target=iniciar_polling, daemon=True).start()


arrancar_servicios_fondo()

if __name__ == "__main__":
  port = int(os.environ.get("PORT", 5000))
  app.run(host="0.0.0.0", port=port, use_reloader=False)
