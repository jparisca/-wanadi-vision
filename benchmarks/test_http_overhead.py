import time
import pytest
from fastapi.testclient import TestClient
from api.app import app

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

def test_http_search_p95_latency(client):
    """
    Benchmark HTTP endpoint /search overhead (p95 < 120ms).
    """
    latencies = []
    
    # Warmup
    for _ in range(5):
        client.get("/api/v1/search?q=warmup&variant=B")
        
    for i in range(30):
        start = time.perf_counter()
        response = client.get(f"/api/v1/search?q=cyberpunk+neon+punk+testing+http+{i}&variant=B")
        latency = (time.perf_counter() - start) * 1000
        latencies.append(latency)
        assert response.status_code == 200
        
    latencies.sort()
    p95_idx = int(len(latencies) * 0.95)
    p95_latency = latencies[p95_idx]
    
    assert p95_latency < 120.0, f"HTTP search P95 latency is {p95_latency:.2f}ms (Budget: <120ms)"
