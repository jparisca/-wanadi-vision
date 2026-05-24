"""
bot/config.py — Wanadi Vision: Configuración centralizada de planes, precios y categorías.
"""
from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

# ── Bot
BOT_TOKEN       = os.getenv("BOT_TOKEN", "")
ADMIN_CHAT_ID   = int(os.getenv("ADMIN_CHAT_ID", "0"))
BOT_USERNAME    = os.getenv("BOT_USERNAME", "wanadivision_bot")
NEXUS_API_URL   = os.getenv("NEXUS_API_URL", "http://127.0.0.1:8000/api/v1")

# ── Planes (búsquedas)
FREE_BUSQUEDAS_DIA     = int(os.getenv("FREE_BUSQUEDAS_DIA", "3"))
STARTER_BUSQUEDAS_MES  = int(os.getenv("STARTER_BUSQUEDAS_MES", "50"))
PRO_BUSQUEDAS          = -1   # ilimitado
TEAMS_USUARIOS_MAX     = int(os.getenv("TEAMS_USUARIOS_MAX", "5"))
TEAMS_API_RPD          = int(os.getenv("TEAMS_API_RPD", "500"))

# ── Precios Telegram Stars (1 Star ≈ $0.013 USD)
PRECIO_STARTER_STARS   = int(os.getenv("PRECIO_STARTER_STARS", "385"))   # ~$5
PRECIO_PRO_STARS       = int(os.getenv("PRECIO_PRO_STARS", "1154"))      # ~$15
PRECIO_TEAMS_STARS     = int(os.getenv("PRECIO_TEAMS_STARS", "3769"))    # ~$49/mes

# ── Categorías (id, slug, nombre, emoji, subcategorías)
CATEGORIAS = [
    {"id": 1,  "slug": "estilo_artistico", "nombre": "Estilos Artísticos",     "emoji": "🎨", "subcategorias": ["oleo","acuarela","pixel_art","anime","cyberpunk","realista","pop_art","manga","low_poly","vaporwave","steampunk","bauhaus","art_deco"]},
    {"id": 2,  "slug": "animacion_series", "nombre": "Animación / Series",     "emoji": "🎬", "subcategorias": ["pixar","disney","ghibli","simpsons","south_park","rick_morty","naruto","dragon_ball","marvel_comic","dc_batman","tim_burton","cartoon_network"]},
    {"id": 3,  "slug": "videojuegos",      "nombre": "Videojuegos",            "emoji": "🕹️","subcategorias": ["minecraft","zelda","pokemon","cuphead","fortnite","hollow_knight","borderlands","gta","red_dead","silent_hill","cyberpunk2077"]},
    {"id": 4,  "slug": "tematica",         "nombre": "Temática General",       "emoji": "🌍", "subcategorias": ["dragones","robots","paisajes","personajes","horror","animales","fantasia","ciencia_ficcion"]},
    {"id": 5,  "slug": "composicion",      "nombre": "Composición y Luz",      "emoji": "📐", "subcategorias": ["primer_plano","macro","aereo","luz_natural","luz_neon","cinematografico","bokeh","contraluz"]},
    {"id": 6,  "slug": "color",            "nombre": "Paleta de Colores",      "emoji": "🎨", "subcategorias": ["monocromatico","pastel","neon","calidos","frios","metalico","sepia"]},
    {"id": 7,  "slug": "marketing",        "nombre": "Marketing / Publicidad", "emoji": "📢", "subcategorias": ["producto_en_uso","lifestyle","banner_web","packshot","before_after","unboxing","minimalista"]},
    {"id": 8,  "slug": "comida",           "nombre": "Comida y Bebida",        "emoji": "🍔", "subcategorias": ["gourmet","postres","cafe","cocteles","food_photography","overhead","mesa_servida"]},
    {"id": 9,  "slug": "ecommerce",        "nombre": "Productos / E-commerce", "emoji": "📦", "subcategorias": ["fondo_blanco","en_uso","render_3d","catalogo","empaque"]},
    {"id": 10, "slug": "moda",             "nombre": "Moda y Belleza",         "emoji": "👗", "subcategorias": ["lookbook","editorial","pasarela","maquillaje","lujo"]},
    {"id": 11, "slug": "arquitectura",     "nombre": "Arquitectura",           "emoji": "🏛️","subcategorias": ["exteriores","interiores","minimalista","futurista","renders"]},
    {"id": 12, "slug": "naturaleza",       "nombre": "Naturaleza",             "emoji": "🌿", "subcategorias": ["atardeceres","bosques","oceanos","desiertos","espacio_exterior"]},
    {"id": 13, "slug": "ciencia_tec",      "nombre": "Ciencia y Tecnología",   "emoji": "🔬", "subcategorias": ["laboratorios","naves","redes_neuronales","ilustracion_cientifica"]},
    {"id": 14, "slug": "deportes",         "nombre": "Deportes y Acción",      "emoji": "⚽", "subcategorias": ["futbol","running","surf","extremos","movimiento_congelado"]},
    {"id": 15, "slug": "dificultad",       "nombre": "Dificultad Técnica",     "emoji": "🧠", "subcategorias": ["facil","medio","avanzado"]},
]

# ── Selfie mode
FRASE_SELFIE = (
    "Use the uploaded face as the exact facial reference. "
    "Apply the lighting, color grading, and mood to be identical "
    "to the reference image, avoiding any external lighting sources.\n\n"
)
CONSEJOS_SELFIE = (
    "💡 Cómo usar con tu selfie:\n"
    "• Midjourney: sube tu foto como referencia + añade --iw 2\n"
    "• DALL-E 3: opción 'subir imagen' + pega el prompt\n"
    "• Stable Diffusion: img2img + ControlNet reference, denoising ~0.7\n"
    "• Flux: sube imagen como referencia en la UI"
)
