#!/bin/sh
# watchdog.sh — Monitorea y reactiva la API y el Bot si mueren.
# Compatible con FreeBSD / Serv00.

# Moverse al directorio del script
cd "$(dirname "$0")"

mkdir -p pids logs

# Verificar API
if [ ! -f pids/api.pid ] || ! kill -0 $(cat pids/api.pid) 2>/dev/null; then
  echo "$(date): API muerta, reiniciando..." >> logs/watchdog.log
  . venv/bin/activate
  nohup uvicorn api.app:app --host 127.0.0.1 --port 8000 > logs/api.log 2>&1 &
  echo $! > pids/api.pid
fi

# Verificar Bot
if [ ! -f pids/bot.pid ] || ! kill -0 $(cat pids/bot.pid) 2>/dev/null; then
  echo "$(date): Bot muerto, reiniciando..." >> logs/watchdog.log
  . venv/bin/activate
  nohup python bot/main.py > logs/bot.log 2>&1 &
  echo $! > pids/bot.pid
fi
