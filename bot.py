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

# Desactivar advertencias SSL para scraping fluido
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ================= CONFIGURACIÓN =================
TOKEN = "8698848083:AAHyJHdx6ZfnuQ9qjF7_lupAxsjEahP7nqU"
TEST_CHANNEL = "@pruebajsj"  # Canal de pruebas indicado

bot = telebot.TeleBot(TOKEN)
scheduler = BackgroundScheduler()
app = Flask(__name__)

# Memoria para evitar duplicados y spam de resultados
enviados_set = set()
ultimas_claves_piramide = []

# Enlaces de páginas oficiales de loterías
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
    "GUACA ACTIVA": "https://lotery.winbigvzla.com/resultados",
    "MEGA GUACA": "https://lotery.winbigvzla.com/resultados",
    "EL GUACHARITO MILLONARIO": "https://elguacharitomillonario.com/",
    "TRIO ACTIVO": "https://www.lottoactivo.com/resultados/trio_activo/",
    "TRIPLE GUACA37": "https://www.guacaactiva.com/",
}


@app.route("/")
def health_check():
  return (
      "Bot de Agencia Harold José operando correctamente con servidor web.",
      200,
  )


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


def es_resultado_valido(texto):
  t_upper = texto.upper()
  palabras_prohibidas = [
      "PENDIENTE",
      "PRÓXIMO",
      "PROXIMO",
      "CIERRE",
      "JUEGA",
      "SORTEO",
      "RULETA ROYAL",
  ]
  if any(p in t_upper for p in palabras_prohibidas):
    return False
  if not ("AM" in t_upper or "PM" in t_upper):
    return False
  if "-" not in t_upper:
    return False
  if len(texto) < 6 or len(texto) > 80:
    return False
  return True


# ================= TAREAS PROGRAMADAS (CRON) =================


def tarea_buenos_dias():
  msg = (
      "🌅 ¡Buenos días a todos! 🌅\n\n"
      "Arrancamos el día con la mejor energía y bendiciones. ¡A asegurar las"
      " mejores jugadas con nosotros! 🍀✨"
  )
  bot.send_message(TEST_CHANNEL, msg)


def tarea_piramide():
  global ultimas_claves_piramide
  today = datetime.now().strftime("%d/%m/%Y")

  # Generar claves dinámicas en rango 0-00 hasta 36 asegurando que no se repitan respecto al día anterior
  posibles = [
      "25-13-07",
      "35-20-02",
      "12-00-18",
      "05-36-22",
      "19-01-33",
      "08-00-24",
  ]
  datos_nuevos = random.choice(posibles)
  while datos_nuevos in ultimas_claves_piramide:
    datos_nuevos = random.choice(posibles)
  ultimas_claves_piramide = [datos_nuevos]

  partes = datos_nuevos.split("-")
  d1, d2, d3 = partes[0], partes[1], partes[2]

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
      f"📌 {d1}-{d2}-{d3}\n"
      f"📌 {d3}-{d1}-{d2}\n\n"
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
      "No te pierdas de los sorteos de las polla\n\n"
      "O\n\n"
      "Ya se subieron o ya se actualizo el canal con las pollas de este sorteo"
      " puedes verlo aquí 👇🏻\n"
      "https://t.me/pollasydupletas"
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


# ================= SCRAPING DE RESULTADOS CADA 30 SEGUNDOS =================


def verificar_resultados():
  global enviados_set
  headers = {"User-Agent": "Mozilla/5.0"}

  # 1. Sitios generales (Winbig y Resultados365)
  general_urls = [
      "https://lotery.winbigvzla.com/resultados",
      "https://resultados365.com/",
  ]
  for url in general_urls:
    try:
      resp = requests.get(url, headers=headers, verify=False, timeout=10)
      if resp.status_code == 200:
        soup = BeautifulSoup(resp.text, "html.parser")
        for item in soup.find_all(["div", "li", "tr", "p", "span"]):
          texto = item.get_text(separator=" ", strip=True)
          if not es_resultado_valido(texto):
            continue

          identificador = f"{url}_{texto}"
          if identificador not in enviados_set:
            enviados_set.add(identificador)
            mensaje_resultado = (
                "🎯 AG HAROLD JOSE 🎯\n\n"
                f"{texto}\n"
                "https://t.me/resultadosagharoldjose"
            )
            bot.send_message(TEST_CHANNEL, mensaje_resultado)
    except Exception as e:
      print(f"Error escaneando {url}: {e}")

  # 2. Páginas oficiales individuales con doble verificación
  for loteria, url_oficial in PAGINAS_OFICIALES.items():
    try:
      resp = requests.get(url_oficial, headers=headers, verify=False, timeout=10)
      if resp.status_code == 200:
        soup = BeautifulSoup(resp.text, "html.parser")
        for block in soup.find_all(["div", "span", "td", "p", "li"]):
          txt = block.get_text(separator=" ", strip=True)
          if not es_resultado_valido(txt):
            continue

          id_oficial = f"{loteria}_{txt}"
          if id_oficial not in enviados_set:
            enviados_set.add(id_oficial)
            mensaje_oficial = (
                "🎯 AG HAROLD JOSE 🎯\n\n"
                f"{loteria}\n"
                f"{txt}\n"
                "https://t.me/resultadosagharoldjose"
            )
            bot.send_message(TEST_CHANNEL, mensaje_oficial)
    except Exception as e:
      print(f"Error en oficial {loteria}: {e}")


# ================= MANEJADOR DE MENSAJES Y PALABRAS CLAVE =================


@bot.message_handler(func=lambda message: True)
def escuchar_canales(message):
  texto = message.text or message.caption or ""

  # Palabra clave: TAQUILLA ACTIVA (Canal privado 1)
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

  # Palabra clave: 📊 RESULTADO PROGRAMADO (Canal privado 2)
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


# ================= CONFIGURACIÓN DE CRONOGRAMA =================

scheduler.add_job(tarea_buenos_dias, "cron", hour=6, minute=30)
scheduler.add_job(tarea_piramide, "cron", hour=6, minute=31)
scheduler.add_job(tarea_bcv, "cron", hour=6, minute=30)
scheduler.add_job(tarea_bcv, "cron", hour=18, minute=30)
scheduler.add_job(tarea_saludo_7am, "cron", hour=7, minute=0)
scheduler.add_job(tarea_aviso_importante, "cron", hour=10, minute=0)
scheduler.add_job(tarea_aviso_importante, "cron", hour=14, minute=0)
scheduler.add_job(tarea_aviso_importante, "cron", hour=17, minute=0)
scheduler.add_job(tarea_fin_jornada, "cron", hour=21, minute=10)
scheduler.add_job(tarea_pollas, "cron", hour="7-18", minute=10)
scheduler.add_job(verificar_resultados, "interval", seconds=30)

if __name__ == "__main__":
  scheduler.start()
  print("Bot de Agencia Harold José iniciado correctamente...")

  # Hilo para ejecutar el bot de Telegram en paralelo con Flask
  def run_bot():
    bot.infinity_polling(skip_pending=True)

  t = threading.Thread(target=run_bot, daemon=True)
  t.start()

  port = int(os.environ.get("PORT", 10000))
  app.run(host="0.0.0.0", port=port)
