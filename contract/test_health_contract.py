def test_liveness_probe(client):
    response = client.get("/api/v1/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "alive"}

def test_readiness_probe(client):
    response = client.get("/api/v1/health/ready")
    
    # We accept 200 or 503 depending on the state of the index
    assert response.status_code in [200, 503]
    
    data = response.json()
    assert "ready" in data
    assert "index_loaded" in data
    assert "db_ok" in data
    assert "embedding_model_loaded" in data
    
    if response.status_code == 200:
        assert data["ready"] is True
    else:
        assert data["ready"] is False
