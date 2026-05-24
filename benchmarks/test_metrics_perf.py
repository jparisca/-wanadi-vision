import time
import pytest
from fastapi.testclient import TestClient
from api.app import app

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

def test_metrics_p95_latency(client):
    """
    Benchmark /metrics endpoint response time (< 25ms).
    """
    latencies = []
    
    # Warmup
    for _ in range(5):
        client.get("/api/v1/metrics")
        
    for _ in range(20):
        start = time.perf_counter()
        response = client.get("/api/v1/metrics")
        latency = (time.perf_counter() - start) * 1000
        latencies.append(latency)
        assert response.status_code == 200
        
    latencies.sort()
    p95_idx = int(len(latencies) * 0.95)
    p95_latency = latencies[p95_idx]
    
    assert p95_latency < 25.0, f"Metrics latency is {p95_latency:.2f}ms (Budget: <25ms)"
