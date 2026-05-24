#!/bin/bash
# Script de inicio unificado para HuggingFace Spaces
# Puerto 7860 requerido por HF Spaces

echo "=== Wanadi Vision Iniciando ==="

# Iniciar Bot de Telegram en segundo plano
echo "🤖 Iniciando Bot de Telegram..."
python -m bot.main &
BOT_PID=$!
echo "   Bot PID: $BOT_PID"

# Iniciar API FastAPI en primer plano (HF Spaces monitorea este proceso)
echo "🚀 Iniciando API FastAPI en puerto 7860..."
exec uvicorn api.app:app --host 0.0.0.0 --port 7860
