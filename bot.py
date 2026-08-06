from datetime import datetime
import os
import random
import threading
import time
from apscheduler.schedulers.background import BackgroundScheduler
from bs4 import BeautifulSoup
from flask import Flask
import requests
import telebot
import urllib3

# Desactivar advertencias SSL para scraping seguro
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ================= CONFIGURACIÓN =================
TOKEN = "8728747633:AAHakMFznhlpK6QbkZinctgbl131wE2hIeI"
TEST_CHANNEL = "@pruebajsj"  # Canal de pruebas configurado

bot = telebot.TeleBot(TOKEN)
scheduler = BackgroundScheduler(timezone="America/Caracas")
app = Flask(__name__)

# Memoria estricta para evitar duplicados en el día
enviados_set = set()
initial_scan_done = False
ultimas_claves_piramide = []

# Fuente oficial única establecida
URL_WINBIG = "https://lotery.winbigvzla.com/resultados"

# Listado oficial exacto de los encabezados de las loterías en Win Big
LOTERIAS_VALIDAS = [
    "LOTTO ACTIVO",
    "LA GRANJITA",
    "EL GUACHARITO MILLONARIO",
    "GUACHARO ACTIVO",
    "SELVA PLUS",
    "LOTTO ACTIVO RD INT",
    "GRANJA MILLONARIA",
    "CONDOR GANA",
    "CENTENA ANIMAL",
    "CENTENA PLUS",
    "LOTTO ACTIVO RDOMINICANA",
    "LOTTO CHAIMA",
    "CAZALOTON",
    "CHANCE ANIMAL",
    "LA RICACHONA",
    "TROPI GANA",
    "FRUITAGANA",
    "GRANJITA PLUS",
    "GRANJAZO",
    "PANDA PLUS",
    "MEGA ANIMAL",
    "MONJE MILLONARIO",
    "LOTTO GATO",
    "GATAZO",
    "ZOOLOGICO ACTIVO",
    "GUACA ACTIVA",
    "LOTO ANIMALITO",
    "LOTTO PANTERA",
    "LOTTO REAL",
    "LOTTO LA QUINTA",
    "RULETON PERU",
    "LOTTOMAX",
    "RULETON COLOMBIA",
    "RULETON VENEZUELA",
    "CALAMAR A",
    "CALAMAR B",
    "MEGA GUACA",
    "RULETA ROYAL",
]


@app.route("/")
def health_check():
  return "Bot Agencia Harold José 3.0 operando correctamente.", 200


# ================= FUNCIONES AUXILIARES =================


def obtener_tasa_bcv():
  try:
    url = "https://www.bcv.org.ve/"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers, verify=False, timeout=10)
    if response.status_code == 200:
      soup = BeautifulSoup(response.text, "html.parser")
      div_dolar = soup.find("div", {"id": "dolar"})
      if div_dolar:
        strong = div_dolar.find("strong")
        if strong:
          return strong.text.strip().replace(",", ".")
  except Exception as e:
    print(f"Error al obtener tasa BCV: {e}")
  return "742,23"


def procesar_y_enviar_resultado(nombre_loteria, hora, detalle_resultado):
  """Valida que el resultado pertenezca estrictamente a la lotería correcta y sea nuevo."""
  global enviados_set, initial_scan_done

  u_loteria = nombre_loteria.upper().strip()
  u_detalle = detalle_resultado.upper().strip()
  u_hora = hora.upper().strip()

  if u_loteria not in LOTERIAS_VALIDAS:
    return

  if "RULETA ROYAL" in u_loteria or "RULETA ROYAL" in u_detalle:
    return

  palabras_prohibidas = [
      "PENDIENTE",
      "PRÓXIMO",
      "PROXIMO",
      "CIERRE",
      "JUEGA",
      "EN ESPERA",
  ]
  if any(p in u_detalle for p in palabras_prohibidas):
    return

  if "-" not in detalle_resultado:
    return

  # Clave única absoluta por Lotería + Hora + Resultado exacto
  clave_unica = f"{u_loteria}_{u_hora}_{u_detalle}"

  if clave_unica not in enviados_set:
    enviados_set.add(clave_unica)
    # Si estamos en el escaneo inicial, solo registramos en memoria sin hacer spam
    if not initial_scan_done:
      return

    mensaje = (
        "🎯 AGENCIA HAROLD JOSE 🎯\n\n"
        f"{u_loteria}\n"
        f"🕒 {u_hora}  {detalle_resultado.strip()}\n"
        "https://t.me/resultadosagharoldjose"
    )
    bot.send_message(TEST_CHANNEL, mensaje)


# ================= TAREAS PROGRAMADAS (CRON) =================


def tarea_buenos_dias():
  msg = (
      "🌅 ¡Buenos días a todos! 🌅\n\n"
      "Que este nuevo día llegue cargado de la mejor energía, bendiciones y"
      " muchas jugadas ganadoras. ¡A triunfar con nosotros! 🍀✨"
  )
  bot.send_message(TEST_CHANNEL, msg)


def tarea_piramide():
  global ultimas_claves_piramide
  today = datetime.now().strftime("%d/%m/%Y")

  posibles_datos = [
      "25-13-07",
      "35-20-02",
      "12-00-18",
      "05-36-22",
      "19-01-33",
      "08-00-24",
  ]
  datos_nuevos = random.choice(posibles_datos)
  while datos_nuevos in ultimas_claves_piramide:
    datos_nuevos = random.choice(posibles_datos)
  ultimas_claves_piramide = [datos_nuevos]

  p = datos_nuevos.split("-")
  piramide_art = (
      "🎯 CENTRO DE APUESTAS HAROLD JOSÉ 🎯\n"
      "📢 REPORTE - LA PIRÁMIDE DE HOY 📢\n\n"
      f"📅 Fecha: {today}\n"
      "Análisis matemático actualizado y listo para la jugada. ¡A asegurar"
      " posición:\n\n"
      "...  2  5  0  7  2  0  2  6  ...\n"
      ".....  7  5  7  9  2  2  8  .....\n"
      ".......  2  2  6  1  4  0  .......\n"
      ".........  4  8  7  5  4  .........\n"
      "...........  2  5  2  9  ...........\n"
      ".............  7  7  1  .............\n"
      "...............  4  8  .......\n"
      ".................  2  .................\n\n"
      "🔥 DATOS CLAVES PARA HOY:\n"
      f"📌 {p[0]}-{p[1]}-{p[2]}\n"
      f"📌 {p[2]}-{p[0]}-{p[1]}\n\n"
      "⚡ ¡La precisión y los números hablan por sí solos! ¡Juega con confianza y"
      " gana con nosotros! 🍀 💰"
  )
  bot.send_message(TEST_CHANNEL, piramide_art)


def tarea_saludo_7am():
  msg = (
      "🎯 AGENCIA HAROLD JOSE 🎯\n\n"
      "🌅 ¡Buenos días a todos! 🌅\n\n"
      "Ya arrancamos un nuevo día con la mejor energía. Por aquí estaremos"
      " compartiendo todos los resultados de los animalitos a medida que vayan"
      " saliendo.\n\n"
      "📢 Nuestros canales oficiales:\n"
      "🎟️ Catálogo y WhatsApp: https://wa.me/c/584124489363\n"
      "📸 Instagram: https://www.instagram.com/agharold.jose (@agharold.jose)\n"
      "💬 Canal de WhatsApp:"
      " https://whatsapp.com/channel/0029Vaza7YIGzzKJq7as7s1T\n\n"
      "¡Mucha suerte en sus jugadas el día de hoy y a ganar! 🍀🔥"
  )
  bot.send_message(TEST_CHANNEL, msg)


def tarea_bcv():
  tasa = obtener_tasa_bcv()
  msg = (
      "💵 TASA OFICIAL BCV 💵\n\n"
      "🏦 Moneda: Dólar Estadounidense\n"
      f"📈 Precio Oficial: Bs. {tasa}\n\n"
      "🔗 Fuente: Banco Central de Venezuela"
  )
  bot.send_message(TEST_CHANNEL, msg)


def tarea_aviso_importante():
  msg = (
      "🎯 AGENCIA HAROLD JOSE 🎯\n"
      "Tu centro de apuestas de confianza. Atendemos vía WhatsApp y Telegram.\n\n"
      "📢 ¡AVISO IMPORTANTE PARA NUESTROS JUGADORES! 📢\n\n"
      "Recuerda que para jugar con nosotros debes acceder primero al Canal de"
      " WhatsApp para verificar si la taquilla se encuentra activa el día de"
      " hoy:\n"
      "👉 https://whatsapp.com/channel/0029Vaza7YIGzzKJq7as7s1T\n\n"
      "📲 Si la taquilla está activa, puedes revisar nuestro catálogo y"
      " escribirnos directamente:\n"
      "🎟️ Catálogo y WhatsApp: https://wa.me/c/584124489363\n\n"
      "💬 También estamos disponibles por Telegram:\n"
      "👉 t.me/ag_haroldjose\n\n"
      "¡Mucha suerte en sus jugadas! 🍀🔥"
  )
  bot.send_message(TEST_CHANNEL, msg)


def tarea_pollas():
  msg = (
      "📢 ¡Pollas actualizadas!\n"
      "Puedes verlas aquí 👇\n"
      "https://t.me/pollasydupletas\n\n"
      "¡Mucho éxito! 🍀"
  )
  bot.send_message(TEST_CHANNEL, msg)


def tarea_fin_jornada():
  msg = (
      "🎯 AGENCIA HAROLD JOSE 🎯\n\n"
      "🌙 ¡FINAL DE JORNADA! 🌙\n\n"
      "Estos fueron todos los resultados del día de hoy. ¡Gracias por jugar"
      " con nosotros! Los esperamos el día de mañana con mucha más suerte y"
      " energía. 🍀✨"
  )
  bot.send_message(TEST_CHANNEL, msg)


# ================= SCRAPING POR TARJETAS INDIVIDUALES =================


def verificar_resultados():
  global initial_scan_done
  headers = {"User-Agent": "Mozilla/5.0"}
  try:
    resp = requests.get(URL_WINBIG, headers=headers, verify=False, timeout=10)
    if resp.status_code == 200:
      soup = BeautifulSoup(resp.text, "html.parser")
      
      # Buscamos contenedores/tarjetas en la página
      cards = soup.find_all(["div", "section", "article"])

      for card in cards:
        parts = [p.strip() for p in card.get_text(separator="|", strip=True).split("|") if p.strip()]
        if not parts:
          continue

        # Identificar con precisión el nombre de la lotería buscando en los primeros elementos de la tarjeta
        matched_lotto = None
        for p in parts[:4]:
          p_up = p.upper()
          if p_up in LOTERIAS_VALIDAS:
            matched_lotto = p_up
            break

        if not matched_lotto:
          # Búsqueda parcial por si hay texto adicional en el título
          for p in parts[:3]:
            p_up = p.upper()
            for l_name in LOTERIAS_VALIDAS:
              if l_name in p_up:
                matched_lotto = l_name
                break
            if matched_lotto:
              break

        if not matched_lotto or matched_lotto == "RULETA ROYAL":
          continue

        # Recorrer buscando pares de hora y resultado dentro de esta tarjeta específica
        i = 0
        while i < len(parts) - 1:
          item = parts[i]
          item_up = item.upper()
          if "AM" in item_up or "PM" in item_up:
            hora_sorteo = item
            if i + 1 < len(parts):
              res_sorteo = parts[i + 1]
              if "-" in res_sorteo and not any(
                  w in res_sorteo.upper()
                  for w in ["PENDIENTE", "PRÓXIMO", "EN ESPERA"]
              ):
                procesar_y_enviar_resultado(
                    matched_lotto, hora_sorteo, res_sorteo
                )
            i += 2
          else:
            i += 1

      if not initial_scan_done:
        initial_scan_done = True
        print(
            "Escaneo inicial completado. A partir de ahora solo se enviarán"
            " resultados nuevos en tiempo real."
        )

  except Exception as e:
    print(f"Error escaneando WinBig: {e}")


# ================= MANEJADOR DE CANALES PRIVADOS =================


@bot.message_handler(func=lambda message: True)
def escuchar_canales(message):
  texto = message.text or message.caption or ""

  if "TAQUILLA ACTIVA" in texto.upper():
    respuesta_activa = (
        "✅ AG HAROLD JOSÉ ACTIVA ✅\n"
        "Ya estamos operativos brindando la mejor atención. Calidad, respaldo y"
        " rapidez en cada una de tus solicitudes.\n\n"
        "📲 Envía tus jugadas:\n"
        "(Comprobante de pago/Lotería / monto / Hora)\n\n"
        "📖 Consulta nuestro reglamento aquí:\n"
        "https://wa.me/p/33319103291071105/584124489363\n"
        "🚀 Agiliza tu proceso aquí:"
        " https://wa.me/p/24724650613899486/584124489363\n\n"
        "RESULTADOS AUTOMÁTICOS\n"
        "https://t.me/resultadosagharoldjose\n\n"
        "¡Mucho éxito en la jornada de hoy! 🍀✨"
    )
    bot.send_message(TEST_CHANNEL, respuesta_activa)

  if "📊 RESULTADO PROGRAMADO" in texto:
    partes = texto.split("📊 RESULTADO PROGRAMADO")
    if len(partes) > 1:
      contenido_inferior = partes[1].strip()
      respuesta_programada = (
          "AGENCIA HAROLD JOSE\n"
          "SEGURIDAD Y CONFIANZA\n"
          "RESULTADOS OFICIALES\n"
          "📲JUEGA AQUI👇👇\n"
          "WHATSAPP: 04124489363\n"
          "📰RESULTADOS ANIMALITOS📰\n\n" + contenido_inferior
      )
      bot.send_message(TEST_CHANNEL, respuesta_programada)


# ================= ASIGNACIÓN DE CRONOGRAMAS =================

scheduler.add_job(tarea_buenos_dias, "cron", hour=6, minute=30)
scheduler.add_job(tarea_piramide, "cron", hour=6, minute=31)
scheduler.add_job(tarea_bcv, "cron", hour=6, minute=30)
scheduler.add_job(tarea_bcv, "cron", hour=18, minute=30)
scheduler.add_job(tarea_saludo_7am, "cron", hour=7, minute=0)
scheduler.add_job(tarea_aviso_importante, "cron", hour=10, minute=0)
scheduler.add_job(tarea_aviso_importante, "cron", hour=14, minute=0)
scheduler.add_job(tarea_aviso_importante, "cron", hour=17, minute=0)
scheduler.add_job(tarea_fin_jornada, "cron", hour=21, minute=10)

# Envío de pollas estrictamente cada hora en el minuto 10, desde las 7:10 AM hasta las 5:10 PM
scheduler.add_job(
    tarea_pollas, "cron", hour="7-17", minute=10, id="job_pollas"
)

# Verificación de resultados en Win Big cada 30 segundos
scheduler.add_job(verificar_resultados, "interval", seconds=30)

if __name__ == "__main__":
  scheduler.start()
  print("Bot de Agencia Harold José iniciado correctamente...")


  def run_bot():
    try:
      bot.remove_webhook()
      time.sleep(1)
      bot.infinity_polling(skip_pending=True)
    except Exception as e:
      print(f"Error en el polling del bot: {e}")


  t = threading.Thread(target=run_bot, daemon=True)
  t.start()

  port = int(os.environ.get("PORT", 10000))
  app.run(host="0.0.0.0", port=port)
