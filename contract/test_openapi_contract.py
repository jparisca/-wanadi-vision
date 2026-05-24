import json
import os
import pytest

SNAPSHOT_PATH = os.path.join(os.path.dirname(__file__), "schemas", "snapshots", "openapi_snapshot.json")

def test_openapi_schema_unchanged(client):
    response = client.get("/openapi.json")
    assert response.status_code == 200
    current_schema = response.json()
    
    if not os.path.exists(SNAPSHOT_PATH):
        pytest.skip(f"Snapshot no encontrado en {SNAPSHOT_PATH}. Ejecuta el snapshot primero.")
        
    with open(SNAPSHOT_PATH, "r") as f:
        snapshot = json.load(f)
        
    # Validar que no haya derive (drift) entre el contrato anterior y el actual
    # Esto asegura que ningún cambio en Pydantic o FastAPI rompa a los clientes frontend.
    assert current_schema.get("paths") == snapshot.get("paths"), "El contrato OpenAPI (rutas) ha cambiado."
    assert current_schema.get("components") == snapshot.get("components"), "El contrato OpenAPI (esquemas de datos) ha cambiado."
