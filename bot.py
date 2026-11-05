from datetime import datetime, timedelta
import json
import logging
import os
import random
import re
from threading import Lock, Thread
import time
import traceback
from apscheduler.schedulers.background import BackgroundScheduler
from bs4 import BeautifulSoup
from flask import Flask, request
import requests
import sqlite3
import telebot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup
import urllib3

# Configuración de logging profesional para Render
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)

# Forzar la zona horaria de Venezuela de forma segura
os.environ["TZ"] = "America/Caracas"
try:
  time.tzset()
except Exception as e:
  logging.warning(f"⚠️ Nota sobre tzset: {e}")

# Desactivar advertencias de certificados SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

TOKEN = os.environ.get(
    "TELEGRAM_TOKEN", "8733552499:AAFL_86sFP2twwGRF1rIXhGeZPRYcOqW8Go"
)
CANAL = "@resultadosagharoldjose"
ENLACE_CANAL = "https://t.me/resultadosagharoldjose"
ENLACE_POLLAS = "https://t.me/pollasydupletas"

bot = telebot.TeleBot(TOKEN)
scheduler = BackgroundScheduler(timezone="America/Caracas")

URL_LOTERIA = "https://lotery.winbigvzla.com/resultados"
URL_BCV = "https://www.bcv.org.ve/"
STATE_FILE = "bot_state.json"
DB_FILE = "bot_results.db"

db_lock = Lock()
memoria_envios_recientes = {}

http_session = requests.Session()
http_session.headers.update(
    {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"}
)

primera_ejecucion = True
ultima_hora_polla = None
taquilla_activa_hoy = False
imagen_taquilla_file_id = None
imagen_cashea_file_id = None
regalos_hoy = []
indice_loteria_encuesta = 0

LOTERIAS_ENCUESTA = ["LOTTO ACTIVO", "LA GRANJITA", "SELVA PLUS", "GUACHARO ACTIVO", "LOTO CHAIMA"]

ANIMALITOS_EXTENDIDOS_DICT = {
    "0": "Delfín", "00": "Ballena", "1": "Carnero", "2": "Toro", "3": "Ciempiés", "4": "Alacrán",
    "5": "León", "6": "Rana", "7": "Perico", "8": "Ratón", "9": "Águila", "10": "Tigre",
    "11": "Gato", "12": "Caballo", "13": "Mono", "14": "Paloma", "15": "Zorro", "16": "Oso",
    "17": "Pavo", "18": "Burro", "19": "Chivo", "20": "Cochino", "21": "Gallo", "22": "Camello",
    "23": "Cebra", "24": "Iguana", "25": "Gallina", "26": "Vaca", "27": "Perro", "28": "Samuro",
    "29": "Elefante", "30": "Caimán", "31": "Lapa", "32": "Ardilla", "33": "Pescado", "34": "Venado",
    "35": "Jirafa", "36": "Culebra",
    "37": "Tortuga", "38": "Búfalo", "39": "Lechuza", "40": "Avispa", "41": "Canguro", "42": "Tucán",
    "43": "Mariposa", "44": "Chigüire", "45": "Garza", "46": "Puma", "47": "Pavo Real", "48": "Puercoespín",
    "49": "Pereza", "50": "Canario", "51": "Pelícano", "52": "Pulpo", "53": "Caracol", "54": "Grillo",
    "55": "Oso Hormiguero", "56": "Tiburón", "57": "Pato", "58": "Hormiga", "59": "Pantera", "60": "Camaleón",
    "61": "Panda", "62": "Cachicamo", "63": "Cangrejo", "64": "Gavilán", "65": "Araña", "66": "Lobo",
    "67": "Avestruz", "68": "Jaguar", "69": "Conejo", "70": "Bisonte", "71": "Guacamaya", "72": "Gorila",
    "73": "Hipopótamo", "74": "Turpial", "75": "Guácharo"
}

CHISTES_REPETICION = {
    "12": [
        "El 12 - Caballo volvió a desbocarse en {loteria}. ¡Parece que le inyectaron nitro hoy! 🐴💨",
        "¡Se escapó el Caballo otra vez en {loteria}! Guarden las trancas que este animal vino desbocado. 🐎😂",
    ],
    "10": [
        "El 10 - Tigre anda hambriento hoy en {loteria}, repitió de nuevo. ¡Échale carne antes de que se coma la banca! 🐅🥩",
        "¡Zarandeo de rayitas en {loteria}! El Tigre volvió a salir. ¡Cuidado y te da un susto! 🐯🔥",
    ],
    "36": [
        "¡Cuidado con el piso! La 36 - Culebra volvió a deslizarse y repitió en {loteria}. ¡Ese animal no pica, bota fuego! 🐍⚡",
        "La Culebra anda suelta por {loteria} y repitió. ¡Reúnan los muchachos que esto se puso picante! 🐍🌀",
    ],
    "27": [
        "El 27 - Perro fiel no abandona la casa. ¡Volvió a salir en {loteria}! 🐕🦴",
        "¡Guau guau! El Perro repitió en {loteria}. ¡A ese animal hay que ponerle su plato de comida ya! 🐶🐾",
    ],
    "0": [
        "El 0 - Delfín saltó dos veces hoy en {loteria}. ¡Parece que el agua está movidita! 🐬🌊",
        "¡Chapuzón repetido! El Delfín volvió a salir en {loteria}. ¡Nadando directo a cobrar! 🐬✨",
    ],
    "21": [
        "¡Kikirikí! El 21 - Gallo volvió a cantar temprano en {loteria}. ¡Despierten a los dormidos! 🐓⏰",
        "El Gallo repitió en {loteria}. ¡Ese animal vino con las pilas puestas desde la madrugada! 🐓🔥",
    ],
}

CHISTES_GENERICOS = [
    "El {num} - {animal} le tomó el gusto a {loteria} y volvió a salir. ¡A ese animal hay que cobrarle alquiler! 🏠😂",
    "¡Vuelve y juega! El {num} - {animal} repitió en {loteria}. ¡Parece que se copió la tarea del sorteo pasado! 📋🔄",
    "¡Epa! El {num} - {animal} salió otra vez en {loteria}. ¡Cuidado y se vuelve mañoso hoy! 🎲🔥",
]


def obtener_conexion_db():
  conn = sqlite3.connect(DB_FILE, timeout=10.0)
  conn.execute("PRAGMA journal_mode=WAL;")
  conn.execute("PRAGMA busy_timeout = 5000;")
  return conn


def obtener_chiste_repetido(num, animal, loteria):
  if num in CHISTES_REPETICION:
    plantilla = random.choice(CHISTES_REPETICION[num])
    return plantilla.format(loteria=loteria)
  else:
    plantilla = random.choice(CHISTES_GENERICOS)
    return plantilla.format(num=num, animal=animal, loteria=loteria)


def inicializar_db():
  with db_lock:
    try:
      conn = obtener_conexion_db()
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
      cursor.execute("""
              CREATE TABLE IF NOT EXISTS lottery_history (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  fecha TEXT,
                  loteria TEXT,
                  hora TEXT,
                  num TEXT,
                  animal TEXT
              )
          """)
      cursor.execute("""
              CREATE TABLE IF NOT EXISTS poll_sessions (
                  poll_session TEXT PRIMARY KEY,
                  loteria TEXT,
                  chat_id TEXT,
                  message_id INTEGER,
                  closed INTEGER DEFAULT 0
              )
          """)
      cursor.execute("""
              CREATE TABLE IF NOT EXISTS poll_votes (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  fecha TEXT,
                  poll_session TEXT,
                  user_id INTEGER,
                  user_name TEXT,
                  num TEXT,
                  animal TEXT,
                  UNIQUE(poll_session, user_id),
                  UNIQUE(poll_session, num)
              )
          """)
      conn.commit()
      conn.close()
      logging.info("🗄️ Base de datos SQLite inicializada en modo WAL.")
    except Exception as e:
      logging.error(f"❌ Error en inicializar_db: {e}")


def verificar_y_registrar_resultado(fecha, agencia, loteria, hora, resultado):
  f_norm = limpiar_texto(str(fecha)).upper()
  ag_norm = normalizar_nombre(str(agencia))
  lot_norm = normalizar_nombre(str(loteria))
  h_norm = limpiar_texto(str(hora)).upper()
  res_norm = limpiar_texto(str(resultado)).upper()

  result_id = f"{f_norm}_{ag_norm}_{lot_norm}_{h_norm}_{res_norm}"

  tiempo_actual = time.time()
  if result_id in memoria_envios_recientes:
    if tiempo_actual - memoria_envios_recientes[result_id] < 180:
      return False

  with db_lock:
    try:
      conn = obtener_conexion_db()
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
        memoria_envios_recientes[result_id] = tiempo_actual
        return True
      else:
        memoria_envios_recientes[result_id] = tiempo_actual
        return False
    except Exception as e:
      logging.error(f"❌ Error en DB: {e}")
      return False
    finally:
      if "conn" in locals() and conn:
        conn.close()


def registrar_historial_sorteo(fecha, loteria, hora, num, animal):
  with db_lock:
    try:
      conn = obtener_conexion_db()
      cursor = conn.cursor()
      cursor.execute(
          """
              SELECT id FROM lottery_history 
              WHERE fecha = ? AND loteria = ? AND hora = ? AND num = ?
          """,
          (fecha, loteria, hora, num),
      )
      if not cursor.fetchone():
        cursor.execute(
            """
                  INSERT INTO lottery_history (fecha, loteria, hora, num, animal)
                  VALUES (?, ?, ?, ?, ?)
              """,
            (fecha, loteria, hora, num, animal),
        )
        conn.commit()
      conn.close()
    except Exception as e:
      logging.error(f"❌ Error registrando historial: {e}")


def cerrar_encuesta_si_existe(nombre_loteria, hora_resultado):
  with db_lock:
    try:
      fecha_str = datetime.now().strftime("%Y-%m-%d")
      lot_norm = normalizar_nombre(nombre_loteria)
      
      conn = obtener_conexion_db()
      cursor = conn.cursor()
      cursor.execute(
          """
          SELECT poll_session, chat_id, message_id FROM poll_sessions 
          WHERE loteria = ? AND closed = 0 AND poll_session LIKE ?
          """,
          (lot_norm, f"{fecha_str}%")
      )
      sesiones = cursor.fetchall()
      
      for sesion in sesiones:
        poll_session, chat_id, message_id = sesion
        cursor.execute("UPDATE poll_sessions SET closed = 1 WHERE poll_session = ?", (poll_session,))
        conn.commit()
        
        cursor.execute("SELECT user_name, num, animal FROM poll_votes WHERE poll_session = ?", (poll_session,))
        votos_finales = cursor.fetchall()
        
        lista_votos_str = "\n".join([f"• {v[0]}: **{v[1]} - {v[2]}**" for v in votos_finales]) if votos_finales else "(Sin votos registrados)"
        
        texto_cerrado = (
            f"🔒 **¡ENCUESTA CERRADA!** ❌\n"
            f"🎰 **LOTERÍA:** {nombre_loteria} ({hora_resultado})\n"
            f"🏁 *¡El resultado oficial ya ha salido! Votación finalizada.*\n\n"
            f"🏆 **Selecciones realizadas:**\n{lista_votos_str}"
        )
        
        url_edit = f"https://api.telegram.org/bot{TOKEN}/editMessageText"
        payload = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": texto_cerrado,
            "parse_mode": "Markdown"
        }
        http_session.post(url_edit, json=payload, timeout=10)
      conn.close()
    except Exception as e:
      logging.error(f"❌ Error cerrando encuesta: {e}")


def cerrar_todas_encuestas_activas():
  with db_lock:
    try:
      fecha_str = datetime.now().strftime("%Y-%m-%d")
      conn = obtener_conexion_db()
      cursor = conn.cursor()
      cursor.execute(
          """
          SELECT poll_session, loteria, chat_id, message_id FROM poll_sessions 
          WHERE closed = 0 AND poll_session LIKE ?
          """,
          (f"{fecha_str}%",)
      )
      sesiones = cursor.fetchall()
      
      for sesion in sesiones:
        poll_session, loteria_db, chat_id, message_id = sesion
        cursor.execute("UPDATE poll_sessions SET closed = 1 WHERE poll_session = ?", (poll_session,))
        conn.commit()
        
        cursor.execute("SELECT user_name, num, animal FROM poll_votes WHERE poll_session = ?", (poll_session,))
        votos_finales = cursor.fetchall()
        
        lista_votos_str = "\n".join([f"• {v[0]}: **{v[1]} - {v[2]}**" for v in votos_finales]) if votos_finales else "(Sin votos registrados)"
        
        texto_cerrado = (
            f"⏰🔒 **¡TIEMPO DE VOTACIÓN CERRADO!** ❌\n"
            f"🎰 **LOTERÍA:** {loteria_db}\n"
            f"🏁 *Se cerró la encuesta al minuto 57. ¡Esperando resultado oficial!*\n\n"
            f"🏆 **Selecciones realizadas:**\n{lista_votos_str}"
        )
        
        url_edit = f"https://api.telegram.org/bot{TOKEN}/editMessageText"
        payload = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": texto_cerrado,
            "parse_mode": "Markdown"
        }
        http_session.post(url_edit, json=payload, timeout=10)
      conn.close()
    except Exception as e:
      logging.error(f"❌ Error cerrando encuestas por tiempo: {e}")


def analizar_eventos_especiales(fecha_str, nombre_loteria, hora, num_limpio, animal_nombre):
  try:
    registrar_historial_sorteo(fecha_str, nombre_loteria, hora, num_limpio, animal_nombre)
    cerrar_encuesta_si_existe(nombre_loteria, hora)

    with db_lock:
      conn = obtener_conexion_db()
      cursor = conn.cursor()
      cursor.execute(
          """
              SELECT COUNT(*) FROM lottery_history 
              WHERE fecha = ? AND loteria = ? AND num = ?
          """,
          (fecha_str, nombre_loteria, num_limpio),
      )
      count_rep = cursor.fetchone()[0]
      conn.close()

    markup_wa = InlineKeyboardMarkup()
    markup_wa.add(InlineKeyboardButton("📲 ESCRIBENOS AL WHATSAPP", url="https://wa.me/584124489363"))
    markup_dict = markup_wa.to_dict()

    if count_rep == 2:
      id_alerta_2 = f"REP2_{fecha_str}_{normalizar_nombre(nombre_loteria)}_{num_limpio}"
      if verificar_y_registrar_resultado(fecha_str, "ALERTA", nombre_loteria, "REPETIDO_2", id_alerta_2):
        chiste_personalizado = obtener_chiste_repetido(num_limpio, animal_nombre, nombre_loteria)
        mensaje_chiste = (
            f"🔄 **¡VUELVE A APARECER HOY!** 🔄\n\n"
            f"{chiste_personalizado}\n\n"
            f"📲 WHATSAPP: 04124489363"
        )
        enviar_telegram_con_botones(mensaje_chiste, markup_dict)
        time.sleep(2)

    elif count_rep >= 3:
      id_alerta_3 = f"REP3_{fecha_str}_{normalizar_nombre(nombre_loteria)}_{num_limpio}_{count_rep}"
      if verificar_y_registrar_resultado(fecha_str, "ALERTA", nombre_loteria, f"REPETIDO_{count_rep}", id_alerta_3):
        mensaje_se_jodio = (
            f"🚨 **¡SE JODIÓ COMPADRE!** 🚨\n\n"
            f"¿Se quedaron sin animalitos en la banca o qué? El **{num_limpio} - {animal_nombre}** "
            f"ya ha salido **{count_rep} veces hoy** en **{nombre_loteria}**. ¡Agarren ese animal! 🔥🐯\n\n"
            f"📲 WHATSAPP: 04124489363"
        )
        enviar_telegram_con_botones(mensaje_se_jodio, markup_dict)
        time.sleep(2)

    ahora_dt = datetime.now()
    if 8 <= ahora_dt.hour < 19 and regalos_hoy and len(regalos_hoy) == 3:
      with db_lock:
        conn = obtener_conexion_db()
        cursor = conn.cursor()
        cursor.execute(
            """
                SELECT DISTINCT num FROM lottery_history 
                WHERE fecha = ? AND loteria = ?
            """,
            (fecha_str, nombre_loteria),
        )
        salidos_hoy = {row[0].lstrip("0") for row in cursor.fetchall()}
        conn.close()

      regalos_nums = {r[0].lstrip("0") for r in regalos_hoy}
      if regalos_nums.issubset(salidos_hoy):
        id_tripleta = f"TRIPLETA_{fecha_str}_{normalizar_nombre(nombre_loteria)}"
        if verificar_y_registrar_resultado(fecha_str, "AGENCIA", nombre_loteria, "TRIPLETA", id_tripleta):
          r1 = f"{regalos_hoy[0][0]} - {regalos_hoy[0][1]}"
          r2 = f"{regalos_hoy[1][0]} - {regalos_hoy[1][1]}"
          r3 = f"{regalos_hoy[2][0]} - {regalos_hoy[2][1]}"

          mensaje_tripleta = (
              f"🎉🎁 **¡TRIPLETAZA COMPLETADA EN LA BANCA!** 🥳🎉\n\n"
              f"¡Los 3 fijos salieron hoy en **{nombre_loteria}**:\n\n"
              f"⭐ {r1}\n⭐ {r2}\n⭐ {r3}\n\n"
              f"🏆 ¡Tripleta completada con éxito en la Agencia Harold José!\n\n"
              f"📲 WHATSAPP: 04124489363"
          )
          enviar_telegram_con_botones(mensaje_tripleta, markup_dict)
          time.sleep(2)

  except Exception as e:
    logging.error(f"❌ Error en analizar_eventos_especiales: {e}")


def cargar_estado_disco():
  global primera_ejecucion, ultima_hora_polla, taquilla_activa_hoy, imagen_cashea_file_id, regalos_hoy, indice_loteria_encuesta
  with db_lock:
    if os.path.exists(STATE_FILE):
      try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
          data = json.load(f)
          imagen_cashea_file_id = data.get("imagen_cashea", None)
          hoy_str = datetime.now().strftime("%Y-%m-%d")
          if data.get("fecha") == hoy_str:
            primera_ejecucion = data.get("primera_ejecucion", False)
            if data.get("ultima_polla_hora"):
              h_data = data.get("ultima_polla_hora")
              ultima_hora_polla = (
                  datetime.strptime(h_data[0], "%Y-%m-%d").date(),
                  h_data[1],
              )
            taquilla_activa_hoy = data.get("taquilla_activa", False)
            regalos_hoy = data.get("regalos_hoy", [])
            indice_loteria_encuesta = data.get("indice_loteria_encuesta", 0)
            return
      except Exception as e:
        logging.warning(f"⚠️ Error cargando estado: {e}")
  primera_ejecucion = True
  ultima_hora_polla = None
  taquilla_activa_hoy = False
  regalos_hoy = []
  indice_loteria_encuesta = 0


def guardar_estado_disco():
  with db_lock:
    try:
      hoy_str = datetime.now().strftime("%Y-%m-%d")
      polla_serializable = None
      if ultima_hora_polla:
        polla_serializable = [str(ultima_hora_polla[0]), ultima_hora_polla[1]]

      existing_cashea = imagen_cashea_file_id
      if not existing_cashea and os.path.exists(STATE_FILE):
        try:
          with open(STATE_FILE, "r", encoding="utf-8") as f:
            old_data = json.load(f)
            existing_cashea = old_data.get("imagen_cashea", None)
        except Exception:
          pass

      data = {
          "fecha": hoy_str,
          "primera_ejecucion": primera_ejecucion,
          "ultima_polla_hora": polla_serializable,
          "taquilla_activa": taquilla_activa_hoy,
          "imagen_cashea": existing_cashea,
          "regalos_hoy": regalos_hoy,
          "indice_loteria_encuesta": indice_loteria_encuesta,
      }
      with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
      logging.warning(f"⚠️ Error guardando estado: {e}")


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
    "• lotto rd\n"
    "• Selva Plus\n"
    "• Guácharo Activo\n"
    "• Loto Chaima\n"
    "• Monje Millonario\n"
    "• Lotto Inter\n"
    "• mega animal\n"
    "• chance con animalitos\n"
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
    "• Guacharito Millonario | Monje Millonario | Tropi Gana | Cóndor Gana | Granja Millonaria | Fruti Gana | Granjazo | Lotto Max | Ruleta Activa | Guaca37 y mucho mas ....\n"
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

app = Flask("")


@app.route("/")
def home():
  estado_tag = "ACTIVADA 🟢" if taquilla_activa_hoy else "DESACTIVADA 🔴"
  cashea_tag = "CONFIGURADA 🟢" if imagen_cashea_file_id else "SOLO TEXTO 🟡"
  return f"Agencia Harold José Bot Activo.<br>Taquilla: {estado_tag}<br>Cashea: {cashea_tag}"


@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
  if request.headers.get("content-type") == "application/json":
    json_string = request.get_data().decode("utf-8")
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "", 200
  return "Forbidden", 403


@app.route("/test/encuesta")
def test_encuesta():
  enviar_encuesta_sorteo()
  return "Prueba de Encuesta ejecutada."


def limpiar_texto(texto):
  return " ".join(texto.split())


def normalizar_nombre(texto):
  return re.sub(r"[^A-Z0-9]", "", texto.upper())


def enviar_telegram(mensaje, disable_web_preview=True):
  url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
  payload = {
      "chat_id": CANAL,
      "text": mensaje,
      "parse_mode": "Markdown",
      "disable_web_page_preview": disable_web_preview,
  }
  try:
    http_session.post(url, json=payload, timeout=10)
  except Exception as e:
    logging.warning(f"⚠️ Error Telegram: {e}")


def enviar_telegram_con_botones(mensaje, reply_markup_dict):
  url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
  payload = {
      "chat_id": CANAL,
      "text": mensaje,
      "parse_mode": "Markdown",
      "reply_markup": reply_markup_dict,
      "disable_web_page_preview": True,
  }
  try:
    http_session.post(url, json=payload, timeout=10)
  except Exception as e:
    logging.warning(f"⚠️ Error Telegram botones: {e}")


def construir_teclado_animalitos(loteria_nombre, poll_session):
  lot_norm = normalizar_nombre(loteria_nombre)
  if "SELVA" in lot_norm:
    keys = [str(i) for i in range(100)]
  elif "GUACHARO" in lot_norm:
    keys = ["0", "00"] + [str(i) for i in range(1, 76)]
  elif "CHAIMA" in lot_norm:
    keys = ["0", "00"] + [str(i) for i in range(1, 56)]
  else:
    keys = ["0", "00"] + [str(i) for i in range(1, 37)]

  markup = InlineKeyboardMarkup(row_width=3)
  botones = []
  for k in keys:
    nombre_an = ANIMALITOS_EXTENDIDOS_DICT.get(k, f"Animal {k}")
    botones.append(InlineKeyboardButton(f"{k} - {nombre_an}", callback_data=f"poll_{poll_session}_{k}"))
  markup.add(*botones)
  return markup


def enviar_encuesta_sorteo():
  global indice_loteria_encuesta
  try:
    ahora = datetime.now()
    fecha_str = ahora.strftime("%Y-%m-%d")
    hora_sorteo_dt = ahora.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    hora_sorteo_str = hora_sorteo_dt.strftime("%I:%M %p").lstrip("0")
    
    loteria_actual = LOTERIAS_ENCUESTA[indice_loteria_encuesta % len(LOTERIAS_ENCUESTA)]
    poll_session = f"{fecha_str}_{hora_sorteo_dt.strftime('%H%M')}_{normalizar_nombre(loteria_actual)}"

    indice_loteria_encuesta += 1
    guardar_estado_disco()

    markup = construir_teclado_animalitos(loteria_actual, poll_session)
    markup_dict = markup.to_dict()

    texto_encuesta = (
        f"📊 **¡ENCUESTA DE LA SUERTE!** 🎲\n"
        f"🎰 **LOTERÍA:** {loteria_actual} ({hora_sorteo_str})\n\n"
        f"¿Cuál animalito crees que saldrá en el sorteo de las **{hora_sorteo_str}** de **{loteria_actual}**?\n"
        f"👇 *Toca un botón para elegir tu animal.* ¡Cada opción es única! Tienes hasta el minuto 57 para votar.\n\n"
        f"🏆 **Selecciones actuales:** (Nadie ha votado aún)"
    )

    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CANAL,
        "text": texto_encuesta,
        "parse_mode": "Markdown",
        "reply_markup": markup_dict,
        "disable_web_page_preview": True,
    }
    response = http_session.post(url, json=payload, timeout=10)
    if response.status_code == 200:
      res_json = response.json()
      message_id = res_json.get("result", {}).get("message_id")
      
      with db_lock:
        conn = obtener_conexion_db()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO poll_sessions (poll_session, loteria, chat_id, message_id, closed)
            VALUES (?, ?, ?, ?, 0)
            """,
            (poll_session, loteria_actual, str(CANAL), message_id)
        )
        conn.commit()
        conn.close()
  except Exception as e:
    logging.error(f"❌ Error en encuesta: {e}")


@bot.callback_query_handler(func=lambda call: call.data.startswith("poll_"))
def handle_poll_vote(call):
  try:
    partes = call.data.split("_")
    if len(partes) < 3:
      return
    poll_session = "_".join(partes[1:-1])
    num_elegido = partes[-1]
    user_id = call.from_user.id
    user_name = call.from_user.first_name or "Usuario"
    animal_nombre = ANIMALITOS_EXTENDIDOS_DICT.get(num_elegido, f"Animal {num_elegido}")

    with db_lock:
      conn = obtener_conexion_db()
      cursor = conn.cursor()

      cursor.execute("SELECT closed, loteria FROM poll_sessions WHERE poll_session = ?", (poll_session,))
      row_session = cursor.fetchone()
      if not row_session:
        conn.close()
        bot.answer_callback_query(call.id, text="❌ Encuesta no encontrada.", show_alert=True)
        return

      closed, loteria_nombre_actual = row_session
      if closed == 1:
        conn.close()
        bot.answer_callback_query(call.id, text="❌ Esta encuesta ya está cerrada.", show_alert=True)
        return

      cursor.execute("SELECT num, animal FROM poll_votes WHERE poll_session = ? AND user_id = ?", (poll_session, user_id))
      user_vote = cursor.fetchone()
      if user_vote:
        conn.close()
        bot.answer_callback_query(call.id, text=f"❌ Ya elegiste el {user_vote[0]} - {user_vote[1]} en esta encuesta.", show_alert=True)
        return

      cursor.execute("SELECT user_name FROM poll_votes WHERE poll_session = ? AND num = ?", (poll_session, num_elegido))
      animal_taken = cursor.fetchone()
      if animal_taken:
        conn.close()
        bot.answer_callback_query(call.id, text=f"❌ ¡El {num_elegido} - {animal_nombre} ya fue elegido por {animal_taken[0]}!", show_alert=True)
        return

      cursor.execute(
          "INSERT INTO poll_votes (fecha, poll_session, user_id, user_name, num, animal) VALUES (?, ?, ?, ?, ?, ?)",
          (datetime.now().strftime("%Y-%m-%d"), poll_session, user_id, user_name, num_elegido, animal_nombre)
      )
      conn.commit()

      cursor.execute("SELECT user_name, num, animal FROM poll_votes WHERE poll_session = ?", (poll_session,))
      votos_actuales = cursor.fetchall()
      conn.close()

    bot.answer_callback_query(call.id, text=f"✅ ¡Has asegurado el {num_elegido} - {animal_nombre}!", show_alert=False)

    lista_votos_str = "\n".join([f"• {v[0]}: **{v[1]} - {v[2]}**" for v in votos_actuales])
    
    texto_orig = call.message.text or ""
    lineas_orig = texto_orig.split("\n")
    loteria_linea = lineas_orig[1] if len(lineas_orig) > 1 else f"🎰 **LOTERÍA:** {loteria_nombre_actual}"

    nuevo_texto = (
        f"📊 **¡ENCUESTA DE LA SUERTE!** 🎲\n"
        f"{loteria_linea}\n\n"
        f"¿Cuál animalito crees que saldrá en el próximo sorteo?\n"
        f"👇 *Toca un botón para elegir tu animal.* ¡Cada opción es única!\n\n"
        f"🏆 **Selecciones actuales:**\n{lista_votos_str}"
    )

    markup = construir_teclado_animalitos(loteria_nombre_actual, poll_session)

    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=nuevo_texto,
        parse_mode="Markdown",
        reply_markup=markup
    )
  except Exception as e:
    logging.error(f"❌ Error en callback voto: {e}")
    bot.answer_callback_query(call.id, text="⚠️ Ocurrió un error al registrar tu voto.", show_alert=True)


def limpiar_memoria_diaria():
  global primera_ejecucion, taquilla_activa_hoy, imagen_taquilla_file_id, ultima_hora_polla, regalos_hoy, indice_loteria_encuesta
  primera_ejecucion = True
  taquilla_activa_hoy = False
  imagen_taquilla_file_id = None
  ultima_hora_polla = None
  regalos_hoy = []
  indice_loteria_encuesta = 0
  guardar_estado_disco()


# --- MOTOR DE SCRAPING BLINDADO (SOLO SECCIÓN INFERIOR DE LOTERÍAS) ---
def verificar_resultados():
  global primera_ejecucion, regalos_hoy
  try:
    respuesta = http_session.get(URL_LOTERIA, timeout=15)
    if respuesta.status_code != 200:
      return

    soup = BeautifulSoup(respuesta.text, "html.parser")

    # 🛡️ FILTRO MAESTRO: Buscamos únicamente las tarjetas de loterías inferiores,
    # ignorando por completo el bloque superior de "Últimos salidos".
    tarjetas = []
    for div in soup.find_all(["div", "section", "article"]):
      texto_div = div.get_text(" ", strip=True).upper()
      # Identificamos el contenedor de lotería oficial individual por la estructura de la página
      if "SORTEOS OFICIALES" in texto_div or "ACTIVA" in texto_div or "PENDIENTE" in texto_div:
        if "RESULTADOS DE HOY" not in texto_div and "ÚLTIMOS SALIDOS" not in texto_div:
          tarjetas.append(div)

    if not tarjetas:
      # Respaldo general si cambia la estructura exacta
      tarjetas = soup.find_all(["div", "section"], class_=re.compile(r"card|box|item|lotto", re.IGNORECASE))

    fecha_actual_str = datetime.now().strftime("%Y-%m-%d")
    agencia_nombre = "AGENCIA HAROLD JOSÉ"
    procesados_en_esta_corrida = set()
    ahora_dt = datetime.now()
    hora_actual_num = ahora_dt.hour

    for tarjeta in tarjetas:
      texto_completo_tarjeta = tarjeta.get_text(" ", strip=True).upper()

      # Doble comprobación para saltar cualquier contenedor superior rezagado
      if "RESULTADOS DE HOY" in texto_completo_tarjeta or "ÚLTIMOS SALIDOS" in texto_completo_tarjeta:
        continue

      nombre_loteria = ""
      posibles_titulos = tarjeta.find_all(["h1", "h2", "h3", "h4", "h5", "span", "div", "strong", "b"])

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
            and "SORTEOS" not in t_text
            and "OFICIALES" not in t_text
            and "ACTIVA" not in t_text
        ):
          nombre_loteria = t_text
          break

      if not nombre_loteria or len(nombre_loteria) > 40:
        continue

      nombre_loteria = limpiar_texto(re.sub(r"^[^a-zA-ZáéíóúÁÉÍÓÚñÑ0-9]+", "", nombre_loteria)).upper()
      if not nombre_loteria:
        continue

      slots_sorteo = tarjeta.find_all(["div", "li", "span", "tr"], class_=re.compile(r"item|slot|draw|row|col", re.IGNORECASE))
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

        if hora_actual_num >= 18 and "AM" in hora:
          continue

        match_res = re.search(
            r"(\d{1,2}\s-\s[A-ZÁÉÍÓÚÑa-zñáéíóú]+(?:\s+[A-ZÁÉÍÓÚÑa-zñáéíóú]+)?)",
            texto_slot,
        )
        if not match_res:
          continue

        resultado_final = limpiar_texto(match_res.group(1)).upper()

        clave_slot = (normalizar_nombre(nombre_loteria), hora, normalizar_nombre(resultado_final))
        if clave_slot in procesados_en_esta_corrida:
          continue
        procesados_en_esta_corrida.add(clave_slot)

        num_match = re.search(r"^(\d{1,2})", resultado_final)
        num_limpio = num_match.group(1) if num_match else "0"
        animal_nombre = ANIMALITOS_EXTENDIDOS_DICT.get(num_limpio, ANIMALITOS_EXTENDIDOS_DICT.get(num_limpio.lstrip("0"), "Animal"))

        if primera_ejecucion:
          verificar_y_registrar_resultado(fecha_actual_str, agencia_nombre, nombre_loteria, hora, resultado_final)
        else:
          if verificar_y_registrar_resultado(fecha_actual_str, agencia_nombre, nombre_loteria, hora, resultado_final):
            markup_wa = InlineKeyboardMarkup()
            markup_wa.add(InlineKeyboardButton("📲 ESCRIBENOS AL WHATSAPP", url="https://wa.me/584124489363"))
            markup_dict = markup_wa.to_dict()

            mensaje_res = (
                "🎯 AGENCIA HAROLD JOSÉ 🎯\n"
                "•••••••••••••••••••••••••••••••••••\n"
                f"🎰 {nombre_loteria}\n"
                f"🕒 {hora}  {resultado_final}\n"
                "•••••••••••••••••••••••••••••••••••\n"
                "📲 WHATSAPP: 04124489363"
            )
            try:
              enviar_telegram_con_botones(mensaje_res, markup_dict)
              logging.info(f"[RESULT SENT] {nombre_loteria} | {hora} | {resultado_final}")
            except Exception as e:
              logging.error(f"[RESULT ERROR] {e}")

            time.sleep(2)
            analizar_eventos_especiales(fecha_actual_str, nombre_loteria, hora, num_limpio, animal_nombre)

            if regalos_hoy:
              for r_num, r_animal in regalos_hoy:
                if num_limpio.lstrip("0") == r_num.lstrip("0") or num_limpio == r_num:
                  mensaje_acierto = (
                      "🎉🎉 ¡ACERTAMOS! 🎉🎉\n\n✅ 🎁 Regalo del Día\n\n"
                      f"🎯 {resultado_final}\n"
                      f"🎲 🎰 {nombre_loteria}\n"
                      f"🕒 {hora}\n\n📲 WHATSAPP: 04124489363\n\n🍀 ¡Felicidades!"
                  )
                  try:
                    enviar_telegram_con_botones(mensaje_acierto, markup_dict)
                  except Exception:
                    pass
                  time.sleep(2)
                  break

    if primera_ejecucion:
      primera_ejecucion = False
      guardar_estado_disco()

  except Exception as e:
    logging.error(f"⚠️ Error en verificar_resultados: {e}")
    traceback.print_exc()


def procesar_mensajes_multicanal(message):
  global taquilla_activa_hoy, imagen_taquilla_file_id, imagen_cashea_file_id
  caption = message.caption or message.text or ""
  caption_lower = caption.lower()

  if "taquilla activa" in caption_lower:
    if message.photo:
      taquilla_activa_hoy = True
      imagen_taquilla_file_id = message.photo[-1].file_id
      guardar_estado_disco()
      enviar_telegram(caption_taquilla, disable_web_preview=True)
    else:
      taquilla_activa_hoy = True
      guardar_estado_disco()
      enviar_telegram(caption_taquilla, disable_web_preview=True)

  elif "cashea" in caption_lower and message.photo:
    imagen_cashea_file_id = message.photo[-1].file_id
    guardar_estado_disco()


@bot.channel_post_handler(content_types=["photo", "text"])
def handle_channel_posts(message):
  procesar_mensajes_multicanal(message)


@bot.message_handler(content_types=["photo", "text"])
def handle_all_messages(message):
  procesar_mensajes_multicanal(message)


def iniciar_scheduler():
  scheduler.add_job(limpiar_memoria_diaria, "cron", hour=0, minute=0)
  scheduler.add_job(enviar_encuesta_sorteo, "cron", hour="7-19", minute=30)
  scheduler.add_job(cerrar_todas_encuestas_activas, "cron", hour="7-19", minute=57)
  scheduler.add_job(verificar_resultados, "interval", seconds=30)
  scheduler.start()
  verificar_resultados()


def configurar_webhook():
  render_url = os.environ.get("RENDER_EXTERNAL_URL")
  if render_url:
    webhook_url = f"{render_url}/{TOKEN}"
    try:
      bot.remove_webhook()
      bot.set_webhook(url=webhook_url)
    except Exception as e:
      logging.error(f"❌ Error webhook: {e}")


if __name__ == "__main__":
  try:
    t_schedule = Thread(target=iniciar_scheduler)
    t_schedule.daemon = True
    t_schedule.start()
    configurar_webhook()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, use_reloader=False)
  except Exception as e:
    logging.critical(f"❌ Error crítico principal: {e}")
    traceback.print_exc()
