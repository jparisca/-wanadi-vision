"""
Wanadi Vision — Motor de Decisión Táctica para Búsqueda Semántica de Prompts.
Arquitectura: Webhook / Long-polling con aiogram 3.x
"""

import os
import sys
import asyncio
import logging
from pathlib import Path
from dotenv import load_dotenv

# Cargar variables de entorno desde bot/.env automáticamente
_env_file = Path(__file__).parent / ".env"
if _env_file.exists():
    load_dotenv(_env_file)

# ─── Path setup ───────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
)
from aiogram.filters import CommandStart, Command, CommandObject
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext

from bot.db import BotDB
from bot.search_client import NexusSearchClient
from bot import admin as admin_module

# Importar manejadores modulares
from bot.handlers.categories import router as categories_router
from bot.handlers.payments import router as payments_router, mostrar_paywall
from bot.handlers.referrals import router as referrals_router
from bot.config import BOT_TOKEN, ADMIN_CHAT_ID, NEXUS_API_URL, FREE_BUSQUEDAS_DIA, BOT_USERNAME

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("NexusBot")

# ─── Instancias globales ──────────────────────────────────────────────────────
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp  = Dispatcher(storage=MemoryStorage())
db  = BotDB()
nexus = NexusSearchClient(base_url=NEXUS_API_URL)

# Incluir todos los routers
dp.include_router(admin_module.router)
dp.include_router(categories_router)
dp.include_router(payments_router)
dp.include_router(referrals_router)


# ─── Keyboards ────────────────────────────────────────────────────────────────
def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔍 Buscar Prompt",   callback_data="do_search")],
        [InlineKeyboardButton(text="🗂️ Explorar Categorías", callback_data="abrir_categorias")],
        [InlineKeyboardButton(text="📊 Ver Planes", callback_data="ver_planes")],
        [InlineKeyboardButton(text="ℹ️ Cómo funciona",  callback_data="how_it_works")],
    ])

def search_results_kb(results: list) -> InlineKeyboardMarkup:
    buttons = []
    for i, r in enumerate(results[:5]):
        engine = r.get("engine", "?")
        buttons.append([InlineKeyboardButton(
            text=f"📋 Ver #{i+1} · {engine}",
            callback_data=f"view_{i}"
        )])
    buttons.append([InlineKeyboardButton(text="🔍 Nueva búsqueda", callback_data="do_search")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ─── Handlers Generales ────────────────────────────────────────────────────────

@dp.message(CommandStart())
async def cmd_start(msg: Message, state: FSMContext):
    await state.clear()
    
    # Manejar referidos
    args = msg.text.split()
    if len(args) > 1 and args[1].startswith("ref_"):
        try:
            referrer_id = int(args[1].split("_")[1])
            if referrer_id != msg.from_user.id:
                await db.save_referral(new_user_id=msg.from_user.id, referrer_id=referrer_id)
                log.info(f"Referido guardado: nuevo {msg.from_user.id} por referidor {referrer_id}")
        except Exception as e:
            log.error(f"Error procesando referido en start: {e}")
            
    # Registrar usuario
    user = await db.get_or_create_user(
        user_id=msg.from_user.id,
        full_name=msg.from_user.full_name,
        username=msg.from_user.username or ""
    )
    
    plan = user.get("plan", "free")
    
    # Calcular límites
    if plan == "free":
        await db.puede_buscar(msg.from_user.id)  # Forzar reset diario vago
        user_updated = await db.get_or_create_user(msg.from_user.id, msg.from_user.full_name)
        remaining = max(0, FREE_BUSQUEDAS_DIA - user_updated.get("busquedas_hoy", 0))
        limit_text = f"🆓 Búsquedas gratuitas hoy: <b>{remaining}/{FREE_BUSQUEDAS_DIA}</b>"
    elif plan == "starter":
        await db.puede_buscar(msg.from_user.id)  # Forzar reset mensual vago
        user_updated = await db.get_or_create_user(msg.from_user.id, msg.from_user.full_name)
        from bot.config import STARTER_BUSQUEDAS_MES
        remaining = max(0, STARTER_BUSQUEDAS_MES - user_updated.get("busquedas_mes", 0))
        limit_text = f"⚡ Búsquedas starter restantes: <b>{remaining}/{STARTER_BUSQUEDAS_MES}</b>"
    else:
        limit_text = f"🔥 Plan <b>{plan.upper()}</b>: Búsquedas <b>Ilimitadas</b>"

    await msg.answer(
        f"💠 <b>Bienvenido a Wanadi Vision</b>, {msg.from_user.first_name}!\n\n"
        f"El motor semántico táctico más completo de prompts para IA.\n"
        f"🎯 <b>Midjourney · Stable Diffusion · Flux · ChatGPT</b>\n\n"
        f"🔢 <b>10,000+ prompts</b> indexados de alta fidelidad\n"
        f"{limit_text}\n\n"
        f"¿Qué imagen quieres crear hoy?",
        reply_markup=main_menu_kb()
    )


@dp.callback_query(F.data == "do_search")
async def cb_do_search(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await cb.message.answer("🔍 <b>¿Qué tipo de imagen quieres generar?</b>\n\nEscríbeme una descripción y te busco los mejores prompts:")
    await cb.answer()


@dp.callback_query(F.data == "how_it_works")
async def cb_how_it_works(cb: CallbackQuery):
    await cb.message.answer(
        "ℹ️ <b>Arquitectura Wanadi Vision</b>\n\n"
        "1️⃣ Escribe lo que quieres crear (en español o inglés)\n"
        "2️⃣ Nuestro motor semántico busca los mejores prompts reales\n"
        "3️⃣ Copia el prompt y pégalo en Midjourney, Stable Diffusion o Flux\n\n"
        "📡 <b>Fuentes:</b> Reddit · Civitai · X/Twitter · Threads\n"
        "🔄 Base de datos actualizada <b>cada 12 horas</b> automáticamente\n\n"
        "🆓 <b>Planes Disponibles:</b>\n"
        "• Gratis: 3 búsquedas al día\n"
        "• Starter: 50 búsquedas al mes por 385 Stars\n"
        "• Pro: Ilimitado por 1154 Stars (pago único)\n"
        "• Teams: Búsquedas ilimitadas para hasta 5 personas por 3769 Stars",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔍 Buscar ahora", callback_data="do_search")],
            [InlineKeyboardButton(text="📊 Ver Planes", callback_data="ver_planes")],
        ])
    )
    await cb.answer()


@dp.callback_query(F.data == "main_menu")
async def cb_main_menu(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await cb.message.answer("Menú principal:", reply_markup=main_menu_kb())
    await cb.answer()


# ─── Comandos Especiales ──────────────────────────────────────────────────────

@dp.message(Command("demo"))
async def cmd_demo(msg: Message):
    """
    Muestra una demo buscando 'landscape photography' sin costo.
    """
    await msg.answer("⏳ Generando demostración táctica de búsqueda...")
    try:
        results = await nexus.search(query="landscape photography", top_k=2)
        if not results:
            await msg.answer("No se encontraron prompts de demo en el índice.")
            return
            
        response_lines = [
            "💠 <b>Demostración de Wanadi Vision</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
        ]
        for i, r in enumerate(results, 1):
            response_lines.append(
                f"<b>#{i}</b> · {r['engine']} · ⭐{r['score']:.2f}\n"
                f"<code>{r['prompt_text']}</code>\n"
                f"📌 <i>Fuente: {r['source']}</i>\n"
            )
        response_lines.append("\nRegístrate gratis → /start")
        await msg.answer("\n".join(response_lines))
    except Exception as e:
        log.error(f"Demo error: {e}")
        await msg.answer("❌ Error al recuperar la demo de búsqueda.")


@dp.message(Command("compartir"))
async def cmd_compartir(msg: Message, command: CommandObject):
    """
    Genera un bloque de texto formateado listo para compartir con branding.
    """
    prompt_text = command.args
    if not prompt_text:
        await msg.answer("⚠️ Uso: <code>/compartir tu prompt de inteligencia artificial aquí</code>")
        return
        
    share_msg = (
        f"💠 <b>Prompt compartido vía @{BOT_USERNAME}</b>\n\n"
        f"<code>{prompt_text}</code>\n\n"
        f"🎯 <i>Encuentra más de 10,000 prompts tácticos gratis en nuestro bot.</i>"
    )
    await msg.answer(share_msg)


@dp.message(Command("addmember"))
async def cmd_addmember(msg: Message, command: CommandObject):
    """
    Permite al administrador de un equipo agregar integrantes.
    """
    admin_id = msg.from_user.id
    target_username = command.args
    
    if not target_username:
        await msg.answer("⚠️ Uso: <code>/addmember @username</code>")
        return
        
    target_username = target_username.lstrip("@").strip()
    
    # 1. Obtener equipo
    team = await db.get_team_by_user(admin_id)
    if not team or team["admin_user_id"] != admin_id:
        await msg.answer("❌ Este comando solo está disponible para administradores de planes de equipo.")
        return
        
    # 2. Buscar al usuario
    user = await db.get_user_by_username(target_username)
    if not user:
        await msg.answer(
            f"⚠️ El usuario <b>@{target_username}</b> no se ha registrado en el bot aún.\n"
            "Pídele que inicie el bot primero enviando /start para registrarlo."
        )
        return
        
    # 3. Agregar miembro
    team_id = team["id"]
    success = await db.add_team_member(team_id, user["user_id"])
    if success:
        await msg.answer(
            f"✅ ¡Usuario <b>@{target_username}</b> agregado con éxito a tu equipo!\n"
            "Ahora disfruta de búsquedas ilimitadas en su cuenta."
        )
        # Notificar al miembro
        try:
            await bot.send_message(
                user["user_id"],
                "🎉 ¡Has sido agregado a un plan de equipo por tu administrador!\n"
                "Ahora tienes acceso táctico ilimitado a Wanadi Vision."
            )
        except Exception:
            pass
    else:
        await msg.answer("❌ No se pudo agregar al miembro. Límite máximo de 5 integrantes de equipo alcanzado.")


@dp.callback_query(F.data.startswith("view_"))
async def cb_view_result(cq: CallbackQuery, state: FSMContext):
    """
    Muestra el prompt completo sin truncar de la búsqueda semántica.
    """
    idx = int(cq.data.split("_")[1])
    data = await state.get_data()
    results = data.get("search_results", [])
    
    if not results or idx >= len(results):
        await cq.answer("Resultados expirados. Realiza otra búsqueda.", show_alert=True)
        return
        
    r = results[idx]
    prompt_text = r.get("prompt_text", "")
    engine = r.get("engine", "Unknown")
    score = r.get("score", 0.0)
    source = r.get("source", "nexus")
    
    response = (
        f"✨ <b>Prompt #{idx+1} · {engine}</b> · ⭐{score:.2f}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"<code>{prompt_text}</code>\n\n"
        f"📌 <i>Fuente: {source}</i>\n"
    )
    await cq.message.answer(response)
    await cq.answer()


# ─── Búsqueda Semántica de Texto Libre ────────────────────────────────────────

@dp.message(F.text)
async def handle_search_query(msg: Message, state: FSMContext):
    user_id = msg.from_user.id
    query = msg.text.strip()
    
    # Ignorar si es comando
    if query.startswith("/"):
        return
        
    # Lazy register/update
    await db.get_or_create_user(user_id, msg.from_user.full_name, msg.from_user.username or "")
    
    # 1. Validar límite
    puede, motivo = await db.puede_buscar(user_id, msg.from_user.full_name)
    if not puede:
        await mostrar_paywall(msg, motivo)
        return
        
    # 2. Ejecutar búsqueda
    await msg.answer("⏳ Buscando en 10,000+ prompts...")
    try:
        results = await nexus.search(query=query, top_k=5)
    except Exception as e:
        log.error(f"Search error: {e}")
        await msg.answer("❌ Error conectando al servidor. Intenta de nuevo.")
        return
        
    if not results:
        await msg.answer(
            "😕 No encontré prompts para esa búsqueda.\n"
            "Intenta con palabras en inglés o una descripción diferente."
        )
        return
        
    # 3. Guardar resultados en FSM context para "Ver más"
    await state.update_data(search_results=results)
    
    # 4. Incrementar contador
    await db.increment_searches_counter(user_id)
    
    # 5. Obtener límites actualizados
    user_updated = await db.get_or_create_user(user_id, msg.from_user.full_name)
    plan = user_updated.get("plan", "free")
    
    if plan == "free":
        remaining = max(0, FREE_BUSQUEDAS_DIA - user_updated.get("busquedas_hoy", 0))
        limit_text = f"búsquedas gratuitas restantes hoy: <b>{remaining}</b>"
    elif plan == "starter":
        from bot.config import STARTER_BUSQUEDAS_MES
        remaining = max(0, STARTER_BUSQUEDAS_MES - user_updated.get("busquedas_mes", 0))
        limit_text = f"búsquedas starter restantes este mes: <b>{remaining}</b>"
    else:
        limit_text = "búsquedas ilimitadas"
        
    header = (
        f"✨ <b>Resultados para:</b> <i>{query}</i>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔢 {limit_text.capitalize()}\n\n"
    )
    
    response_lines = [header]
    for i, r in enumerate(results, 1):
        prompt_text = r.get("prompt_text", "")
        # Truncar visualmente
        display_text = prompt_text[:280] + "..." if len(prompt_text) > 280 else prompt_text
        response_lines.append(
            f"<b>#{i}</b> · {r.get('engine', 'Unknown')} · ⭐{r.get('score', 0.0):.2f}\n"
            f"<code>{display_text}</code>\n"
            f"📌 <i>Fuente: {r.get('source', 'nexus')}</i>\n"
        )
        
    await msg.answer(
        "\n".join(response_lines),
        reply_markup=search_results_kb(results)
    )


# ─── Entry Point ──────────────────────────────────────────────────────────────
async def main():
    if not BOT_TOKEN:
        log.error("❌ BOT_TOKEN no configurado. Crea bot/.env con tu token de @BotFather")
        return
    log.info("💠 Wanadi Vision Bot iniciando con aiogram 3.x...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
