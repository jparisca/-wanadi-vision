#!/bin/bash
# Script de inicio unificado para Render.com

echo "Iniciando Wanadi Vision Bot en segundo plano..."
python -m bot.main &

echo "Iniciando Wanadi Vision API..."
exec uvicorn api.app:app --host 0.0.0.0 --port ${PORT:-8000}
