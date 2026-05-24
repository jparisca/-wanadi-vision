import queue
import threading
import time
import json
import os
from collections import deque
import numpy as np
from database.db_utils import get_session
from database.schema import SearchEvent

class AnalyticsWorker:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if not cls._instance:
                cls._instance = super(AnalyticsWorker, cls).__new__(cls, *args, **kwargs)
                cls._instance._initialized = False
        return cls._instance
        
    def __init__(self):
        if self._initialized:
            return
        self.queue_maxsize = 10000
        self.queue = queue.Queue(maxsize=self.queue_maxsize)
        self.dropped_events = 0
        self.total_events_received = 0
        self.last_flush_latency = 0.0
        self.recent_latencies = deque(maxlen=100)
        self.recent_cache_hits = deque(maxlen=100)
        self.stats_lock = threading.Lock()
        self._load_snapshot()
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()
        self._initialized = True
        print("🚀 [AnalyticsWorker] Hilo persistente de telemetría por lotes iniciado.")
        
    def _load_snapshot(self):
        try:
            if os.path.exists("metrics_snapshot.json"):
                with open("metrics_snapshot.json", "r") as f:
                    data = json.load(f)
                    with self.stats_lock:
                        self.dropped_events = data.get("dropped_events", 0)
                        self.recent_latencies.extend(data.get("recent_latencies", []))
                        self.recent_cache_hits.extend(data.get("recent_cache_hits", []))
        except Exception as e:
            print(f"⚠️  [AnalyticsWorker] Error cargando snapshot de métricas: {e}")

    def _save_snapshot(self):
        try:
            with open("metrics_snapshot.json", "w") as f:
                with self.stats_lock:
                    data = {
                        "dropped_events": self.dropped_events,
                        "recent_latencies": list(self.recent_latencies),
                        "recent_cache_hits": list(self.recent_cache_hits)
                    }
                json.dump(data, f)
        except Exception as e:
            print(f"⚠️  [AnalyticsWorker] Error guardando snapshot de métricas: {e}")
        
    def log_event(self, query: str, latency: float, cache_hit: int, top_result_hash: str):
        """
        Encola un evento de búsqueda en la cola thread-safe de forma inmediata (no bloqueante).
        """
        with self.stats_lock:
            self.total_events_received += 1
            self.recent_latencies.append(latency)
            self.recent_cache_hits.append(cache_hit)
            
        try:
            self.queue.put_nowait({
                "query": query[:250],
                "latency": latency,
                "cache_hit": cache_hit,
                "top_result_hash": top_result_hash
            })
        except queue.Full:
            with self.stats_lock:
                self.dropped_events += 1
            print("⚠️  [AnalyticsWorker] Cola de telemetría llena. Evento omitido.")
            
    def stats(self) -> dict:
        """
        Retorna estadísticas de salud y carga de la cola analítica, junto con percentiles recientes.
        """
        with self.stats_lock:
            dropped = self.dropped_events
            total = self.total_events_received
            flush_latency = self.last_flush_latency
            latencies = list(self.recent_latencies)
            cache_hits = list(self.recent_cache_hits)
            
        drop_rate = (dropped / total) if total > 0 else 0.0
        q_depth = self.queue.qsize()
        queue_fill_ratio = (q_depth / self.queue_maxsize) if self.queue_maxsize > 0 else 0.0
        
        p50 = float(np.percentile(latencies, 50)) if latencies else 0.0
        p95 = float(np.percentile(latencies, 95)) if latencies else 0.0
        hit_rate = float(sum(cache_hits) / len(cache_hits)) if cache_hits else 0.0
        
        return {
            "queue_depth": q_depth,
            "queue_fill_ratio": queue_fill_ratio,
            "dropped_events": dropped,
            "drop_rate": drop_rate,
            "total_events": total,
            "worker_flush_latency_ms": flush_latency,
            "p50_latency_ms": p50,
            "p95_latency_ms": p95,
            "cache_hit_rate": hit_rate
        }

    def _worker_loop(self):
        """
        Loop continuo ejecutado en segundo plano por el hilo demonio.
        Agrupa eventos de búsqueda y realiza inserciones masivas en SQLite cada 50 registros o 1 segundo.
        """
        last_snapshot_time = time.time()
        while True:
            batch = []
            start_time = time.time()
            
            # Guardar snapshot de métricas operacionales cada 60 segundos
            if (time.time() - last_snapshot_time) > 60:
                self._save_snapshot()
                last_snapshot_time = time.time()
                
            # Recolectar elementos hasta llenar el lote o agotar el tiempo
            while len(batch) < 50 and (time.time() - start_time) < 1.0:
                try:
                    # Timeout dinámico dependiente del tiempo restante del segundo en curso
                    time_remaining = max(0.05, 1.0 - (time.time() - start_time))
                    event_data = self.queue.get(timeout=time_remaining)
                    batch.append(event_data)
                except queue.Empty:
                    break
                    
            if batch:
                self._persist_batch(batch)
                # Marcar las tareas como terminadas solo DESPUÉS de que se hayan persistido
                for _ in range(len(batch)):
                    self.queue.task_done()
                
    def _persist_batch(self, batch):
        """
        Persiste de forma masiva (bulk_save_objects) en una única transacción de base de datos.
        """
        session = get_session()
        flush_start = time.time()
        try:
            events = []
            for item in batch:
                event = SearchEvent(
                    query=item["query"],
                    latency=item["latency"],
                    cache_hit=item["cache_hit"],
                    top_result_hash=item["top_result_hash"],
                    clicked=0
                )
                events.append(event)
                
            session.bulk_save_objects(events)
            session.commit()
            
            flush_end = time.time()
            with self.stats_lock:
                self.last_flush_latency = (flush_end - flush_start) * 1000.0
                
        except Exception as e:
            session.rollback()
            print(f"❌ [AnalyticsWorker] Error al persistir lote de analíticas ({len(batch)} registros): {e}")
        finally:
            session.close()
