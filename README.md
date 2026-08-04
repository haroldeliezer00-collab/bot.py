# AG HAROLD JOSE BOT

Bot de resultados de animalitos preparado para GitHub + Render.

## Archivos

- `bot.py`: código principal.
- `requirements.txt`: dependencias.
- `render.yaml`: configuración opcional de Render.

## Variables de entorno

En Render configura:

- `BOT_TOKEN`: token del bot de Telegram.
- `ACTIVE_CHANNEL_ID`: canal donde quieres probar el bot. Inicialmente `@pruebajsj`.
- `CHANNEL_ID`: canal principal `@AGHAROLDJOSE_BOT`.
- `TEST_CHANNEL_ID`: canal de pruebas `@pruebajsj`.
- `TIMEZONE`: `America/Caracas`.

## Pruebas HTTP

Con el servicio desplegado:

- `/health`
- `/test/piramide`
- `/test/table/10`
- `/test/table/20`
- `/test/table/50`
- `/test/source/L.ACT`
- `/test/source/R.ACT`
- `/test/all-sources`
- `/test/send/table/10`
- `/test/send/table/20`
- `/test/send/table/50`
- `/test/send/piramide`

## Comandos Telegram

- `/start`
- `/id`
- `/test10`
- `/test20`
- `/test50`
- `/piramide`

## Nota importante

La estructura de fuentes y horarios ya está cargada según la información proporcionada durante la conversación. Los parsers HTML de las páginas externas son genéricos porque esas páginas pueden cambiar su estructura. Antes de activar el bot en producción conviene probar `/test/all-sources` y corregir cualquier parser que no identifique correctamente el resultado real.

El bot no contiene ningún token.
