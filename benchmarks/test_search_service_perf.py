import time
import pytest
from search.semantic_search import search_hybrid

def test_search_service_p95_latency():
    """
    Benchmark core SearchService.execute_search (search_hybrid) latency (p95 < 80ms).
    """
    latencies = []
    
    # Warmup
    for _ in range(5):
        search_hybrid("warmup query", variant="B")
        
    for i in range(30):
        start = time.perf_counter()
        results = search_hybrid(f"cyberpunk city cyborg hybrid search testing {i}", variant="B")
        latency = (time.perf_counter() - start) * 1000
        latencies.append(latency)
        
    latencies.sort()
    p95_idx = int(len(latencies) * 0.95)
    p95_latency = latencies[p95_idx]
    
    assert p95_latency < 80.0, f"Search service core P95 latency is {p95_latency:.2f}ms (Budget: <80ms)"
