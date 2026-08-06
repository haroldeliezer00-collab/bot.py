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

# Memoria estricta para evitar duplicados y spam diario
enviados_set = set()
ultimas_claves_piramide = []

# Enlaces de páginas oficiales individuales de loterías
PAGINAS_OFICIALES = {
    "LOTTO ACTIVO": "https://www.lottoactivo.com/resultados/lotto_activo/",
    "GUACHARO ACTIVO": "https://www.guacharoactivo.com.ve/resultados",
    "LOTO CHAIMA": "https://lotochaima.com/",
    "LA GRANJITA": "https://lagranjitaonline.com/",
    "SELVA PLUS": "https://www.selvaplus.com/resultados",
    "MONJE MILLONARIO": (
        "https://www.lottoactivo.com/resultados/lottoactivo2(monjemillonario)/"
    ),
    "LOTTO ACTIVO RD INTERNACIONAL": (
        "https://www.lottoactivo.com/resultados/lotto_activo_internacional/"
    ),
    "EL GUACHARITO MILLONARIO": "https://elguacharitomillonario.com/",
    "TRIO ACTIVO": "https://www.lottoactivo.com/resultados/trio_activo/",
    "TRIPLE GUACA37": "https://www.guacaactiva.com/",
}


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
  """Valida rigurosamente que el resultado sea nuevo y lo envía al canal con el formato exacto."""
  global enviados_set

  u_loteria = nombre_loteria.upper()
  u_detalle = detalle_resultado.upper()

  # Excluir Ruleta Royal y estados pendientes o en espera
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

  # El detalle debe contener un guión separando el número y el animal (ej: "73 - CALAMAR")
  if "-" not in detalle_resultado:
    return

  # Clave única absoluta para evitar que se repita la misma lotería, hora y resultado en todo el día
  clave_unica = f"{u_loteria}_{hora.upper()}_{u_detalle.strip()}"

  if clave_unica not in enviados_set:
    enviados_set.add(clave_unica)
    mensaje = (
        "🎯 AGENCIA HAROLD JOSE 🎯\n\n"
        f"{nombre_loteria.upper()}\n"
        f"🕒 {hora.upper()}  {detalle_resultado.strip()}\n"
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


# ================= SCRAPING AUTOMÁTICO CADA 30 SEGUNDOS =================


def verificar_resultados():
  headers = {"User-Agent": "Mozilla/5.0"}

  # 1. Monitoreo individual de cada página oficial asignada en el diccionario
  for loteria, url_oficial in PAGINAS_OFICIALES.items():
    try:
      resp = requests.get(url_oficial, headers=headers, verify=False, timeout=10)
      if resp.status_code == 200:
        soup = BeautifulSoup(resp.text, "html.parser")
        for block in soup.find_all(["div", "span", "td", "p", "li"]):
          txt = block.get_text(separator=" ", strip=True)
          t_up = txt.upper()
          if ("AM" in t_up or "PM" in t_up) and "-" in txt:
            palabras = txt.split()
            hora = "Sorteo"
            for i, w in enumerate(palabras):
              if w.upper() in ["AM", "PM"] and i > 0:
                hora = f"{palabras[i-1]} {w}"
                break
            procesar_y_enviar_resultado(loteria, hora, txt)
    except Exception as e:
      print(f"Error en oficial {loteria}: {e}")

  # 2. Monitoreo de páginas múltiples (Win Big y Resultados 365) con separación estricta
  winbig_urls = [
      "https://lotery.winbigvzla.com/resultados",
      "https://resultados365.com/",
  ]
  for url in winbig_urls:
    try:
      resp = requests.get(url, headers=headers, verify=False, timeout=10)
      if resp.status_code == 200:
        soup = BeautifulSoup(resp.text, "html.parser")
        # Buscamos contenedores que dividan las secciones de loterías
        cards = soup.find_all(
            ["div", "section"],
            class_=lambda x: x
            and any(
                k in x.lower() for k in ["card", "box", "item", "lotto", "col"]
            ),
        )
        if not cards:
          cards = soup.find_all(["div", "tr"])

        for card in cards:
          texto_card = card.get_text(separator=" | ", strip=True)
          t_card_up = texto_card.upper()
          if "-" in texto_card and ("AM" in t_card_up or "PM" in t_card_up):
            # Determinar el nombre exacto de la lotería dentro de este bloque específico
            nombre_lote = "GUACA ACTIVA"
            if "MEGA" in t_card_up:
              nombre_lote = "MEGA GUACA"
            elif "GUACA" in t_card_up and "MEGA" not in t_card_up:
              nombre_lote = "GUACA ACTIVA"
            elif "GRANJA" in t_card_up:
              nombre_lote = "LA GRANJITA"

            if "RULETA ROYAL" in t_card_up:
              continue

            # Extraer la hora y el resultado limpio de la tarjeta
            partes = [p.strip() for p in texto_card.split("|") if p.strip()]
            for p in partes:
              p_up = p.upper()
              if ("AM" in p_up or "PM" in p_up) and "-" in p:
                procesar_y_enviar_resultado(nombre_lote, "Sorteo", p)
    except Exception as e:
      print(f"Error escaneando WinBig {url}: {e}")


# ================= MANEJADOR DE CANALES PRIVADOS =================


@bot.message_handler(func=lambda message: True)
def escuchar_canales(message):
  texto = message.text or message.caption or ""

  # Canal Privado 1: TAQUILLA ACTIVA
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

  # Canal Privado 2: RESULTADO PROGRAMADO
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
# Minuto 10 de cada hora desde las 7 AM hasta las 6 PM
scheduler.add_job(tarea_pollas, "cron", hour="7-18", minute=10)
# Verificación de resultados cada 30 segundos
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
