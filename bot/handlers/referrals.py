"""
bot/handlers/referrals.py — Wanadi Vision: Sistema de referidos y recompensas.
"""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message

from bot.config import BOT_USERNAME
from bot.db import BotDB

router = Router()
db = BotDB()


@router.message(Command("milink"))
async def cmd_milink(msg: Message):
    """
    Genera el enlace de referidos único para el usuario.
    """
    user_id = msg.from_user.id
    ref_link = f"https://t.me/{BOT_USERNAME}?start=ref_{user_id}"
    
    response = (
        "🔗 <b>Tu Enlace de Referidos de Wanadi Vision</b>\n\n"
        "Comparte este enlace con otros creadores o diseñadores. "
        "Por cada amigo que use tu link y se suscriba a cualquier plan de pago, "
        "recibirás una recompensa:\n\n"
        "🎁 <b>Recompensa:</b> ¡Cada 5 amigos que compren un plan, obtienes <b>1 mes de Plan Starter totalmente gratis</b>!\n\n"
        f"<code>{ref_link}</code>\n\n"
        "<i>Pulsa sobre el enlace de arriba para copiarlo automáticamente.</i>"
    )
    await msg.answer(response)


@router.message(Command("misreferidos"))
@router.message(Command("mis_referidos"))
async def cmd_mis_referidos(msg: Message):
    """
    Muestra las estadísticas de referidos del usuario.
    """
    user_id = msg.from_user.id
    stats = await db.get_referral_count(user_id)
    
    total = stats.get("total", 0)
    converted = stats.get("converted", 0)
    needed_for_next = 5 - (converted % 5)
    
    response = (
        "📊 <b>Tus Estadísticas de Referidos</b>\n\n"
        f"• Amigos registrados con tu link: <b>{total}</b>\n"
        f"• Amigos que han comprado un plan (Conversión): <b>{converted}</b>\n\n"
        f"🎯 Te faltan <b>{needed_for_next}</b> conversiones para recibir tu próximo mes de Starter gratis."
    )
    await msg.answer(response)
