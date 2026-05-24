"""
bot/handlers/categories.py — Wanadi Vision: Manejador de navegación por categorías.
"""
from aiogram import Router, F
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from bot.config import CATEGORIAS, FRASE_SELFIE, CONSEJOS_SELFIE, NEXUS_API_URL
from bot.db import BotDB
from bot.search_client import NexusSearchClient

router = Router()
db = BotDB()

class CategoriesStates(StatesGroup):
    SELECCIONANDO_CATEGORIA = State()
    SELECCIONANDO_SUBCATEGORIA = State()
    PREGUNTANDO_SELFIE = State()
    MOSTRANDO_RESULTADOS = State()


# ─── Keyboards ────────────────────────────────────────────────────────────────

def get_categories_markup() -> InlineKeyboardMarkup:
    buttons = []
    # Grid de 15 categorías: 5 filas x 3 columnas
    for i in range(0, len(CATEGORIAS), 3):
        row = []
        for cat in CATEGORIAS[i:i+3]:
            # Recortar si el nombre es demasiado largo
            name = cat["nombre"]
            if len(name) > 15:
                name = name[:13] + ".."
            row.append(InlineKeyboardButton(
                text=f"{cat['emoji']} {name}",
                callback_data=f"cat_{cat['id']}"
            ))
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="🔙 Volver al menú", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_subcategories_markup(categoria_id: int) -> InlineKeyboardMarkup:
    cat = next((c for c in CATEGORIAS if c["id"] == categoria_id), None)
    if not cat:
        return InlineKeyboardMarkup(inline_keyboard=[])
    
    buttons = []
    subcats = cat["subcategorias"]
    # Grid de subcategorías (2 columnas por fila)
    for i in range(0, len(subcats), 2):
        row = []
        for sub in subcats[i:i+2]:
            display_name = sub.replace("_", " ").title()
            row.append(InlineKeyboardButton(
                text=display_name,
                callback_data=f"sub_{sub}"
            ))
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="🔙 Volver a categorías", callback_data="volver_cats")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_selfie_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Sí, usar mi rostro", callback_data="selfie_yes"),
            InlineKeyboardButton(text="❌ No, prompt normal", callback_data="selfie_no")
        ],
        [InlineKeyboardButton(text="🔙 Volver a categorías", callback_data="volver_cats")]
    ])


def get_results_markup(page_results: list, page: int, total_results: int, voted_hashes: list = None) -> InlineKeyboardMarkup:
    if voted_hashes is None:
        voted_hashes = []
        
    buttons = []
    
    # Fila de botones 👍 Útil por prompt
    vote_row = []
    for idx, r in enumerate(page_results, 1):
        hash_id = r.get("hash_id", "")
        if hash_id in voted_hashes:
            vote_row.append(InlineKeyboardButton(
                text=f"✅ #{idx}",
                callback_data="voted_already"
            ))
        else:
            vote_row.append(InlineKeyboardButton(
                text=f"👍 #{idx}",
                callback_data=f"util_{hash_id}"
            ))
    buttons.append(vote_row)
    
    # Fila de navegación
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="⏪ Anterior", callback_data="page_prev"))
    if (page + 1) * 5 < total_results:
        nav_row.append(InlineKeyboardButton(text="Siguiente ⏩", callback_data="page_next"))
    if nav_row:
        buttons.append(nav_row)
        
    # Fila de acciones generales
    buttons.append([
        InlineKeyboardButton(text="🗂️ Categorías", callback_data="volver_cats"),
        InlineKeyboardButton(text="🔍 Nueva búsqueda", callback_data="nueva_busqueda")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ─── Handlers ─────────────────────────────────────────────────────────────────

@router.message(Command("categorias"))
async def cmd_categorias(msg: Message, state: FSMContext):
    await state.clear()
    await state.set_state(CategoriesStates.SELECCIONANDO_CATEGORIA)
    await msg.answer(
        "🗂️ <b>Explorar por Categorías</b>\n\n"
        "Selecciona una categoría de la siguiente lista para ver subcategorías y prompts optimizados:",
        reply_markup=get_categories_markup()
    )

@router.callback_query(F.data == "abrir_categorias")
async def cb_abrir_categorias(cq: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(CategoriesStates.SELECCIONANDO_CATEGORIA)
    await cq.message.edit_text(
        "🗂️ <b>Explorar por Categorías</b>\n\n"
        "Selecciona una categoría de la siguiente lista para ver subcategorías y prompts optimizados:",
        reply_markup=get_categories_markup()
    )
    await cq.answer()

@router.callback_query(CategoriesStates.SELECCIONANDO_CATEGORIA, F.data.startswith("cat_"))
async def cb_categoria_elegida(cq: CallbackQuery, state: FSMContext):
    cat_id = int(cq.data.split("_")[1])
    cat = next((c for c in CATEGORIAS if c["id"] == cat_id), None)
    if not cat:
        await cq.answer("Categoría no encontrada.")
        return
        
    await state.update_data(categoria_id=cat_id, categoria_slug=cat["slug"])
    await state.set_state(CategoriesStates.SELECCIONANDO_SUBCATEGORIA)
    
    await cq.message.edit_text(
        f"{cat['emoji']} <b>Categoría: {cat['nombre']}</b>\n\n"
        "Selecciona una subcategoría para filtrar los prompts:",
        reply_markup=get_subcategories_markup(cat_id)
    )
    await cq.answer()

@router.callback_query(CategoriesStates.SELECCIONANDO_SUBCATEGORIA, F.data.startswith("sub_"))
async def cb_subcategoria_elegida(cq: CallbackQuery, state: FSMContext):
    sub_slug = cq.data.split("_")[1]
    await state.update_data(subcategoria_slug=sub_slug)
    await state.set_state(CategoriesStates.PREGUNTANDO_SELFIE)
    
    await cq.message.edit_text(
        "👤 <b>Fidelidad Facial (Selfie Mode)</b>\n\n"
        "¿Quieres añadir la instrucción de fidelidad facial a estos prompts para usarlos con tu rostro?",
        reply_markup=get_selfie_markup()
    )
    await cq.answer()

@router.callback_query(CategoriesStates.PREGUNTANDO_SELFIE, F.data.in_(["selfie_yes", "selfie_no"]))
async def cb_selfie_respuesta(cq: CallbackQuery, state: FSMContext):
    selfie_mode = (cq.data == "selfie_yes")
    await state.update_data(selfie=selfie_mode, page=0, voted_hashes=[])
    
    data = await state.get_data()
    cat_id = data["categoria_id"]
    sub_slug = data["subcategoria_slug"]
    
    # Mensaje temporal
    await cq.message.edit_text("⏳ Obteniendo prompts de la base de datos...")
    
    try:
        client = NexusSearchClient(base_url=NEXUS_API_URL)
        results = await client.get_prompts_by_category(categoria_id=cat_id, subcategoria_id=sub_slug, top_k=50)
        
        if not results:
            await cq.message.edit_text(
                "😕 No encontramos prompts clasificados en esta subcategoría todavía.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Volver a categorías", callback_data="volver_cats")]
                ])
            )
            await cq.answer()
            return
            
        await state.update_data(results_cache=results)
        await state.set_state(CategoriesStates.MOSTRANDO_RESULTADOS)
        await show_results_page(cq.message, state)
        
    except Exception as e:
        await cq.message.edit_text(
            f"❌ Error conectando con el servidor de búsqueda: {e}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Volver", callback_data="volver_cats")]
            ])
        )
    await cq.answer()

async def show_results_page(message: Message, state: FSMContext):
    data = await state.get_data()
    results = data.get("results_cache", [])
    page = data.get("page", 0)
    selfie = data.get("selfie", False)
    voted_hashes = data.get("voted_hashes", [])
    sub_slug = data.get("subcategoria_slug", "general").replace("_", " ").title()
    
    start_idx = page * 5
    end_idx = start_idx + 5
    page_results = results[start_idx:end_idx]
    
    header = (
        f"🎯 <b>Prompts para: {sub_slug}</b> (Pág. {page+1}/{((len(results)-1)//5)+1})\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
    )
    
    response_lines = [header]
    for idx, r in enumerate(page_results, 1):
        prompt_text = r["prompt_text"]
        
        # Si tiene selfie mode activo, añadir frase al inicio
        if selfie:
            prompt_text = FRASE_SELFIE + prompt_text
            
        # Truncar el texto del prompt si es muy largo
        display_text = prompt_text[:400] + "..." if len(prompt_text) > 400 else prompt_text
        
        response_lines.append(
            f"<b>#{idx}</b> · {r['engine']} · ⭐{r['score']:.2f}\n"
            f"<code>{display_text}</code>\n"
            f"📌 Fuente: {r['source']}\n"
        )
        
    # Añadir consejos al final de la primera página
    if page == 0 and selfie:
        response_lines.append(f"\n{CONSEJOS_SELFIE}")
        
    text = "\n".join(response_lines)
    
    # Enviar o editar mensaje
    markup = get_results_markup(page_results, page, len(results), voted_hashes)
    try:
        await message.edit_text(text, reply_markup=markup)
    except Exception:
        # En caso de que falle editar por longitud o contenido idéntico
        await message.answer(text, reply_markup=markup)

@router.callback_query(CategoriesStates.MOSTRANDO_RESULTADOS, F.data == "page_next")
async def cb_siguiente_pagina(cq: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    page = data.get("page", 0)
    results = data.get("results_cache", [])
    
    if (page + 1) * 5 < len(results):
        await state.update_data(page=page + 1)
        await show_results_page(cq.message, state)
        
    await cq.answer()

@router.callback_query(CategoriesStates.MOSTRANDO_RESULTADOS, F.data == "page_prev")
async def cb_anterior_pagina(cq: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    page = data.get("page", 0)
    
    if page > 0:
        await state.update_data(page=page - 1)
        await show_results_page(cq.message, state)
        
    await cq.answer()

@router.callback_query(CategoriesStates.MOSTRANDO_RESULTADOS, F.data.startswith("util_"))
async def cb_util_prompt(cq: CallbackQuery, state: FSMContext):
    hash_id = cq.data.split("_")[1]
    
    data = await state.get_data()
    voted_hashes = data.get("voted_hashes", [])
    
    if hash_id in voted_hashes:
        await cq.answer("Ya has votado por este prompt.", show_alert=True)
        return
        
    try:
        client = NexusSearchClient(base_url=NEXUS_API_URL)
        await client.vote_prompt(hash_id)
        
        # Registrar en la lista de votados del estado
        voted_hashes.append(hash_id)
        await state.update_data(voted_hashes=voted_hashes)
        
        # Actualizar la página para reflejar el cambio del botón
        await show_results_page(cq.message, state)
        await cq.answer("¡Voto útil registrado! +1 punto.", show_alert=True)
        
    except Exception as e:
        await cq.answer(f"Error al registrar voto: {e}", show_alert=True)

@router.callback_query(F.data == "voted_already")
async def cb_voted_already(cq: CallbackQuery):
    await cq.answer("Ya has votado por este prompt.", show_alert=True)

@router.callback_query(F.data == "volver_cats")
async def cb_volver_categorias(cq: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(CategoriesStates.SELECCIONANDO_CATEGORIA)
    await cq.message.edit_text(
        "🗂️ <b>Explorar por Categorías</b>\n\n"
        "Selecciona una categoría de la siguiente lista para ver subcategorías y prompts optimizados:",
        reply_markup=get_categories_markup()
    )
    await cq.answer()

@router.callback_query(F.data == "nueva_busqueda")
async def cb_nueva_busqueda(cq: CallbackQuery, state: FSMContext):
    await state.clear()
    await cq.message.edit_text(
        "🔍 <b>¿Qué tipo de imagen quieres generar?</b>\n\n"
        "Escríbeme una descripción y te busco los mejores prompts:"
    )
    await cq.answer()
