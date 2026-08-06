from datetime import datetime
import os
import random
import re
from threading import Thread
import time
from bs4 import BeautifulSoup
from flask import Flask
import requests
import telebot
import urllib3

# Forzar la zona horaria de Venezuela de forma segura
os.environ["TZ"] = "America/Caracas"
try:
  time.tzset()
except Exception as e:
  print(f"⚠️ Nota sobre tzset: {e}")

# Desactivar advertencias de certificados SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Credenciales y canal de pruebas configurado
TOKEN = "8728747633:AAHakMFznhlpK6QbkZinctgbl131wE2hIeI"
CANAL = "@pruebajsj"  # Canal de pruebas indicado
ENLACE_CANAL = "https://t.me/resultadosagharoldjose"
ENLACE_POLLAS = "https://t.me/pollasydupletas"

bot = telebot.TeleBot(TOKEN)

URL_LOTERIA = "https://lotery.winbigvzla.com/resultados"
URL_BCV = "https://www.bcv.org.ve/"

# Listado oficial exacto de loterías permitidas (RULETA ROYAL EXCLUIDA)
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
]

resultados_enviados = set()
primera_ejecucion = True

# Variable de control para el mensaje de taquilla activado por imagen con texto "Taquilla activa"
taquilla_activa_hoy = False
imagen_taquilla_file_id = None
caption_taquilla = (
    "✅ AG HAROLD JOSÉ ACTIVA ✅\n"
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

# Encabezado personalizado con el enlace del canal integrado arriba
HEADER_RESULTADOS = (
    "AGENCIA HAROLD JOSE\n"
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
      f"¡El bot de resultados AG HAROLD JOSE está activo apuntando al canal de"
      f" pruebas {CANAL}!<br><br>"
      f"<b>Estado del aviso de taquilla de hoy:</b> {estado_tag}<br><br>"
      "<b>Enlaces de prueba rápida (Test de cada opción):</b><br>"
      "👉 <a href='/test/madrugada'>Probar Saludo de Madrugada (6:30 AM)</a><br>"
      "👉 <a href='/test/piramide'>Probar Pirámide Numérica (6:31 AM)</a><br>"
      "👉 <a href='/test/saludo'>Probar Saludo Matutino (7:00 AM)</a><br>"
      "👉 <a href='/test/bcv'>Probar Tasa Oficial BCV</a><br>"
      "👉 <a href='/test/taquilla_manual'>Probar Envío Manual de Taquilla"
      " Activa</a><br>"
      "👉 <a href='/test/aviso_antiguo'>Probar Aviso de Taquilla Antiguo"
      " (10am/2pm/5pm)</a><br>"
      "👉 <a href='/test/pollas'>Probar Aviso de Pollas (Minuto 10)</a><br>"
      "👉 <a href='/test/resultados'>Forzar Revisión de Resultados"
      " Individuales</a><br>"
      "👉 <a href='/test/cierre'>Probar Mensaje de Cierre (9:10 PM)</a>"
  )


# --- RUTAS DE PRUEBA MANUAL (TESTS) ---
@app.route("/test/madrugada")
def test_madrugada():
  enviar_saludo_madrugada()
  return "Prueba de Saludo de Madrugada ejecutada."


@app.route("/test/piramide")
def test_piramide():
  enviar_piramide_diaria()
  return "Prueba de Pirámide Numérica ejecutada."


@app.route("/test/saludo")
def test_saludo():
  enviar_saludo_matutino()
  return "Prueba de Saludo Matutino ejecutada."


@app.route("/test/bcv")
def test_bcv():
  enviar_tasa_dolar()
  return "Prueba de Tasa BCV ejecutada."


@app.route("/test/taquilla_manual")
def test_taquilla_manual():
  global taquilla_activa_hoy, imagen_taquilla_file_id
  taquilla_activa_hoy = True
  if imagen_taquilla_file_id:
    enviar_telegram_foto(imagen_taquilla_file_id, caption_taquilla)
  else:
    enviar_telegram(caption_taquilla, disable_web_preview=True)
  return "Prueba de Taquilla Activa ejecutada (y estado marcado como activado)."


@app.route("/test/aviso_antiguo")
def test_aviso_antiguo():
  enviar_aviso_taquilla()
  return "Prueba de Aviso de Taquilla Antiguo ejecutada."


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
# ---------------------------------------


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


def enviar_saludo_madrugada():
  enviar_telegram(
      "🎯 CENTRO DE APUESTAS HAROLD JOSÉ 🎯\n\n"
      "🌅 ¡Despertando con la mejor energía y listos para ganar! 🌅\n\n"
      "Comenzamos este nuevo día activos y enfocados. ¡Que la suerte esté de"
      " nuestro lado! 🍀🔥",
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
  for i, f in enumerate(filas):
    nums_str = "  ".join(str(d) for d in f)
    dots_count = 3 + (i * 2)
    lineas_formateadas.append(
        f"{'.' * dots_count}  {nums_str}  {'.' * dots_count}"
    )

  cuerpo_piramide = "\n".join(lineas_formateadas)
  seed_val = int(ahora.strftime("%Y%m%d"))
  rnd = random.Random(seed_val)

  candidates = []
  for f in filas:
    for idx in range(len(f) - 1):
      val = (f[idx] * 10 + f[idx + 1]) % 37
      candidates.append(f"{val:02d}" if val != 0 else "0")
      candidates.append("00")
    for num in f:
      val = (num * 7) % 37
      candidates.append(f"{val:02d}" if val != 0 else "0")
      candidates.append("00")

  unique_candidates = []
  for c in candidates:
    if c not in unique_candidates:
      unique_candidates.append(c)

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
      "🎯 CENTRO DE APUESTAS HAROLD JOSÉ 🎯\n"
      "📢 REPORTE TÁCTICO - LA PIRÁMIDE 📢\n\n"
      f"📅 Fecha: {fecha_str}\n"
      "Análisis matemático actualizado y listo para la jugada. ¡A asegurar"
      " posición:\n\n"
      f"{cuerpo_piramide}\n\n"
      "🔥 DATOS CLAVES PARA HOY:\n"
      f"📌 {d1}\n"
      f"📌 {d2}\n\n"
      "⚡ ¡La precisión y los números hablan por sí solos! ¡Juega con confianza y"
      " gana con nosotros! 🍀 💰"
  )


def enviar_piramide_diaria():
  enviar_telegram(generar_piramide(), disable_web_preview=True)


def enviar_saludo_matutino():
  enviar_telegram(
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
      "¡Mucha suerte en sus jugadas el día de hoy y a ganar! 🍀🔥",
      disable_web_preview=True,
  )


def enviar_tasa_dolar():
  try:
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(URL_BCV, headers=headers, timeout=15, verify=False)
    precio_dolar = "742,23"
    if response.status_code == 200:
      soup = BeautifulSoup(response.text, "html.parser")
      dolar_div = soup.find("div", id="dolar")
      if dolar_div and dolar_div.find("strong"):
        precio_dolar = dolar_div.find("strong").get_text(strip=True)
    enviar_telegram(
        "💵 TASA OFICIAL BCV 💵\n\n"
        "🏦 Moneda: Dólar Estadounidense\n"
        f"📈 Precio Oficial: Bs. {precio_dolar}\n\n"
        "🔗 Fuente: Banco Central de Venezuela\n"
        f"La página para verificar el precio oficial del dólar es esta {URL_BCV}",
        disable_web_preview=True,
    )
  except Exception as e:
    print(f"Error BCV: {e}")
    enviar_telegram(
        "💵 TASA OFICIAL BCV 💵\n\n"
        "🏦 Moneda: Dólar Estadounidense\n"
        "📈 Precio Oficial: Bs. 742,23\n\n"
        "🔗 Fuente: Banco Central de Venezuela\n"
        f"La página para verificar el precio oficial del dólar es esta {URL_BCV}",
        disable_web_preview=True,
    )


def enviar_aviso_taquilla():
  enviar_telegram(
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
      "¡Mucha suerte en sus jugadas! 🍀🔥",
      disable_web_preview=True,
  )


def tarea_envio_programado_taquilla():
  global taquilla_activa_hoy, imagen_taquilla_file_id
  if taquilla_activa_hoy:
    if imagen_taquilla_file_id:
      enviar_telegram_foto(imagen_taquilla_file_id, caption_taquilla)
    else:
      enviar_telegram(caption_taquilla, disable_web_preview=True)


def reiniciar_activacion_diaria():
  global taquilla_activa_hoy
  taquilla_activa_hoy = False


def tarea_minuto_diez():
  enviar_telegram(
      "🎯 AGENCIA HAROLD JOSE 🎯\n\n"
      "📢 ¡Pollas actualizadas!\n"
      f"Puedes verlas aquí 👇🏻\n"
      f"{ENLACE_POLLAS}\n\n"
      "¡Mucho éxito! 🍀",
      disable_web_preview=False,
  )


def enviar_mensaje_cierre():
  global taquilla_activa_hoy
  enviar_telegram(
      "🎯 AGENCIA HAROLD JOSE 🎯\n\n"
      "🌙 ¡FINAL DE JORNADA! 🌙\n\n"
      "Estos fueron todos los resultados del día de hoy. ¡Gracias por jugar con"
      " nosotros! Los esperamos el día de mañana con mucha más suerte y"
      " energía. 🍀✨",
      disable_web_preview=True,
  )
  taquilla_activa_hoy = False


# ================= VERIFICACIÓN PRECISA DE RESULTADOS (CADA 30 SEGUNDOS) =================
def verificar_resultados():
  global resultados_enviados, primera_ejecucion
  try:
    headers = {"User-Agent": "Mozilla/5.0"}
    respuesta = requests.get(URL_LOTERIA, headers=headers, timeout=15)
    if respuesta.status_code != 200:
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

      # Identificar con precisión el nombre oficial de esta tarjeta
      nombre_loteria = None
      for loteria_valida in LOTERIAS_VALIDAS:
        if loteria_valida in texto_tarjeta:
          nombre_loteria = loteria_valida
          break

      if not nombre_loteria or "RULETA ROYAL" in nombre_loteria:
        continue

      # Buscar los slots de horas dentro de esta tarjeta específica
      slots = tarjeta.find_all(
          ["div", "li", "span", "tr", "p"],
          class_=re.compile(r"item|slot|draw|row|col", re.IGNORECASE),
      )
      if not slots:
        slots = [tarjeta]

      for slot in slots:
        texto_slot = slot.get_text(" ", strip=True).upper()
        if (
            "PENDIENTE" in texto_slot
            or "PRÓXIMO" in texto_slot
            or "EN ESPERA" in texto_slot
        ):
          continue

        match_h = re.search(r"(\d{1,2}:\d{2}\s*(?:AM|PM))", texto_slot)
        if not match_h:
          continue
        hora = match_h.group(1).upper()

        match_res = re.search(
            r"(\d{1,2}\s-\s[A-ZÁÉÍÓÚÑa-zñáéíóú]+(?:\s+[A-ZÁÉÍÓÚÑa-zñáéíóú]+)?)",
            texto_slot,
        )
        if not match_res:
          continue

        resultado_crudo = limpiar_texto(match_res.group(1)).upper()
        clave = (nombre_loteria, hora, resultado_crudo)

        if primera_ejecucion:
          resultados_enviados.add(clave)
        else:
          if clave not in resultados_enviados:
            # Validar estrictamente que no se haya enviado ya esta hora para esta lotería
            ya_enviado_esta_hora = any(
                c[0] == nombre_loteria and c[1] == hora for c in resultados_enviados
            )
            if not ya_enviado_esta_hora:
              item_dict = {
                  "loteria": nombre_loteria,
                  "hora": hora,
                  "resultado": resultado_crudo,
              }
              if item_dict not in nuevos_encontrados:
                nuevos_encontrados.append(item_dict)
                resultados_enviados.add(clave)

    if primera_ejecucion:
      primera_ejecucion = False
      print("✅ Escaneo inicial completado (resultados base sincronizados).")
      return

    if nuevos_encontrados:
      for item_nuevo in nuevos_encontrados:
        mensaje = (
            "🎯 AG HAROLD JOSE 🎯\n\n"
            f"🎰 {item_nuevo['loteria']}\n"
            f"🕒 {item_nuevo['hora']}  {item_nuevo['resultado']}\n"
            f"{ENLACE_CANAL}"
        )
        enviar_telegram(mensaje, disable_web_preview=True)
        time.sleep(2)

  except Exception as e:
    print(f"Error en resultados: {e}")


# --- MANEJADOR UNIVERSAL DE ACTIVACIÓN DE TAQUILLA ---
def procesar_activacion_taquilla(message):
  global taquilla_activa_hoy, imagen_taquilla_file_id
  caption = message.caption or message.text or ""
  if "taquilla activa" in caption.lower():
    if message.photo:
      taquilla_activa_hoy = True
      imagen_taquilla_file_id = message.photo[-1].file_id
      enviar_telegram_foto(imagen_taquilla_file_id, caption_taquilla)
      print("✅ Taquilla activada y publicada automáticamente con la imagen.")
    else:
      taquilla_activa_hoy = True
      enviar_telegram(caption_taquilla, disable_web_preview=True)
      print("✅ Taquilla activada por texto.")


@bot.message_handler(content_types=["photo"])
def handle_photos(message):
  procesar_activacion_taquilla(message)


@bot.channel_post_handler(content_types=["photo"])
def handle_channel_photos(message):
  procesar_activacion_taquilla(message)


@bot.message_handler(
    func=lambda msg: True, content_types=["text"]
)
def handle_text_messages(message):
  if "taquilla activa" in (message.text or "").lower():
    global taquilla_activa_hoy
    taquilla_activa_hoy = True
    if imagen_taquilla_file_id:
      enviar_telegram_foto(imagen_taquilla_file_id, caption_taquilla)
    else:
      enviar_telegram(caption_taquilla, disable_web_preview=True)
    print("✅ Taquilla activada por mensaje de texto.")


# --- MANEJADOR INTELIGENTE DE RECISIÓN Y LIMPIEZA ---
def procesar_limpieza_y_envio_animalitos(text):
  if "resultado programado" in text.lower():
    clave_corte = "resultados animalitos"
    if clave_corte.lower() in text.lower():
      pos = text.lower().find(clave_corte.lower())
      texto_limpio = text[pos:].strip()
      mensaje_completo = f"{HEADER_RESULTADOS}\n\n{texto_limpio}"
      enviar_telegram(mensaje_completo, disable_web_preview=True)
      print(
          "✅ Mensaje procesado en canal: recortado y con enlace integrado."
      )
      return True
  return False


@bot.channel_post_handler(func=lambda message: True)
def handle_channel_posts(message):
  text = message.text or message.caption or ""
  procesar_limpieza_y_envio_animalitos(text)


@bot.message_handler(
    func=lambda message: True, content_types=["text"]
)
def handle_direct_messages_animalitos(message):
  text = message.text or ""
  procesar_limpieza_y_envio_animalitos(text)
# -----------------------------------------------------------------------------

import schedule


def loop_bot():
  verificar_resultados()

  schedule.every().day.at("06:30").do(enviar_saludo_madrugada)
  schedule.every().day.at("06:31").do(enviar_piramide_diaria)
  schedule.every().day.at("07:00").do(enviar_saludo_matutino)

  schedule.every().day.at("06:30").do(enviar_tasa_dolar)
  schedule.every().day.at("18:30").do(enviar_tasa_dolar)

  schedule.every().day.at("15:00").do(tarea_envio_programado_taquilla)
  schedule.every().day.at("05:00").do(reiniciar_activacion_diaria)

  schedule.every().hour.at(":10").do(
      lambda: tarea_minuto_diez() if 7 <= datetime.now().hour <= 18 else None
  )
  schedule.every().day.at("21:10").do(enviar_mensaje_cierre)

  # Verificación de resultados exactamente cada 30 segundos como solicitaste
  schedule.every(30).seconds.do(verificar_resultados)

  while True:
    try:
      schedule.run_pending()
    except Exception as e:
      print(f"Error en schedule: {e}")
    time.sleep(1)


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
      print(f"⚠️ Error en polling de Telegram: {e}")
      time.sleep(5)


# Inicialización de hilos en segundo plano
try:
  t_schedule = Thread(target=loop_bot)
  t_schedule.daemon = True
  t_schedule.start()

  t_bot = Thread(target=iniciar_polling_bot)
  t_bot.daemon = True
  t_bot.start()
  print("✅ Hilos en segundo plano inicializados correctamente.")
except Exception as e:
  print(f"⚠️ Error al iniciar hilos: {e}")

if __name__ == "__main__":
  port = int(os.environ.get("PORT", 5000))
  app.run(host="0.0.0.0", port=port)
