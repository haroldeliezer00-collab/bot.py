import os
import threading
import time
import logging
from flask import Flask, jsonify
import telebot
from telebot.apihelper import ApiTelegramException

# Configuración básica de logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger("AGHaroldJoseBot")

# ============================================================
# CONFIGURACIONES Y VARIABLES GLOBALES
# ============================================================
PORT = 5000
TIMEZONE = "America/Caracas"
ACTIVE_CHANNEL_ID = "@resultadosagharoldjose"
MAIN_CHANNEL_REFERENCE = "AG HAROLD JOSE"
RESULTS_REFRESH_SECONDS = 60
SCHEDULER_SECONDS = 30
POLLING_CONFLICT_WAIT = 20

# Instancias de Flask y Telebot (leyendo el token de forma segura desde las variables de entorno de Render)
app = Flask(__name__)
BOT_TOKEN = os.environ.get("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("No se encontró la variable de entorno BOT_TOKEN en Render.")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

LOTTERIES = {
    "GATAZO": {"name": "GATAZO"},
    "TRIO": {"name": "TRIO ACTIVO"}
}

# ============================================================
# FUNCIONES DE LÓGICA INTERNA (Tus funciones originales)
# ============================================================

def cleanup_old_state():
    log.info("Ejecutando limpieza de estados antiguos...")
    # Aquí va tu lógica original de limpieza de estados

def scheduler_loop():
    while True:
        try:
            current = now()
            # ------------------------------------------------
            # LIMPIEZA DIARIA
            # ------------------------------------------------
            if current.hour == 0 and current.minute == 5:
                cleanup_old_state()

            time.sleep(SCHEDULER_SECONDS)
        except Exception as exc:
            log.exception("Error en scheduler: %s", exc)
            time.sleep(SCHEDULER_SECONDS)

def pyramid_text():
    return "🎯 PIRÁMIDE AG HAROLD JOSE 🎯\nGenerada correctamente."

def build_table(block):
    return f"📊 TABLA DE RESULTADOS (BLOQUE {block}) 📊"

def merge_source_results(code):
    return {}, []

def source_urls(code):
    return []

def send_message(text):
    # Lógica para enviar mensajes al canal activo
    return True

def update_all_results(force=False):
    return {}

def now():
    import datetime
    import pytz
    tz = pytz.timezone(TIMEZONE)
    return datetime.datetime.now(tz)


# ============================================================
# ENDPOINT ROOT
# ============================================================

@app.get("/")
def root():
    return jsonify({
        "status": "ok",
        "bot": "AG HAROLD JOSE BOT",
        "active_channel": ACTIVE_CHANNEL_ID,
        "main_reference": MAIN_CHANNEL_REFERENCE,
        "timezone": TIMEZONE,
        "trio_activo": "TRIO ACTIVO 🇻🇪",
    })


# ============================================================
# HEALTH
# ============================================================

@app.get("/health")
def health():
    return jsonify({
        "status": "healthy",
        "time": now().isoformat()
    })


# ============================================================
# TEST PIRAMIDE
# ============================================================

@app.get("/test/piramide")
def test_piramide():
    return app.response_class(
        pyramid_text(),
        mimetype="text/plain; charset=utf-8"
    )


# ============================================================
# TEST TABLAS
# ============================================================

@app.get("/test/table/10")
def test_table_10():
    return app.response_class(
        build_table(10),
        mimetype="text/plain; charset=utf-8"
    )

@app.get("/test/table/20")
def test_table_20():
    return app.response_class(
        build_table(20),
        mimetype="text/plain; charset=utf-8"
    )

@app.get("/test/table/50")
def test_table_50():
    return app.response_class(
        build_table(50),
        mimetype="text/plain; charset=utf-8"
    )


# ============================================================
# TEST FUENTE
# ============================================================

@app.get("/test/source/<code>")
def test_source(code):
    code = code.upper()
    if code not in LOTTERIES:
        return jsonify({
            "error": "Código no registrado",
            "valid": list(LOTTERIES)
        }), 404

    merged, sources = merge_source_results(code)
    return jsonify({
        "code": code,
        "name": LOTTERIES[code]["name"],
        "merged": merged,
        "sources": sources,
        "urls": source_urls(code)
    })


# ============================================================
# TEST ENVIAR TABLA
# ============================================================

@app.get("/test/send/table/<int:block>")
def test_send_table(block):
    if block not in (10, 20, 50):
        return jsonify({
            "error": "Bloque debe ser 10, 20 o 50"
        }), 400

    msg = send_message(build_table(block))
    return jsonify({
        "sent": bool(msg),
        "channel": ACTIVE_CHANNEL_ID
    })


# ============================================================
# TEST ENVIAR PIRAMIDE
# ============================================================

@app.get("/test/send/piramide")
def test_send_pyramid():
    msg = send_message(pyramid_text())
    return jsonify({
        "sent": bool(msg),
        "channel": ACTIVE_CHANNEL_ID
    })


# ============================================================
# TEST UPDATE
# ============================================================

@app.get("/test/update")
def test_update():
    data = update_all_results(force=True)
    return jsonify({
        "updated": True,
        "date": now().strftime("%Y-%m-%d"),
        "lotteries": len(data),
    })


# ============================================================
# COMANDOS TELEGRAM
# ============================================================

@bot.message_handler(commands=["start"])
def cmd_start(message):
    bot.reply_to(
        message,
        "🤖 <b>AG HAROLD JOSE BOT</b>\n"
        "Bot activo.\n"
        f"Canal de prueba: {ACTIVE_CHANNEL_ID}\n"
        "Usa /id para consultar el ID del chat."
    )

@bot.message_handler(commands=["id"])
def cmd_id(message):
    bot.reply_to(
        message,
        f"🆔 Chat ID: <code>{message.chat.id}</code>"
    )

@bot.message_handler(commands=["test10"])
def cmd_test10(message):
    bot.send_message(
        message.chat.id,
        build_table(10),
        disable_web_page_preview=True
    )

@bot.message_handler(commands=["test20"])
def cmd_test20(message):
    bot.send_message(
        message.chat.id,
        build_table(20),
        disable_web_page_preview=True
    )

@bot.message_handler(commands=["test50"])
def cmd_test50(message):
    bot.send_message(
        message.chat.id,
        build_table(50),
        disable_web_page_preview=True
    )

@bot.message_handler(commands=["piramide"])
def cmd_piramide(message):
    bot.send_message(
        message.chat.id,
        pyramid_text(),
        disable_web_page_preview=True
    )


# ============================================================
# FLASK Y TELEGRAM LOOPS
# ============================================================

def run_flask():
    app.run(
        host="0.0.0.0",
        port=PORT,
        threaded=True,
        use_reloader=False
    )

def telegram_polling_loop():
    while True:
        try:
            log.info("Iniciando polling de Telegram...")
            bot.infinity_polling(
                timeout=30,
                long_polling_timeout=30,
                allowed_updates=["message", "channel_post"],
                skip_pending=True,
                restart_on_change=False
            )
            log.warning("Polling terminó inesperadamente. Reintentando en 10 segundos.")
            time.sleep(10)
        except ApiTelegramException as exc:
            error_text = str(exc)
            if getattr(exc, "error_code", None) == 409 or "409" in error_text or "Conflict" in error_text or "terminated by other getUpdates" in error_text:
                log.error("⚠️ TELEGRAM 409: otra instancia está usando getUpdates con este BOT_TOKEN.")
                log.error("Esperando %s segundos antes de reintentar.", POLLING_CONFLICT_WAIT)
                time.sleep(POLLING_CONFLICT_WAIT)
                continue
            log.exception("Error de Telegram: %s", exc)
            time.sleep(15)
        except Exception as exc:
            error_text = str(exc)
            if "409" in error_text or "Conflict" in error_text or "terminated by other getUpdates" in error_text:
                log.error("⚠️ Conflicto 409 detectado. Esperando antes de reintentar.")
                time.sleep(POLLING_CONFLICT_WAIT)
                continue
            log.exception("Error inesperado en polling: %s", exc)
            time.sleep(15)


# ============================================================
# MAIN
# ============================================================

def main():
    log.info("Iniciando AG HAROLD JOSE BOT")
    log.info("Canal activo: %s", ACTIVE_CHANNEL_ID)
    log.info("Canal principal referencia: %s", MAIN_CHANNEL_REFERENCE)
    log.info("TRIO ACTIVO 🇻🇪 integrado correctamente")
    log.info("Zona horaria: %s", TIMEZONE)
    log.info("Actualización de resultados cada %s segundos.", RESULTS_REFRESH_SECONDS)

    # 1. LIMPIEZA INICIAL UBICADA DE FORMA SEGURA DENTRO DE MAIN
    cleanup_old_state()

    # 2. FLASK SERVER
    threading.Thread(
        target=run_flask,
        name="FlaskServer",
        daemon=True
    ).start()

    # 3. SCHEDULER
    threading.Thread(
        target=scheduler_loop,
        name="Scheduler",
        daemon=True
    ).start()

    # 4. TELEGRAM POLLING
    telegram_thread = threading.Thread(
        target=telegram_polling_loop,
        name="TelegramPolling",
        daemon=False
    )
    telegram_thread.start()
    telegram_thread.join()


# ============================================================
# EJECUCIÓN
# ============================================================

if __name__ == "__main__":
    main()
