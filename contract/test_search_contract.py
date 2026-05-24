def test_search_valid_200(client):
    response = client.get("/api/v1/search?q=cyberpunk&variant=B&top_k=3")
    assert response.status_code == 200
    data = response.json()
    assert "query" in data
    assert data["query"] == "cyberpunk"
    assert "results" in data
    assert isinstance(data["results"], list)

def test_search_variant_a(client):
    response = client.get("/api/v1/search?q=test&variant=A")
    assert response.status_code == 200

def test_search_invalid_engine(client):
    response = client.get("/api/v1/search?q=test&engine=invalid_engine_name")
    assert response.status_code == 200

def test_search_empty_q_422(client):
    response = client.get("/api/v1/search?q=")
    assert response.status_code == 422

def test_search_top_k_exceeded_422(client):
    response = client.get("/api/v1/search?q=test&top_k=100")
    assert response.status_code == 422
