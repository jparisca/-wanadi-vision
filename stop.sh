#!/bin/sh
# stop.sh — Detiene de forma segura los procesos de la API y el Bot usando los PIDs guardados.

# Moverse al directorio del script
cd "$(dirname "$0")"

# Detener API
if [ -f pids/api.pid ]; then
  PID=$(cat pids/api.pid)
  echo "Deteniendo API (PID: $PID)..."
  kill $PID 2>/dev/null
  # Esperar a que muera
  sleep 1
  kill -9 $PID 2>/dev/null
  rm pids/api.pid
else
  echo "No se encontró PID de la API."
fi

# Detener Bot
if [ -f pids/bot.pid ]; then
  PID=$(cat pids/bot.pid)
  echo "Deteniendo Bot (PID: $PID)..."
  kill $PID 2>/dev/null
  # Esperar a que muera
  sleep 1
  kill -9 $PID 2>/dev/null
  rm pids/bot.pid
else
  echo "No se encontró PID del Bot."
fi

echo "Procesos detenidos con éxito."
