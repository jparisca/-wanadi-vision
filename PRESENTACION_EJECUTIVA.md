# 🚀 Wanadi Vision: The Ultimate AI Prompt Nexus

## 1. Resumen Ejecutivo
**Wanadi Vision** es una plataforma integral impulsada por IA (Bot de Telegram + API Backend) diseñada para revolucionar cómo los creadores descubren, gestionan y aplican prompts para generación de imágenes (Midjourney, DALL-E 3, Stable Diffusion).  
No es solo un buscador; es un "Nexus" que combina **búsqueda semántica (FAISS)**, **clasificación inteligente por categorías**, y un **modelo de monetización nativo** a través de Telegram Stars.

## 2. Problema y Oportunidad
* **El Problema:** La creación de prompts avanzados es un arte complejo. Las galerías actuales están fragmentadas, carecen de búsqueda semántica real y no se integran directamente en el flujo de trabajo de los usuarios (mensajería móvil).
* **La Solución:** Un bot de Telegram con acceso a más de 10,000 prompts curados, con un motor de búsqueda que entiende el *contexto* (semántica) y no solo palabras clave.

## 3. Características Clave
* 🔍 **Búsqueda Semántica Avanzada:** Desarrollado sobre FAISS (Facebook AI Similarity Search) para ofrecer resultados precisos y contextualmente relevantes en milisegundos.
* 🗂️ **Navegación Visual por Categorías:** Interfaz amigable con botones *Inline* (Telegram) para explorar 15 categorías principales y decenas de subcategorías sin escribir una sola palabra.
* 🤖 **Integración de "Selfie Mode":** Modificación en tiempo real de los prompts para incluir instrucciones precisas de retención de rostro ("fidelidad facial"), optimizado para avatares e influencers digitales.
* 💸 **Modelo de Negocio Integrado (Paywall):** 
  * **Free:** 3 búsquedas al día.
  * **Starter:** 50 búsquedas/mes (~385 Stars).
  * **Pro:** Búsquedas ilimitadas (~1154 Stars).
  * **Teams:** Hasta 5 usuarios compartidos + Acceso a la API (~3769 Stars).
* 🔗 **Sistema de Referidos (Growth):** Generación de enlaces únicos que otorgan búsquedas extra para fomentar el crecimiento viral (modelo "DropBox").

## 4. Arquitectura Técnica
* **Frontend/Bot:** `aiogram 3.x` (Asíncrono, rápido, nativo para Telegram).
* **Backend API:** `FastAPI` (Alto rendimiento, autodescriptivo, arquitectura RESTful).
* **Base de Datos & Indexación:** `SQLite` (Persistencia ligera y rápida) + `FAISS` (Indexación vectorial en memoria para la búsqueda semántica).
* **Infraestructura:** Despliegue unificado y en contenedores (`Docker`) en **Render.com** (Web Service + Persistent Disk), asegurando portabilidad y fácil escalabilidad.

## 5. Plan de Lanzamiento (Estrategia "Guerrilla")
1. **Días 1-10 (Soft Launch & Seeding):** 
   * Pruebas beta cerradas y seeding en comunidades (Discord/Reddit de AI Art).
   * Uso del sistema de referidos en grupos cerrados.
2. **Días 11-20 (Viralización "Selfie Mode"):** 
   * Campaña en redes centrada en la función exclusiva de preservar el rostro usando los prompts de la base de datos.
3. **Días 21-30 (Monetización & Partnerships):** 
   * Activación progresiva del paywall con Telegram Stars.
   * Onboarding de equipos creativos / agencias pequeñas al plan *Teams*.

---
> *Wanadi Vision convierte la inspiración difusa en instrucciones técnicas precisas, accesibles desde el bolsillo de cada creador.*
