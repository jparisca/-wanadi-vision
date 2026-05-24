import pytest
import os
import json
import time
import shutil
from search.index_manager import IndexManager
from search.analytics_worker import AnalyticsWorker

def test_ct01_corrupted_snapshot_triggers_rebuild(tmp_path, monkeypatch):
    # Definir rutas temporales
    tmp_index = tmp_path / "nexus_faiss.index"
    tmp_map = tmp_path / "nexus_mappings.json"
    
    # Copiar snapshots actuales para tener una base válida
    if os.path.exists("nexus_faiss.index"):
        shutil.copy("nexus_faiss.index", tmp_index)
    if os.path.exists("nexus_mappings.json"):
        shutil.copy("nexus_mappings.json", tmp_map)
        
    # Monkeypatch de rutas globales en el módulo de index_manager
    monkeypatch.setattr("search.index_manager.INDEX_PATH", str(tmp_index))
    monkeypatch.setattr("search.index_manager.MAPPINGS_PATH", str(tmp_map))
    
    # Asegurar que tmp_map exista
    if not os.path.exists(tmp_map):
        with open(tmp_map, "w") as f:
            json.dump([{"hash_id": "test"}], f)
    
    # 1. Simular corrupción de FAISS escribiendo datos inválidos
    with open(tmp_index, "wb") as f:
        f.write(b"broken index data")
        
    # Resetear el singleton para forzar una inicialización limpia
    IndexManager._instance = None
    manager = IndexManager()
    
    # 2. Verificar que se disparó la recuperación de errores y rebuild total
    assert manager.snapshot_load_failures >= 1
    assert manager.index_rebuild_total >= 1
    assert manager.index is not None
    assert manager.index.ntotal == len(manager.mappings)


def test_ct02_metadata_drift_triggers_rebuild(tmp_path, monkeypatch):
    # Definir rutas temporales
    tmp_index = tmp_path / "nexus_faiss.index"
    tmp_map = tmp_path / "nexus_mappings.json"
    
    if os.path.exists("nexus_faiss.index"):
        shutil.copy("nexus_faiss.index", tmp_index)
    if os.path.exists("nexus_mappings.json"):
        shutil.copy("nexus_mappings.json", tmp_map)
        
    monkeypatch.setattr("search.index_manager.INDEX_PATH", str(tmp_index))
    monkeypatch.setattr("search.index_manager.MAPPINGS_PATH", str(tmp_map))
    
    # Asegurar que ambos existan para que load_snapshot no falle rápido
    if not os.path.exists(tmp_index):
        import faiss
        idx = faiss.IndexHNSWFlat(384, 32)
        faiss.write_index(idx, str(tmp_index))
        
    if not os.path.exists(tmp_map):
        with open(tmp_map, "w") as f:
            json.dump([{"hash_id": "test"}], f)
            
    # 1. Simular drift eliminando una entrada del mapeo JSON
    with open(tmp_map, "r") as f:
        mappings = json.load(f)
        
    if mappings:
        mappings.pop()
        
    with open(tmp_map, "w") as f:
        json.dump(mappings, f)
        
    # Resetear el singleton para forzar una inicialización limpia
    IndexManager._instance = None
    manager = IndexManager()
    
    # 2. Verificar rebuild por desincronización de dimensiones
    assert manager.snapshot_load_failures >= 1
    assert manager.index_rebuild_total >= 1
    assert manager.index is not None
    assert manager.index.ntotal == len(manager.mappings)


def test_ct03_queue_backpressure():
    # Reiniciar Singleton para prueba aislada
    AnalyticsWorker._instance = None
    worker = AnalyticsWorker()
    
    # Llenar la cola (maxsize=10000) rápidamente con 25,000 eventos
    for i in range(25000):
        worker.log_event(
            query=f"query_{i}",
            latency=50.0,
            cache_hit=1,
            top_result_hash="hash"
        )
        
    stats = worker.stats()
    
    # 1. Verificar descartes
    assert stats["dropped_events"] > 0
    assert stats["queue_fill_ratio"] <= 1.0
    assert stats["drop_rate"] > 0.0
