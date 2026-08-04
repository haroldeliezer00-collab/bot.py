# AG HAROLD JOSE BOT

Bot de resultados de animalitos preparado para GitHub + Render.

## Destino de pruebas

El destino activo por defecto es:

`@pruebajsj`

El canal:

`@AGHAROLDJOSE_BOT`

se conserva únicamente como referencia y no se utiliza como destino activo por defecto.

## Archivos

- `bot.py`: bot completo.
- `requirements.txt`: dependencias.
- `render.yaml`: configuración de Render.
- `.gitignore`: archivos que no deben subirse.
- `README.md`: instrucciones.

## Variables de Render

Configura:

- `BOT_TOKEN`: token real entregado por BotFather.
- `ACTIVE_CHANNEL_ID`: `@pruebajsj`
- `TEST_CHANNEL_ID`: `@pruebajsj`
- `MAIN_CHANNEL_REFERENCE`: `@AGHAROLDJOSE_BOT`
- `TIMEZONE`: `America/Caracas`

## Antes de desplegar

El bot debe tener permisos suficientes en el canal de prueba para publicar mensajes.

## Endpoints

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

## Comandos

- `/start`
- `/id`
- `/test10`
- `/test20`
- `/test50`
- `/piramide`

## Importante

El token no está incluido en el código. Debe colocarse como variable de entorno `BOT_TOKEN` en Render.
