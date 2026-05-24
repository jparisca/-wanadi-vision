import sys
import os
import time
import numpy as np

# Ajuste de path para importaciones correctas
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from search.semantic_search import search_hybrid
from search.model_registry import get_model

MODEL_NAME = "all-MiniLM-L6-v2"
DB_PATH = "nexus_prompts.db"

def get_process_memory_mb() -> float:
    try:
        import psutil
        return psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024)
    except ImportError:
        try:
            with open("/proc/self/status") as f:
                for line in f:
                    if line.startswith("VmRSS:"):
                        return float(line.split()[1]) / 1024.0
        except IOError:
            return 0.0

def run_benchmark():
    print("\n" + "="*75)
    print("🌌 BENCHMARK SUITE v2 — RETRIEVAL ENGINE PROMPT NEXUS")
    print("="*75)

    # 1. Tamaño de la base de datos
    db_size = os.path.getsize(DB_PATH) if os.path.exists(DB_PATH) else 0
    print(f"📊 DB (SQLite):         {db_size / 1024:.2f} KB")

    # 2. Memoria base del proceso
    mem_base = get_process_memory_mb()

    # 3. Indexación vectorial (velocidad de embed + normalización L2)
    print("⚡ Midiendo velocidad de indexación...")
    model = get_model(MODEL_NAME)
    samples = [f"A futuristic render of a holographic city room version {i}" for i in range(10)]
    t0 = time.perf_counter()
    embeddings = model.encode(samples)
    for emb in embeddings:
        norm = np.linalg.norm(emb)
        if norm > 0:
            _ = emb / norm
    index_time = time.perf_counter() - t0
    print(f"   Tiempo total (10 prompts): {index_time:.4f} s")
    print(f"   Promedio por prompt:       {index_time / len(samples) * 1000:.2f} ms")

    # 4. Cold vs Warm latency
    print("\n⚡ Cold vs Warm Query Latency...")
    COLD_QUERY = "cinematic rainy cyberpunk cold benchmark"
    WARM_QUERY = "cinematic rainy cyberpunk"

    # Cold: primera vez que se codifica esa query
    t0 = time.perf_counter()
    search_hybrid(COLD_QUERY, top_k=5)
    cold_ms = (time.perf_counter() - t0) * 1000

    # Calentar la query WARM_QUERY antes de medirla
    search_hybrid(WARM_QUERY, top_k=5)

    # Warm x10: misma query, LRU cache activa
    warm_latencies = []
    for _ in range(10):
        t0 = time.perf_counter()
        search_hybrid(WARM_QUERY, top_k=5)
        warm_latencies.append((time.perf_counter() - t0) * 1000)
    warm_arr = np.array(warm_latencies)


    print(f"   🔴 Cold Query (CPU inference): {cold_ms:.2f} ms")
    print(f"   🟢 Warm P50  (LRU cache hit):  {np.percentile(warm_arr, 50):.2f} ms")
    print(f"   🟡 Warm P95  (LRU cache hit):  {np.percentile(warm_arr, 95):.2f} ms")
    print(f"   ⚡ Speedup:                    {cold_ms / np.percentile(warm_arr, 50):.0f}×")

    # 5. Recall de calidad
    print("\n⚡ Recall semántico (dataset cyberpunk)...")
    recall_results = search_hybrid("cyberpunk", top_k=5)
    hits = len([r for r in recall_results if "cyberpunk" in r["prompt_text"].lower()])
    total = 3
    print(f"   Recall@3: {hits}/{total} prompts ({hits/total*100:.1f}%)")

    # 6. Memoria tras carga del modelo
    mem_after = get_process_memory_mb()
    print(f"\n🧠 Memoria antes del modelo: {mem_base:.2f} MB")
    print(f"🧠 Memoria tras el modelo:   {mem_after:.2f} MB")
    print(f"🧠 Delta (overhead modelo):  {mem_after - mem_base:.2f} MB")

    print("="*75 + "\n")

if __name__ == "__main__":
    run_benchmark()
