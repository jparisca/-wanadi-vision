FROM python:3.11-slim

# Establecer variables de entorno
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/home/user/app
ENV HF_HOME=/home/user/app/.cache/huggingface
ENV HOME=/home/user
ENV PATH=/home/user/.local/bin:$PATH
# Puerto requerido por HuggingFace Spaces
ENV PORT=7860

# Instalar dependencias del sistema necesarias para FAISS y numpy
RUN apt-get update && apt-get install -y \
    build-essential \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Crear usuario no-root requerido por HuggingFace Spaces
RUN useradd -m -u 1000 user

# Establecer directorio de trabajo
WORKDIR /home/user/app

# Cambiar a usuario no-root
USER user

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

# Puerto de HuggingFace Spaces
EXPOSE 7860

# Healthcheck usando el puerto de HF Spaces
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=5 \
    CMD curl -f http://localhost:7860/api/v1/health/ready || exit 1

# Iniciar ambos servicios (API y Bot)
CMD ["./start.sh"]
