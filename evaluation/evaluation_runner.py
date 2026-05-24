import sys
import os
import json
import time
import math
import numpy as np

# Ajuste de path para importaciones correctas
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from search.semantic_search import search_hybrid

GOLDEN_QUERIES_PATH = "evaluation/golden_queries.json"

def calculate_precision_at_k(retrieved_ids: list, expected_ids: list, k: int) -> float:
    top_k_retrieved = retrieved_ids[:k]
    relevant_retrieved = len(set(top_k_retrieved).intersection(set(expected_ids)))
    return relevant_retrieved / k if k > 0 else 0.0

def calculate_recall_at_k(retrieved_ids: list, expected_ids: list, k: int) -> float:
    top_k_retrieved = retrieved_ids[:k]
    relevant_retrieved = len(set(top_k_retrieved).intersection(set(expected_ids)))
    total_relevant = len(expected_ids)
    return relevant_retrieved / total_relevant if total_relevant > 0 else 0.0

def calculate_average_precision(retrieved_ids: list, expected_ids: list) -> float:
    """
    Calcula el Average Precision (AP) para una consulta de búsqueda (insumo para MAP).
    """
    if not expected_ids:
        return 0.0
        
    ap = 0.0
    relevant_count = 0
    
    for idx, item_id in enumerate(retrieved_ids, 1):
        if item_id in expected_ids:
            relevant_count += 1
            precision_at_rank = relevant_count / idx
            ap += precision_at_rank
            
    return ap / len(expected_ids) if len(expected_ids) > 0 else 0.0

def calculate_mrr(retrieved_ids: list, expected_ids: list) -> float:
    for idx, item_id in enumerate(retrieved_ids, 1):
        if item_id in expected_ids:
            return 1.0 / idx
    return 0.0

def calculate_dcg_at_k(retrieved_ids: list, expected_ids: list, k: int) -> float:
    dcg = 0.0
    for idx, item_id in enumerate(retrieved_ids[:k], 1):
        if item_id in expected_ids:
            relevance = 1.0
            dcg += relevance / math.log2(idx + 1)
    return dcg

def calculate_ndcg_at_k(retrieved_ids: list, expected_ids: list, k: int) -> float:
    dcg = calculate_dcg_at_k(retrieved_ids, expected_ids, k)
    
    # Calcular IDCG (Ideal DCG)
    ideal_retrieved = [item for item in expected_ids if item in expected_ids]
    idcg = calculate_dcg_at_k(ideal_retrieved, expected_ids, k)
    
    return dcg / idcg if idcg > 0.0 else 0.0

def calculate_hit_rate(retrieved_ids: list, expected_ids: list, k: int) -> float:
    """
    Retorna 1.0 si al menos un elemento esperado se encuentra en el Top-K devuelto, de lo contrario 0.0.
    """
    top_k_retrieved = retrieved_ids[:k]
    intersection = set(top_k_retrieved).intersection(set(expected_ids))
    return 1.0 if len(intersection) >= 1 else 0.0

def calculate_success_at_1(retrieved_ids: list, expected_ids: list) -> float:
    """
    Retorna 1.0 si el primer resultado devuelto coincide con un ID esperado, de lo contrario 0.0.
    """
    if retrieved_ids and retrieved_ids[0] in expected_ids:
        return 1.0
    return 0.0

def run_evaluation():
    print("\n" + "="*75)
    print("🌌 RETRIEVAL EVALUATION RUNNER v2 — PROMPT NEXUS ENGINE")
    print("="*75)
    
    if not os.path.exists(GOLDEN_QUERIES_PATH):
        print(f"❌ Archivo de queries de oro no encontrado en '{GOLDEN_QUERIES_PATH}'")
        return
        
    with open(GOLDEN_QUERIES_PATH, "r") as f:
        golden_queries = json.load(f)
        
    print(f"📋 Cargadas {len(golden_queries)} Golden Queries de producción.")
    print("🚀 Evaluando métricas avanzadas (MAP, Recall@50, Success@1, HitRate)...")
    print("─"*75)
    
    precisions_5 = []
    recalls_10 = []
    recalls_50 = []
    mrrs = []
    ndcgs_5 = []
    aps = []
    hit_rates_10 = []
    success_1s = []
    latencies = []
    
    # Calentamiento del caché para eliminar el sesgo de cold startup en métricas
    search_hybrid("warmup query", top_k=5)
    
    for q_entry in golden_queries:
        query = q_entry["query"]
        expected = q_entry["expected_ids"]
        
        # Consultamos Top 50 para poder calcular Recall@50
        start_time = time.perf_counter()
        results = search_hybrid(query, top_k=50)
        end_time = time.perf_counter()
        
        latency_ms = (end_time - start_time) * 1000
        latencies.append(latency_ms)
        
        # Extraer IDs únicos de prompts devueltos preservando el orden de relevancia
        retrieved_ids = []
        for res in results:
            pid = res["prompt_id"]
            if pid not in retrieved_ids:
                retrieved_ids.append(pid)

        
        # Computar métricas avanzadas por query
        p5 = calculate_precision_at_k(retrieved_ids, expected, k=5)
        r10 = calculate_recall_at_k(retrieved_ids, expected, k=10)
        r50 = calculate_recall_at_k(retrieved_ids, expected, k=50)
        ap = calculate_average_precision(retrieved_ids, expected)
        mrr = calculate_mrr(retrieved_ids, expected)
        ndcg5 = calculate_ndcg_at_k(retrieved_ids, expected, k=5)
        hr10 = calculate_hit_rate(retrieved_ids, expected, k=10)
        succ1 = calculate_success_at_1(retrieved_ids, expected)
        
        precisions_5.append(p5)
        recalls_10.append(r10)
        recalls_50.append(r50)
        aps.append(ap)
        mrrs.append(mrr)
        ndcgs_5.append(ndcg5)
        hit_rates_10.append(hr10)
        success_1s.append(succ1)
        
        print(f"🔍 QUERY: \"{query}\"")
        print(f"   ⏱️  Latencia: {latency_ms:.2f} ms")
        print(f"   🎯 Precision@5: {p5*100:.1f}% | Recall@10: {r10*100:.1f}% | Recall@50: {r50*100:.1f}%")
        print(f"   📈 MAP: {ap:.3f} | MRR: {mrr:.3f} | nDCG@5: {ndcg5:.3f}")
        print(f"   🏆 Success@1: {succ1*100:.1f}% | HitRate@10: {hr10*100:.1f}%")
        print("─"*75)
        
    # Calcular consolidados agregados
    avg_p5 = np.mean(precisions_5)
    avg_r10 = np.mean(recalls_10)
    avg_r50 = np.mean(recalls_50)
    avg_map = np.mean(aps)
    avg_mrr = np.mean(mrrs)
    avg_ndcg5 = np.mean(ndcgs_5)
    avg_hr10 = np.mean(hit_rates_10)
    avg_succ1 = np.mean(success_1s)
    
    latencies = np.array(latencies)
    p50_latency = np.percentile(latencies, 50)
    p95_latency = np.percentile(latencies, 95)
    
    print("\n" + "="*75)
    print("📊 RESULTADOS CONSOLIDADOS DE EVALUACIÓN MULTI-MÉTRICA")
    print("="*75)
    print(f"🎯 Avg Precision@5:  {avg_p5 * 100:.2f}%  (Target: >80.0%)")
    print(f"📈 Avg Recall@10:    {avg_r10 * 100:.2f}%  (Target: >85.0%)")
    print(f"🔥 Avg Recall@50:    {avg_r50 * 100:.2f}%  (Target: >95.0%)")
    print(f"🧠 Mean MAP:          {avg_map:.4f}      (Métrica Principal Calidad)")
    print(f"💎 Mean MRR:          {avg_mrr:.4f}      (Target: >0.80)")
    print(f"🚀 Mean nDCG@5:       {avg_ndcg5:.4f}      (Target: >0.85)")
    print(f"🏆 Success@1:         {avg_succ1 * 100:.2f}%  (Top-1 Relevance)")
    print(f"⚡ HitRate@10:        {avg_hr10 * 100:.2f}%  (Recall de Coincidencia)")
    print(f"⏱️  Latencia Mediana:  {p50_latency:.2f} ms")
    print(f"⏱️  Latencia P95:      {p95_latency:.2f} ms   (Target: <200ms)")
    print("="*75 + "\n")
 
if __name__ == "__main__":
    run_evaluation()
