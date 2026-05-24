# 🚀 Manual de Despliegue (Render.com)

Este manual explica cómo desplegar el proyecto completo de Wanadi Vision (API FastAPI + Bot de Telegram) en un único contenedor de Render.com usando la configuración de Blueprints.

## 📁 Archivos Clave Preparados
Para este despliegue, el proyecto ya cuenta con los siguientes archivos:
1. `render.yaml`: La declaración de infraestructura como código (IaC) para Render.
2. `Dockerfile`: Preparado para instalar dependencias de sistema (FAISS) y Python, y ejecutar el script de inicio.
3. `start.sh`: El script bash unificado que lanza el Bot en segundo plano (`&`) y la API en primer plano (`exec uvicorn`).

## 🛠️ Pasos de Despliegue

### Paso 1: Subir código a GitHub/GitLab
Asegúrate de que todo el código del proyecto (incluyendo `render.yaml`, `Dockerfile` y `start.sh`) esté comiteado y pusheado a tu repositorio remoto (GitHub o GitLab).

### Paso 2: Conectar con Render.com
1. Inicia sesión en tu cuenta de [Render.com](https://render.com).
2. En el Dashboard principal, haz clic en el botón **New +** y selecciona **Blueprint**.
3. Conecta tu cuenta de GitHub/GitLab y selecciona el repositorio de `prompt_nexus`.

### Paso 3: Configuración Automática (render.yaml)
Al seleccionar el repositorio como Blueprint, Render leerá automáticamente el archivo `render.yaml`. 
Este archivo está configurado para:
* Crear un **Web Service** llamado `wanadi-vision`.
* Utilizar entorno **Docker**.
* Montar un **Disco Persistente** (`wanadi-data`) en `/app/database` para que las bases de datos SQLite (`nexus_prompts.db` y `nexus_bot.db`) no se pierdan cuando el contenedor se reinicie.
* Configurar el *Health Check* apuntando al endpoint `/api/v1/health/ready`.

### Paso 4: Configurar Variables de Entorno Seguras
El archivo `render.yaml` especifica que ciertas variables de entorno *no* se sincronizan automáticamente por seguridad (`sync: false`). 
Antes de que el servicio arranque con éxito, Render te pedirá que introduzcas los valores manualmente en el dashboard:

* `BOT_TOKEN`: El token de tu bot obtenido de BotFather.
* `ADMIN_CHAT_ID`: Tu ID numérico de Telegram para recibir alertas.

> **Nota:** La variable `NEXUS_API_URL` ya está preconfigurada a `http://127.0.0.1:8000/api/v1` en el yaml porque ambos servicios (Bot y API) se ejecutan dentro del mismo contenedor de red.

### Paso 5: Despliegue y Base de Datos
Una vez aplicados los cambios y configuradas las variables, Render comenzará la construcción (Build) basada en el `Dockerfile`.

1. **Build:** Instalará dependencias OS (C++, libgomp) necesarias para FAISS, y luego los paquetes de Python.
2. **Start:** Ejecutará `./start.sh`.

**¡Atención sobre la Base de Datos!** 
Dado que Render iniciará con un disco vacío en `/app/database`, debes inicializar la base de datos de prompts en el servidor. Puedes hacer esto de dos maneras:
* **Opción A (Recomendada):** Acceder a la Shell interactiva de tu servicio en el Dashboard de Render, navegar a `/app` y ejecutar `python -m database.populate_synthetic` o copiar tu `.db` existente usando utilidades como `scp`/`rsync` (requiere plan de pago o acceso shell específico).
* **Opción B:** Si tu base de datos SQLite pesa menos de 100MB, puedes incluirla en el repositorio Git temporalmente para el primer despliegue, y en el script de arranque copiarla al disco montado si este está vacío.

### 🎉 Verificación
Una vez que el despliegue marque estado **Live**:
1. Entra a la URL pública de tu API (ej. `https://wanadi-vision.onrender.com/api/v1/health/ready`) para verificar que FastAPI funciona.
2. Abre Telegram y envía `/start` a tu bot para comprobar que está respondiendo correctamente.
