from datetime import datetime
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
scheduler = BackgroundScheduler(timezone="America/Caracas")

URL_LOTERIA = "https://lotery.winbigvzla.com/resultados"
URL_BCV = "https://www.bcv.org.ve/"

# Listado oficial de loterías ordenadas de mayor a menor longitud
LOTERIAS_VALIDAS = sorted(
    [
        "LOTTO ACTIVO RD INT",
        "LOTTO ACTIVO RDOMINICANA",
        "EL GUACHARITO MILLONARIO",
        "ZOOLOGICO ACTIVO",
        "GRANJA MILLONARIA",
        "CENTENA ANIMAL",
        "GUACHARO ACTIVO",
        "CHANCE ANIMAL",
        "RULETON VENEZUELA",
        "RULETON COLOMBIA",
        "LOTTO LA QUINTA",
        "GRANJITA PLUS",
        "MONJE MILLONARIO",
        "LOTO ANIMALITO",
        "LOTTO PANTERA",
        "RULETON PERU",
        "LA RICACHONA",
        "CENTENA PLUS",
        "LOTTO ACTIVO",
        "LA GRANJITA",
        "SELVA PLUS",
        "CONDOR GANA",
        "LOTTO CHAIMA",
        "CAZALOTON",
        "TROPI GANA",
        "FRUITAGANA",
        "GRANJAZO",
        "PANDA PLUS",
        "MEGA ANIMAL",
        "LOTTO GATO",
        "GATAZO",
        "GUACA ACTIVA",
        "LOTTO REAL",
        "LOTTOMAX",
        "CALAMAR A",
        "CALAMAR B",
        "MEGA GUACA",
    ],
    key=len,
    reverse=True,
)

resultados_enviados = set()
primera_ejecucion = True
ultima_hora_polla = None

# Variables de estado diario para la Taquilla
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


def limpiar_memoria_diaria():
  global resultados_enviados, primera_ejecucion, taquilla_activa_hoy, imagen_taquilla_file_id
  resultados_enviados.clear()
  primera_ejecucion = True
  taquilla_activa_hoy = False
  imagen_taquilla_file_id = None
  print("🧹 Memoria y estado de taquilla reiniciados para el nuevo día.")


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

  # Semilla altamente dinámica basada en el día, hora, minuto y segundo para garantizar cambio diario absoluto
  seed_val = (
      int(ahora.strftime("%Y%m%d"))
      + ahora.hour * 100
      + ahora.minute
      + random.randint(1000, 9999)
  )
  rnd = random.Random(seed_val)

  candidates = []
  for f in filas:
    for idx in range(len(f) - 1):
      val = (f[idx] * 10 + f[idx + 1] + rnd.randint(1, 15)) % 37
      candidates.append(f"{val:02d}")
    for num in f:
      val2 = (num * 7 + rnd.randint(1, 15)) % 37
      candidates.append(f"{val2:02d}")

  unique_candidates = []
  for c in candidates:
    if c not in unique_candidates:
      unique_candidates.append(c)

  rnd.shuffle(unique_candidates)

  while len(unique_candidates) < 6:
    val_rand = rnd.randint(0, 36)
    c_rand = f"{val_rand:02d}"
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
    precio_dolar = "756,71"
    if response.status_code == 200:
      soup = BeautifulSoup(response.text, "html.parser")
      dolar_div = soup.find("div", id="dolar")
      if dolar_div and dolar_div.find("strong"):
        raw_precio = dolar_div.find("strong").get_text(strip=True)
        # Limpieza robusta y formateo corto a 2 decimales exactos
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
      print("✅ Taquilla activa reenviada automáticamente a las 3:00 PM.")
    else:
      enviar_telegram(caption_taquilla, disable_web_preview=True)
      print("✅ Taquilla activa reenviada por texto a las 3:00 PM.")
  else:
    print(
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
      enviar_telegram(
          "🎯 AGENCIA HAROLD JOSE 🎯\n\n"
          "📢 ¡Pollas actualizadas!\n"
          "Puedes verlas aquí 👇🏻\n"
          f"{ENLACE_POLLAS}\n\n"
          "¡Mucho éxito! 🍀",
          disable_web_preview=False,
      )


def enviar_mensaje_cierre():
  global taquilla_activa_hoy, imagen_taquilla_file_id
  enviar_telegram(
      "🎯 AGENCIA HAROLD JOSE 🎯\n\n"
      "🌙 ¡FINAL DE JORNADA! 🌙\n\n"
      "Estos fueron todos los resultados del día de hoy. ¡Gracias por jugar con"
      " nosotros! Los esperamos el día de mañana con mucha más suerte y"
      " energía. 🍀✨",
      disable_web_preview=True,
  )
  taquilla_activa_hoy = False
  imagen_taquilla_file_id = None


def verificar_resultados():
  global resultados_enviados, primera_ejecucion
  try:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
        )
    }
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
    keys_en_este_ciclo = set()  # Filtro estricto anti-duplicados por ciclo

    for tarjeta in tarjetas:
      nombre_loteria = ""
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
        ):
          if t_text not in ["WINBIG", "RESULTADOS"]:
            nombre_loteria = t_text
            break

      if not nombre_loteria:
        lineas = [
            l.strip().upper()
            for l in tarjeta.get_text("\n", strip=True).split("\n")
            if l.strip()
        ]
        for linea in lineas:
          if (
              len(linea) > 2
              and not re.search(r"\d{1,2}:\d{2}", linea)
              and "PENDIENTE" not in linea
              and "-" not in linea
          ):
            nombre_loteria = linea
            break

      if not nombre_loteria or len(nombre_loteria) > 40:
        continue

      nombre_loteria = re.sub(r"^[^a-zA-ZáéíóúÁÉÍÓÚñÑ0-9]+", "", nombre_loteria)
      nombre_loteria = limpiar_texto(nombre_loteria)
      if not nombre_loteria:
        continue

      slots_sorteo = tarjeta.find_all(
          ["div", "li", "span", "tr"],
          class_=re.compile(r"item|slot|draw|row|col", re.IGNORECASE),
      )
      if not slots_sorteo:
        slots_sorteo = [tarjeta]

      for slot in slots_sorteo:
        texto_slot = slot.get_text(" ", strip=True).upper()
        if "PENDIENTE" in texto_slot:
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

        resultado_final = limpiar_texto(match_res.group(1)).upper()
        clave = (nombre_loteria, hora, resultado_final)
        par_loteria_hora = (nombre_loteria, hora)

        if primera_ejecucion:
          resultados_enviados.add(clave)
        else:
          if (
              clave not in resultados_enviados
              and par_loteria_hora not in keys_en_este_ciclo
          ):
            ya_enviado_hora = any(
                c[0] == nombre_loteria and c[1] == hora for c in resultados_enviados
            )
            if not ya_enviado_hora:
              item_dict = {
                  "loteria": nombre_loteria,
                  "hora": hora,
                  "resultado": resultado_final,
              }
              if item_dict not in nuevos_encontrados:
                nuevos_encontrados.append(item_dict)
                resultados_enviados.add(clave)
                keys_en_este_ciclo.add(par_loteria_hora)

    if primera_ejecucion:
      primera_ejecucion = False
      print(f"✅ Sincronización inicial lista. Total: {len(resultados_enviados)}")
      return

    if nuevos_encontrados:
      for item_nuevo in nuevos_encontrados:
        mensaje = (
            "🎯 AGENCIA HAROLD JOSE 🎯\n\n"
            f"🎰 {item_nuevo['loteria']}\n"
            f"🕒 {item_nuevo['hora']}  {item_nuevo['resultado']}\n"
            f"{ENLACE_CANAL}"
        )
        enviar_telegram(mensaje, disable_web_preview=True)
        time.sleep(2)

  except Exception as e:
    print(f"⚠️ Error en resultados: {e}")


# --- MANEJADOR DE TAQUILLA ACTIVA DESDE EL CANAL PRIVADO ---
def procesar_activacion_taquilla(message):
  global taquilla_activa_hoy, imagen_taquilla_file_id
  caption = message.caption or message.text or ""
  if "taquilla activa" in caption.lower():
    if message.photo:
      taquilla_activa_hoy = True
      imagen_taquilla_file_id = message.photo[-1].file_id
      enviar_telegram_foto(imagen_taquilla_file_id, caption_taquilla)
      print("✅ Taquilla activada y publicada con la imagen adjunta.")
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
    print("✅ Taquilla activada por texto.")


# --- MANEJADOR DE RESULTADOS PROGRAMADOS / ANIMALITOS ---
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
    print("✅ Mensaje programado / animalitos enviado con éxito.")
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


def iniciar_scheduler():
  scheduler.add_job(limpiar_memoria_diaria, "cron", hour=0, minute=0)
  scheduler.add_job(enviar_saludo_madrugada, "cron", hour=6, minute=30)
  scheduler.add_job(enviar_piramide_diaria, "cron", hour=6, minute=31)
  scheduler.add_job(enviar_saludo_matutino, "cron", hour=7, minute=0)
  scheduler.add_job(enviar_tasa_dolar, "cron", hour=6, minute=30)
  scheduler.add_job(enviar_tasa_dolar, "cron", hour=18, minute=30)

  # Envío programado de taquilla a las 3:00 PM (15:00) sujeto a activación previa
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
