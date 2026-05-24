# 🤗 Manual de Despliegue en HuggingFace Spaces

Guía completa para desplegar **Wanadi Vision** (Bot + API) gratuitamente en HuggingFace Spaces usando Docker, **sin tarjeta de crédito**.

## ✅ Requisitos Previos
- Cuenta gratuita en [huggingface.co](https://huggingface.co/join) (solo email)
- El repositorio de GitHub ya subido: `github.com/jparisca/-wanadi-vision`
- Tu `BOT_TOKEN` de Telegram (de BotFather)

---

## 🛠️ Pasos de Despliegue

### Paso 1: Crear un nuevo Space
1. Entra a [huggingface.co/new-space](https://huggingface.co/new-space)
2. Configura los campos así:
   - **Space name:** `wanadi-vision`
   - **License:** MIT
   - **Select SDK:** Docker ← **muy importante**
   - **Hardware:** CPU basic (FREE, 2vCPU 16GB RAM) ← el gratuito
   - **Visibility:** Public ← necesario para el plan gratuito
3. Haz clic en **Create Space**

### Paso 2: Conectar con GitHub (sincronización automática)
En lugar de subir archivos manualmente, puedes vincular tu repositorio de GitHub para que HuggingFace se sincronice automáticamente:

1. En tu Space recién creado, ve a **Settings** (pestaña)
2. Busca la sección **"Linked GitHub repository"**
3. Conecta tu cuenta de GitHub y selecciona el repositorio `jparisca/-wanadi-vision`
4. Rama: `main`

Desde ahora, cada vez que hagas `git push`, HuggingFace reconstruirá automáticamente el contenedor. 🎉

> **Alternativa manual:** Si no quieres conectar GitHub, puedes clonar el repositorio del Space que HF crea (es un repo Git con URL `https://huggingface.co/spaces/TU_USUARIO/wanadi-vision`) y hacer push directo ahí.

### Paso 3: Configurar Variables de Entorno Secretas
Este es el paso **más importante** — aquí le damos al bot su token sin exponerlo en el código:

1. En tu Space, ve a **Settings** → sección **"Repository secrets"**
2. Añade estos secretos uno por uno haciendo clic en **"New secret"**:

| Nombre | Valor |
|--------|-------|
| `BOT_TOKEN` | Tu token de BotFather (ej. `7123456789:AAF...`) |
| `ADMIN_CHAT_ID` | Tu ID de Telegram (número, ej. `123456789`) |

> **¿Cómo saber tu Chat ID?** Escríbele a [@userinfobot](https://t.me/userinfobot) en Telegram, te responde con tu ID.

### Paso 4: Verificar el Build
Tras configurar los secretos, HuggingFace iniciará automáticamente el build del Dockerfile. Puedes ver el progreso en la pestaña **"Logs"** del Space.

El build tarda entre **5 y 15 minutos** la primera vez (está descargando PyTorch y FAISS). Las siguientes actualizaciones son mucho más rápidas gracias al caché de capas Docker.

### Paso 5: ¡Listo! Verificar que funciona
Una vez que el Space esté en estado **"Running"** (punto verde):
- **API:** Entra a `https://TU_USUARIO-wanadi-vision.hf.space/api/v1/health/ready` — debe responder `{"status": "ok"}`
- **Bot:** Abre Telegram y escríbele `/start` a tu bot

---

## 🔋 Mantener el Space Despierto (Anti-Sleep)

HuggingFace pone el Space a "dormir" tras **48 horas sin tráfico**. Para evitarlo:

1. Crea una cuenta gratuita en [uptimerobot.com](https://uptimerobot.com)
2. Crea un nuevo monitor tipo **"HTTP(s)"**:
   - **URL:** `https://TU_USUARIO-wanadi-vision.hf.space/api/v1/health/ready`
   - **Intervalo:** cada 5 minutos
3. ¡Listo! UptimeRobot hará ping cada 5 minutos y el Space nunca se dormirá. También te avisará por email si cae.

---

## 🗄️ Base de Datos — Nota Importante

HuggingFace Spaces **no tiene disco persistente en el plan gratuito**. Esto significa que si el Space se reinicia, la base de datos de usuarios (`nexus_bot.db`) se resetea (se pierden los contadores de búsquedas y los usuarios registrados).

**Soluciones gratuitas para persistencia:**
- **Opción A (Recomendada):** Usar [Supabase](https://supabase.com) como base de datos PostgreSQL gratuita y conectar `bot/db.py` a Supabase en lugar de SQLite. Supabase no pide TDC.
- **Opción B:** Usar el dataset de HuggingFace como almacenamiento persistente (más complejo de configurar pero 100% dentro del ecosistema HF).
- **Opción C (Simple):** Aceptar que los usuarios deben "re-registrarse" cada vez que el Space se reinicia (cada vez que haces un nuevo deploy). Para el lanzamiento inicial, esto es aceptable.

Para la base de datos de prompts (`nexus_prompts.db`), como es de **solo lectura** (no cambia con el uso), sí puedes incluirla directamente en el repositorio de GitHub y se copiará al contenedor en cada build.

---

## 📋 Resumen de Archivos Clave

| Archivo | Propósito |
|---------|-----------|
| `README.md` | Metadatos del Space (SDK, puerto, título) |
| `Dockerfile` | Construcción del contenedor (puerto 7860) |
| `start.sh` | Inicia Bot (background) + API (foreground) |
| `requirements.txt` | Dependencias Python |
