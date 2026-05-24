# 🚀 Guía de Despliegue en Serv00 (FreeBSD) — Wanadi Vision

Este documento detalla el procedimiento paso a paso para desplegar el motor de búsqueda semántica y el bot de Telegram **Wanadi Vision** en servidores Serv00 (entorno FreeBSD).

---

## ⚙️ Diferencias Críticas: FreeBSD vs. Linux

*   **Sin Docker / Systemd:** Serv00 es un entorno compartido FreeBSD. No puedes correr contenedores Docker ni configurar servicios de `systemd`. Todo se corre mediante procesos en segundo plano con `nohup` o `daemon`.
*   **Shell compatible:** El shell por defecto de FreeBSD es `sh` o `tcsh`. Usa siempre `#!/bin/sh` al inicio de tus scripts y sourcea entornos virtuales usando `. venv/bin/activate` (el comando `source` puede no estar soportado).
*   **Gestión de PIDs:** Como no hay supervisor del sistema, guardamos los IDs de los procesos (PIDs) en archivos de texto dentro de un directorio `pids/` para poder monitorear y detener la aplicación de forma controlada.

---

## 📋 Requisitos Previos en el Panel de Serv00

Antes de comenzar el despliegue por SSH, realiza las siguientes configuraciones en el [Panel de Control de Serv00](https://panel.serv00.com):

1.  **Habilitar Binexec:** En la sección **Additional services**, asegúrate de que **Run system applications (Binexec)** esté configurado en **Enabled** (es indispensable para ejecutar binarios como Python o FAISS).
2.  **Reservar Puerto:** Ve a la sección **Port reservation** y reserva un puerto libre para la API de FastAPI (ejemplo: `8000`). Anota este puerto.

---

## 🛠️ Procedimiento de Despliegue (10 Pasos)

### Paso 1 — Acceso por SSH
Conéctate a tu cuenta de Serv00 usando tu cliente SSH preferido:
```bash
ssh tu_usuario@sX.serv00.com
```
*(Reemplaza `sX` por el número de tu servidor, por ejemplo: `s3.serv00.com`)*.

### Paso 2 — Clonar el Código del Proyecto
Navega a tu directorio de inicio y clona el repositorio del proyecto:
```bash
cd ~
git clone https://github.com/tu-usuario/prompt_nexus.git nexus_prompt_bot
cd nexus_prompt_bot
```

### Paso 3 — Configurar el Entorno Virtual (FreeBSD)
Crea y activa un entorno virtual de Python compatible con Serv00:
```bash
python3 -m venv venv
. venv/bin/activate
```

### Paso 4 — Instalar Dependencias
Instala las dependencias necesarias. Nota: FreeBSD compila ciertas dependencias C, por lo que este proceso puede tomar un par de minutos:
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Paso 5 — Configurar Variables de Entorno
Crea los archivos `.env` tanto para el bot como para el backend API copiando los ejemplos.

**Para el Bot (`bot/.env`):**
```bash
cp bot/.env.example bot/.env
nano bot/.env
```
*Configura los siguientes valores:*
```env
BOT_TOKEN=tu_telegram_bot_token
ADMIN_CHAT_ID=tu_telegram_chat_id
BOT_USERNAME=tu_bot_username
NEXUS_API_URL=http://127.0.0.1:8000/api/v1
```

**Para la API (`.env`):**
*Configura el puerto de escucha y las variables necesarias.*

### Paso 6 — Inicializar la Base de Datos y Clasificación
Ejecuta la inicialización de la base de datos de prompts y corre la migración inicial de categorías para clasificar los datos existentes:
```bash
python init_db.py
python database/migrate_prompts_db.py
```

### Paso 7 — Configurar Tareas Programadas (Cron Jobs)
Agrega los cron jobs en tu panel de Serv00 o mediante `crontab -e`.
Serv00 permite configurar cron directamente. Agrega estas tres reglas de cron:

| Expresión Cron | Comando | Descripción |
| :--- | :--- | :--- |
| `*/5 * * * *` | `cd ~/nexus_prompt_bot && sh watchdog.sh` | **Watchdog:** Revive la API y el Bot cada 5 minutos si se caen. |
| `0 */12 * * *` | `cd ~/nexus_prompt_bot && venv/bin/python miners/pipeline/ingestion_engine.py > logs/miner.log 2>&1` | **Minería:** Ingesta y clasifica nuevos prompts cada 12 horas. |
| `0 0 1 */2 *` | `cd ~/nexus_prompt_bot && sh renew.sh` | **Renovación:** Registra actividad en Serv00 cada 2 meses. |

### Paso 8 — Crear y Cargar Scripts de Gestión
El proyecto incluye scripts dedicados de control de procesos en la raíz:
*   [watchdog.sh](file:///media/obsidian/disco%20local1/prompt_nexus/watchdog.sh): Verifica si la API o el Bot están caídos y los reinicia automáticamente.
*   [stop.sh](file:///media/obsidian/disco%20local1/prompt_nexus/stop.sh): Lee los archivos PID y detiene los servicios de forma limpia.
*   [renew.sh](file:///media/obsidian/disco%20local1/prompt_nexus/renew.sh): Hace un curl al panel de Serv00 para simular actividad.

### Paso 9 — Levantar los Servicios Inicialmente
Puedes arrancar la aplicación por primera vez invocando el watchdog manualmente:
```bash
sh watchdog.sh
```
Esto creará el directorio `pids/` y escribirá los PIDs de la API y del Bot de Telegram, levantándolos en segundo plano.

---

## 📁 Estructura de Logs

Los logs de los procesos en ejecución se guardan en el directorio `logs/` para facilitar la depuración:
```text
logs/
├── api.log        ← Registro del framework FastAPI (Uvicorn)
├── bot.log        ← Registro del bot de Telegram (aiogram)
├── miner.log      ← Salida de la recolección periódica del pipeline ETL
├── watchdog.log   ← Eventos de monitoreo y reinicios de procesos
└── renew.log      ← Marca de tiempo de las renovaciones de actividad
```

---

## Paso 10 — Verificación y Comandos de Control

Para asegurar que todo funcione correctamente, ejecuta los siguientes comandos de verificación:

### 1. Comprobar PIDs en Ejecución
Verifica que los archivos PID contengan números válidos de proceso:
```bash
cat pids/api.pid && cat pids/bot.pid
```

### 2. Inspeccionar Logs en Tiempo Real
Sigue los logs de la API o el Bot para verificar que procesen peticiones sin errores:
```bash
tail -f logs/api.log
tail -f logs/bot.log
```

### 3. Probar la API de Recuperación Localmente
Prueba el motor de búsqueda semántica local desde la terminal:
```bash
curl "http://127.0.0.1:8000/api/v1/search?q=cyberpunk+city&top_k=3"
```

### 4. Prueba del Bot en Telegram
1. Abre Telegram y escribe `/start` a tu bot.
2. Pulsa en **🗂️ Explorar Categorías** o envía el comando `/categorias`.
3. Selecciona una categoría y una subcategoría de los botones.
4. Responde a la pregunta de fidelidad facial y comprueba que se listen 5 prompts con paginación funcional y botones 👍 de voto útil.
