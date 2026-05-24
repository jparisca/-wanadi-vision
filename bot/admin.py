"""
Admin commands for the Nexus Prompt Bot.
Añade comandos de administración solo accesibles desde ADMIN_CHAT_ID.
"""

import os
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message

from bot.db import BotDB

router = Router()
db = BotDB()

ADMIN_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))


def is_admin(msg: Message) -> bool:
    return ADMIN_ID > 0 and msg.from_user.id == ADMIN_ID


@router.message(Command("admin"))
async def cmd_admin(msg: Message):
    if not is_admin(msg):
        return

    stats = await db.stats()
    from search.index_manager import IndexManager
    import asyncio
    loop = asyncio.get_event_loop()
    index_stats = await loop.run_in_executor(None, lambda: IndexManager().stats())

    await msg.answer(
        "🔧 <b>Panel Admin — Nexus Prompt</b>\n\n"
        f"👤 Usuarios totales  : <b>{stats['total_users']}</b>\n"
        f"⭐ Usuarios premium  : <b>{stats['premium_users']}</b>\n"
        f"🔍 Búsquedas totales : <b>{stats['total_searches']}</b>\n\n"
        f"📊 <b>Índice FAISS</b>\n"
        f"  Vectores    : <b>{index_stats['active_vectors']:,}</b>\n"
        f"  Algoritmo   : <b>{index_stats['using_ann']}</b>\n"
        f"  Último sync : <b>{index_stats['last_refreshed']}</b>\n\n"
        f"💰 <b>Revenue estimado</b>: ${stats['premium_users'] * 15} USD"
    )


@router.message(Command("grant"))
async def cmd_grant(msg: Message):
    """Uso: /grant 123456789  — activa premium manualmente."""
    if not is_admin(msg):
        return

    parts = msg.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        await msg.answer("Uso: /grant <user_id>")
        return

    target_id = int(parts[1])
    await db.upgrade_to_premium(target_id)
    await msg.answer(f"✅ Usuario <b>{target_id}</b> activado como premium.")


@router.message(Command("stats"))
async def cmd_stats(msg: Message):
    if not is_admin(msg):
        return
    stats = await db.stats()
    await msg.answer(
        f"📈 <b>Stats rápidas</b>\n"
        f"Usuarios: {stats['total_users']} | Premium: {stats['premium_users']} | "
        f"Búsquedas: {stats['total_searches']}"
    )
