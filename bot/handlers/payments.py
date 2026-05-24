"""
bot/handlers/payments.py — Wanadi Vision: Sistema de pagos nativo con Telegram Stars.
"""
import secrets
import logging
from aiogram import Router, F, Bot
from aiogram.types import (
    CallbackQuery, Message, PreCheckoutQuery,
    InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice
)
from aiogram.filters import Command

from bot.config import (
    PRECIO_STARTER_STARS, PRECIO_PRO_STARS, PRECIO_TEAMS_STARS, ADMIN_CHAT_ID
)
from bot.db import BotDB

log = logging.getLogger("NexusBot.Payments")
router = Router()
db = BotDB()


# ─── Keyboards ────────────────────────────────────────────────────────────────

def get_planes_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚡ Starter (385 ⭐)", callback_data="pagar_starter")],
        [InlineKeyboardButton(text="🔥 Pro (1154 ⭐)", callback_data="pagar_pro")],
        [InlineKeyboardButton(text="👥 Teams (3769 ⭐)", callback_data="pagar_teams")],
        [InlineKeyboardButton(text="🔙 Volver", callback_data="main_menu")]
    ])


def get_paywall_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⚡ Starter (385 ⭐)", callback_data="pagar_starter"),
            InlineKeyboardButton(text="🔥 Pro (1154 ⭐)", callback_data="pagar_pro")
        ],
        [InlineKeyboardButton(text="👥 Teams (3769 ⭐)", callback_data="pagar_teams")],
        [InlineKeyboardButton(text="📊 Comparar Planes", callback_data="ver_planes")],
        [InlineKeyboardButton(text="🔙 Volver al menú", callback_data="main_menu")]
    ])


# ─── Handlers ─────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "ver_planes")
async def cb_ver_planes(cq: CallbackQuery):
    table = (
        "📊 <b>Wanadi Vision — Comparativa de Planes</b>\n\n"
        "🟢 <b>Gratuito (Free)</b>\n"
        "• 3 búsquedas al día (no acumulables)\n"
        "• Acceso a base de datos básica\n"
        "• Costo: 0 Stars/mes\n\n"
        "⚡ <b>Starter</b>\n"
        "• 50 búsquedas al mes\n"
        "• Búsqueda semántica táctica de alta velocidad\n"
        "• Costo: <b>385 Stars</b> (~$5 USD/mes)\n\n"
        "🔥 <b>Pro</b>\n"
        "• Búsquedas semánticas ilimitadas (Lifetime)\n"
        "• Modo Selfie (Fidelidad Facial)\n"
        "• Costo: <b>1154 Stars</b> (~$15 USD pago único)\n\n"
        "👥 <b>Teams (B2B SaaS)</b>\n"
        "• Búsquedas ilimitadas para hasta 5 personas\n"
        "• Acceso a API Privada (500 req/día)\n"
        "• API key autogenerada al instante\n"
        "• Costo: <b>3769 Stars</b> (~$49 USD/mes)\n\n"
        "<i>Elige tu plan a continuación:</i>"
    )
    await cq.message.edit_text(table, reply_markup=get_planes_markup())
    await cq.answer()


@router.message(Command("planes"))
async def cmd_planes(msg: Message):
    table = (
        "📊 <b>Wanadi Vision — Comparativa de Planes</b>\n\n"
        "🟢 <b>Gratuito (Free)</b>\n"
        "• 3 búsquedas al día (no acumulables)\n"
        "• Costo: 0 Stars/mes\n\n"
        "⚡ <b>Starter</b>\n"
        "• 50 búsquedas al mes\n"
        "• Costo: <b>385 Stars</b> (~$5 USD/mes)\n\n"
        "🔥 <b>Pro</b>\n"
        "• Búsquedas semánticas ilimitadas (Lifetime)\n"
        "• Modo Selfie (Fidelidad Facial)\n"
        "• Costo: <b>1154 Stars</b> (~$15 USD pago único)\n\n"
        "👥 <b>Teams (B2B SaaS)</b>\n"
        "• Búsquedas ilimitadas para hasta 5 personas\n"
        "• Acceso a API Privada (500 req/día)\n"
        "• Costo: <b>3769 Stars</b> (~$49 USD/mes)\n\n"
        "<i>Elige tu plan a continuación:</i>"
    )
    await msg.answer(table, reply_markup=get_planes_markup())


@router.callback_query(F.data == "pagar_starter")
async def cb_pagar_starter(cq: CallbackQuery):
    await cq.message.answer_invoice(
        title="⚡ Wanadi Vision — Plan Starter",
        description="50 búsquedas mensuales de prompts de IA de alta fidelidad.",
        payload=f"plan_starter_{cq.from_user.id}",
        currency="XTR",
        prices=[LabeledPrice(label="Starter mensual", amount=PRECIO_STARTER_STARS)],
        protect_content=False
    )
    await cq.answer()


@router.callback_query(F.data == "pagar_pro")
async def cb_pagar_pro(cq: CallbackQuery):
    await cq.message.answer_invoice(
        title="🔥 Wanadi Vision — Plan Pro (Lifetime)",
        description="Búsquedas ilimitadas + Instrucción de fidelidad facial en todos los prompts.",
        payload=f"plan_pro_{cq.from_user.id}",
        currency="XTR",
        prices=[LabeledPrice(label="Pro de por vida", amount=PRECIO_PRO_STARS)],
        protect_content=False
    )
    await cq.answer()


@router.callback_query(F.data == "pagar_teams")
async def cb_pagar_teams(cq: CallbackQuery):
    await cq.message.answer_invoice(
        title="👥 Wanadi Vision — Plan Teams",
        description="Búsquedas ilimitadas + API key + hasta 5 integrantes de equipo.",
        payload=f"plan_teams_{cq.from_user.id}",
        currency="XTR",
        prices=[LabeledPrice(label="Teams mensual", amount=PRECIO_TEAMS_STARS)],
        protect_content=False
    )
    await cq.answer()


@router.pre_checkout_query()
async def pre_checkout_handler(pcq: PreCheckoutQuery, bot: Bot):
    """
    Aprueba la pre-transacción de pago de Telegram.
    Debe responder en menos de 10 segundos.
    """
    try:
        await bot.answer_pre_checkout_query(pcq.id, ok=True)
    except Exception as e:
        log.error(f"Error en pre-checkout: {e}")


@router.message(F.successful_payment)
async def pago_ok(msg: Message, bot: Bot):
    """
    Maneja el pago exitoso de Telegram Stars, activa el plan y registra la transacción.
    """
    user_id = msg.from_user.id
    stars = msg.successful_payment.total_amount
    charge_id = msg.successful_payment.telegram_payment_charge_id
    payload = msg.successful_payment.invoice_payload
    
    plan = "free"
    if "starter" in payload:
        plan = "starter"
    elif "pro" in payload:
        plan = "pro"
    elif "teams" in payload:
        plan = "teams"
        
    log.info(f"Pago OK de usuario {user_id}: {stars} estrellas para plan '{plan}' (Charge ID: {charge_id})")
    
    # 1. Guardar pago en base de datos
    await db.save_payment(user_id, charge_id, stars, plan)
    
    # 2. Activar plan y dar feedback correspondiente
    if plan == "teams":
        # Generar API Key única
        api_key = f"wv_{secrets.token_urlsafe(32)}"
        team_id = await db.create_team(admin_user_id=user_id, api_key=api_key)
        # Activar el plan y asociar team_id
        await db.activate_plan(user_id, plan, team_id=team_id)
        
        await msg.answer(
            "🎉 <b>¡Pago del Plan Teams Confirmado!</b>\n\n"
            "✅ Tu equipo B2B ha sido creado con éxito en Wanadi Vision.\n"
            "🗝️ <b>Tu API KEY Privada es:</b>\n"
            f"<code>{api_key}</code>\n\n"
            "⚠️ <i>Guarda esta llave en un lugar seguro. No la vuelvas a compartir.</i>\n\n"
            "👥 <b>Gestión de Miembros (Máx 5):</b>\n"
            "Usa el comando /addmember @username para añadir integrantes de tu equipo a tu plan."
        )
    else:
        await db.activate_plan(user_id, plan)
        
        plan_display = plan.capitalize()
        await msg.answer(
            f"🎉 <b>¡Pago del Plan {plan_display} Confirmado!</b>\n\n"
            f"✅ Tu cuenta ha sido activada en el plan <b>{plan_display}</b>.\n"
            f"⭐ Estrellas procesadas: <b>{stars} Stars</b>.\n\n"
            "¡Ya puedes empezar a explorar o buscar prompts!"
        )

    # 3. Marcar si fue referido para que cuente como conversión pagada
    await db.mark_referral_converted(user_id)
    
    # 4. Notificar a administradores
    if ADMIN_CHAT_ID:
        try:
            await bot.send_message(
                ADMIN_CHAT_ID,
                f"💰 <b>NUEVA VENTA CONFIRMADA</b>\n\n"
                f"• Usuario: {msg.from_user.full_name} (ID: {user_id})\n"
                f"• Plan: <b>{plan.upper()}</b>\n"
                f"• Stars: {stars} ⭐\n"
                f"• Charge ID: {charge_id}"
            )
        except Exception as e:
            log.error(f"Error notificando al admin: {e}")


async def mostrar_paywall(event, motivo: str):
    """
    Función utilitaria para mostrar el paywall cuando el límite del plan se alcanza.
    """
    msg = event if isinstance(event, Message) else event.message
    
    if motivo == "paywall_free":
        text = (
            "🔒 <b>Límite de Búsquedas Gratis Alcanzado</b>\n\n"
            "Has consumido tus 3 búsquedas gratuitas de hoy.\n"
            "Actualiza tu cuenta a uno de nuestros planes premium para continuar:"
        )
    elif motivo == "limite_starter":
        text = (
            "🔒 <b>Límite Mensual de Starter Alcanzado</b>\n\n"
            "Has consumido tus 50 búsquedas mensuales contratadas.\n"
            "Puedes subir a un plan superior para continuar sin límites:"
        )
    elif motivo == "limite_teams":
        text = (
            "🔒 <b>Límite de Equipo Alcanzado</b>\n\n"
            "Tu plan de equipo no está activo o ha sido suspendido.\n"
            "Por favor, contacta a tu administrador o renueva la suscripción:"
        )
    else:
        text = (
            "🔒 <b>Función Premium Requerida</b>\n\n"
            "Por favor, suscríbete a un plan de pago para poder utilizar esta función:"
        )
        
    await msg.answer(text, reply_markup=get_paywall_markup())
