#!/bin/sh
# renew.sh — Simula actividad web para evitar que Serv00 borre la cuenta por inactividad.

# Moverse al directorio del script
cd "$(dirname "$0")"

mkdir -p logs

# Realizar curl al panel de Serv00 para registrar actividad
curl -s "https://panel.serv00.com" -o /dev/null

echo "$(date): Renovación de actividad registrada con éxito" >> logs/renew.log
