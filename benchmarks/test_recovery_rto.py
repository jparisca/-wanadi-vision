import time
from search.index_manager import IndexManager

def test_recovery_rto_budget():
    """
    Validate that IndexManager recovery time objective (RTO) is under 60 seconds.
    """
    manager = IndexManager()
    
    start = time.perf_counter()
    # Ejecutamos carga o reconstrucción del snapshot para simular recuperación
    success = manager.load_snapshot()
    elapsed = time.perf_counter() - start
    
    assert success is True, "Fallo al cargar el snapshot durante RTO"
    assert elapsed < 60.0, f"RTO de recuperación excedido: {elapsed:.2f}s (Presupuesto: <60s)"
