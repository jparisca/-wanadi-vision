FROM python:3.11-slim

# Establecer variables de entorno
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV HF_HOME=/app/.cache/huggingface

# Instalar dependencias del sistema necesarias para FAISS y numpy
RUN apt-get update && apt-get install -y \
    build-essential \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Establecer directorio de trabajo
WORKDIR /app

# Copiar requirements primero para aprovechar caché de capas Docker
COPY requirements.txt .
# Instalar PyTorch CPU primero (capa cacheada por separado para evitar re-descarga)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
        --timeout=120 \
        --retries=10 \
        torch==2.12.0+cpu \
        --extra-index-url https://download.pytorch.org/whl/cpu

# Instalar el resto de dependencias (sin torch ni nvidia)
COPY requirements.txt .
RUN grep -v "^torch==" requirements.txt | grep -v "^--extra-index-url" | \
    pip install --no-cache-dir --timeout=60 -r /dev/stdin

# Crear directorio de caché para HuggingFace
RUN mkdir -p /app/.cache/huggingface && chmod 777 /app/.cache/huggingface

# Copiar el resto del proyecto
COPY . .

# Exponer el puerto
EXPOSE 8000

# Healthcheck a nivel Docker usando el readiness probe
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health/ready || exit 1

# Iniciar ambos servicios (API y Bot)
CMD ["./start.sh"]
