"""
Scheduler Autónomo del Pipeline de Ingestión.

Ejecuta el ciclo ETL completo (Minar → Refinar → Guardar → Vectorizar → Indexar)
de forma automática cada N horas, sin necesidad de intervención humana.

Uso:
    # Correr manualmente una sola vez:
    python miners/scheduler.py --once

    # Correr como daemon (cada 12 horas):
    python miners/scheduler.py

    # Configurar como servicio systemd o nohup:
    nohup python miners/scheduler.py > logs/miner.log 2>&1 &
"""
import sys
import os
import time
import signal
import asyncio
import argparse
import logging
from datetime import datetime, timezone
from pathlib import Path

# Configurar path base del proyecto
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from miners.extractors.reddit_miner   import RedditMiner
from miners.extractors.threads_miner  import ThreadsMiner
from miners.extractors.twitter_miner  import TwitterMiner
from miners.extractors.civitai_miner  import CivitaiMiner
from miners.pipeline.ingestion_engine import IngestionEngine

# ─── Logging configuración ────────────────────────────────────────────────────
LOG_DIR = Path(BASE_DIR) / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_DIR / "miner_scheduler.log", encoding="utf-8"),
    ],
)
log = logging.getLogger("NexusScheduler")

# ─── Config ───────────────────────────────────────────────────────────────────
DEFAULT_INTERVAL_HOURS = 12
PROMPTS_PER_SOURCE     = 30   # límite por fuente por ciclo (conservador para disco)

# ─── Señales de apagado limpio ────────────────────────────────────────────────
_shutdown = False

def _handle_signal(signum, frame):
    global _shutdown
    log.info(f"⛔  Señal {signum} recibida. Deteniendo scheduler tras el ciclo actual...")
    _shutdown = True

signal.signal(signal.SIGINT,  _handle_signal)
signal.signal(signal.SIGTERM, _handle_signal)

# ─── Lógica principal ─────────────────────────────────────────────────────────

def build_engine() -> IngestionEngine:
    """Construye el motor de ingestión con todos los mineros activos."""
    return IngestionEngine(
        miners=[
            RedditMiner(),
            CivitaiMiner(),   # Mejor fuente de SD/Flux (API pública real)
            TwitterMiner(),   # Via Nitter (sin API key)
            ThreadsMiner(),   # Mock/Apify
        ]
    )


async def run_cycle(engine: IngestionEngine):
    """Ejecuta un ciclo completo del pipeline ETL."""
    start = datetime.now(timezone.utc)
    log.info("=" * 60)
    log.info("🚀 Iniciando Ciclo de Ingestión")
    log.info(f"   Timestamp: {start.isoformat()}")
    log.info(f"   Fuentes activas: {len(engine.miners)}")
    log.info("=" * 60)

    try:
        await engine.ingest_all(limit_per_source=PROMPTS_PER_SOURCE)
        elapsed = (datetime.now(timezone.utc) - start).total_seconds()
        log.info(f"✅ Ciclo completado en {elapsed:.1f}s")
    except Exception as e:
        log.error(f"❌ Error en ciclo de ingestión: {e}", exc_info=True)


def main():
    parser = argparse.ArgumentParser(description="Nexus Prompt Miner Scheduler")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Ejecutar un solo ciclo y salir (útil para cron)"
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=DEFAULT_INTERVAL_HOURS,
        help=f"Intervalo en horas entre ciclos (default: {DEFAULT_INTERVAL_HOURS})"
    )
    args = parser.parse_args()

    engine = build_engine()

    if args.once:
        log.info("🔂 Modo ONE-SHOT activado.")
        asyncio.run(run_cycle(engine))
        return

    interval_secs = args.interval * 3600
    log.info(f"⏰ Scheduler iniciado. Ciclos cada {args.interval}h.")
    log.info("   Presiona Ctrl+C para detener limpiamente.\n")

    while not _shutdown:
        asyncio.run(run_cycle(engine))

        if _shutdown:
            break

        next_run = datetime.now(timezone.utc).timestamp() + interval_secs
        log.info(f"💤 Próximo ciclo en {args.interval}h "
                 f"({datetime.fromtimestamp(next_run).strftime('%Y-%m-%d %H:%M:%S')} UTC)")

        # Esperar en trozos de 60s para responder rápido a señales
        waited = 0.0
        while waited < interval_secs and not _shutdown:
            time.sleep(min(60, interval_secs - waited))
            waited += 60

    log.info("🛑 Scheduler detenido limpiamente.")


if __name__ == "__main__":
    main()
