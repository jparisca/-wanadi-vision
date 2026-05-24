import os
import json
import tempfile
from threading import Lock, RLock
import numpy as np
import faiss
from datetime import datetime, timezone
from sqlalchemy import func
from sqlalchemy.orm import selectinload
from database.db_utils import get_session
from database.schema import Prompt, PromptEmbedding, PromptVersion

MODEL_NAME = "all-MiniLM-L6-v2"
VECTOR_DIM = 384
INDEX_PATH = "nexus_faiss.index"
MAPPINGS_PATH = "nexus_mappings.json"

class IndexManager:
    _instance = None
    _lock = Lock()
    
    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if not cls._instance:
                cls._instance = super(IndexManager, cls).__new__(cls, *args, **kwargs)
                cls._instance._initialized = False
        return cls._instance
        
    def __init__(self):
        if self._initialized:
            return
        self.index = None
        self.mappings = []
        self.last_refreshed = None
        self.index_state_hash = ""
        self.rw_lock = RLock()
        self._initialized = True
        
        self.index_rebuild_total = 0
        self.last_rebuild_timestamp = None
        self.snapshot_load_failures = 0
        
        # Intentar cargar desde el snapshot al iniciar
        self.load_snapshot()
        
    def build(self) -> bool:
        """
        Consulta la base de datos, construye DTOs serializables (previniendo ORM detached issues)
        y genera un índice FAISS HNSWFlat (ANN real) con hiperparámetros óptimos para recall e indexación.
        """
        print("🛠️  [IndexManager] Iniciando construcción del índice HNSW ANN...")
        session = get_session()
        try:
            # Carga Eager para evitar N+1 queries
            results = (
                session.query(Prompt, PromptEmbedding)
                .options(
                    selectinload(Prompt.versions).selectinload(PromptVersion.sources)
                )
                .join(PromptEmbedding)
                .filter(
                    Prompt.embedding_status == "completed",
                    PromptEmbedding.model_name == MODEL_NAME
                )
                .all()
            )
            
            # Obtener el hash de estado de base de datos actual con firma ultra-robusta
            db_count = len(results)
            db_max_id = max([p.id for p, _ in results], default=0)
            db_sum_id = sum([p.id for p, _ in results])
            db_max_emb_time = session.query(func.max(PromptEmbedding.created_at)).scalar()
            db_max_emb_ts = db_max_emb_time.timestamp() if db_max_emb_time else 0.0
            state_hash = f"{db_count}:{db_max_id}:{db_sum_id}:{db_max_emb_ts}"
            
            if not results:
                print("⚠️  [IndexManager] No se encontraron prompts completados en base de datos.")
                with self.rw_lock:
                    self.index = None
                    self.mappings = []
                    self.index_state_hash = state_hash
                return False
                
            vectors = []
            new_mappings = []
            
            for prompt, prompt_emb in results:
                vector = np.frombuffer(prompt_emb.vector, dtype=np.float32)
                if len(vector) == VECTOR_DIM:
                    vectors.append(vector)
                    
                    # Convertir objeto ORM a DTO plano e independiente (Evita DetachedInstanceError)
                    dto = {
                        "prompt_id": prompt.id,
                        "hash_id": prompt.hash_id,
                        "prompt_text": prompt.canonical_text,
                        "versions": []
                    }
                    
                    for version in prompt.versions:
                        v_dto = {
                            "id": version.id,
                            "engine": version.engine,
                            "parameters": version.parameters,
                            "sources": []
                        }
                        for source in version.sources:
                            v_dto["sources"].append({
                                "id": source.id,
                                "platform": source.platform,
                                "author": source.author,
                                "url": source.url,
                                "engagement_score": float(source.engagement_score or 0.0)
                            })
                        dto["versions"].append(v_dto)
                        
                    new_mappings.append(dto)
                    
            if not vectors:
                return False
                
            matrix = np.vstack(vectors).astype(np.float32)
            
            # Crear índice HNSW ANN real con Producto Punto (Inner Product)
            # M = 16 (número de enlaces por nodo), METRIC_INNER_PRODUCT para vectores L2 normalizados
            hnsw_index = faiss.IndexHNSWFlat(VECTOR_DIM, 16, faiss.METRIC_INNER_PRODUCT)
            
            # Endurecimiento metodológico de HNSW: configuración de parámetros críticos de recall/latencia
            hnsw_index.hnsw.efConstruction = 200
            hnsw_index.hnsw.efSearch = 64
            
            hnsw_index.add(matrix)
            
            # Reemplazo atómico con bloqueo de escritura
            with self.rw_lock:
                self.index = hnsw_index
                self.mappings = new_mappings
                self.index_state_hash = state_hash
                self.last_refreshed = datetime.now(timezone.utc)
                self.index_rebuild_total += 1
                self.last_rebuild_timestamp = self.last_refreshed
                
            print(f"✨ [IndexManager] HNSW Index construido exitosamente con {hnsw_index.ntotal} vectores (efConstruction=200, efSearch=64).")
            
            # Guardar snapshot físico automáticamente
            self.save_snapshot()
            return True
            
        except Exception as e:
            print(f"❌ [IndexManager] Error construyendo el índice: {e}")
            return False
        finally:
            session.close()
            
    def refresh(self, force: bool = False) -> bool:
        """
        Actualiza el índice si ha habido cambios en base de datos.
        Aplica un throttling de 10 segundos para evitar sobrecargar SQLite con consultas.
        Soporta indexación incremental rápida si solo hay adiciones, y reconstrucción de respaldo si hay eliminaciones.
        """
        if not force and self.last_refreshed is not None:
            elapsed = (datetime.now(timezone.utc) - self.last_refreshed).total_seconds()
            if elapsed < 10.0:
                return False
                
        session = get_session()
        try:
            local_count = len(self.mappings)
            local_max_id = max([m["prompt_id"] for m in self.mappings], default=0) if self.mappings else 0
            
            db_count = session.query(Prompt).filter_by(embedding_status="completed").count()
            db_max_id = session.query(func.max(Prompt.id)).filter_by(embedding_status="completed").scalar() or 0
            db_sum_id = session.query(func.sum(Prompt.id)).filter_by(embedding_status="completed").scalar() or 0
            db_max_emb_time = session.query(func.max(PromptEmbedding.created_at)).scalar()
            db_max_emb_ts = db_max_emb_time.timestamp() if db_max_emb_time else 0.0
            state_hash = f"{db_count}:{db_max_id}:{db_sum_id}:{db_max_emb_ts}"
            
            if state_hash == self.index_state_hash and self.index is not None:
                return False  # No hay cambios
                
            if not self.index or local_count == 0:
                print("🔄 [IndexManager] Índice vacío o no inicializado. Reconstruyendo por completo...")
                return self.build()
                
            # Si solo hay inserciones nuevas (id mayor y contador ascendente)
            if db_count > local_count and db_max_id > local_max_id:
                print(f"⚡ [IndexManager] Detectadas nuevas inserciones. Iniciando indexación incremental ({db_count - local_count} nuevos prompts)...")
                new_results = (
                    session.query(Prompt, PromptEmbedding)
                    .options(
                        selectinload(Prompt.versions).selectinload(PromptVersion.sources)
                    )
                    .join(PromptEmbedding)
                    .filter(
                        Prompt.embedding_status == "completed",
                        PromptEmbedding.model_name == MODEL_NAME,
                        Prompt.id > local_max_id
                    )
                    .all()
                )
                
                if not new_results:
                    return False
                    
                new_vectors = []
                with self.rw_lock:
                    for prompt, prompt_emb in new_results:
                        vector = np.frombuffer(prompt_emb.vector, dtype=np.float32)
                        if len(vector) == VECTOR_DIM:
                            new_vectors.append(vector)
                            
                            # Crear DTO plano
                            dto = {
                                "prompt_id": prompt.id,
                                "hash_id": prompt.hash_id,
                                "prompt_text": prompt.canonical_text,
                                "versions": []
                            }
                            for version in prompt.versions:
                                v_dto = {
                                    "id": version.id,
                                    "engine": version.engine,
                                    "parameters": version.parameters,
                                    "sources": []
                                }
                                for source in version.sources:
                                    v_dto["sources"].append({
                                        "id": source.id,
                                        "platform": source.platform,
                                        "author": source.author,
                                        "url": source.url,
                                        "engagement_score": float(source.engagement_score or 0.0)
                                    })
                                dto["versions"].append(v_dto)
                            self.mappings.append(dto)
                            
                    if new_vectors:
                        new_matrix = np.vstack(new_vectors).astype(np.float32)
                        self.index.add(new_matrix)
                        self.index_state_hash = state_hash
                        self.last_refreshed = datetime.now(timezone.utc)
                        
                    print(f"✨ [IndexManager] Indexación incremental exitosa. Agregados {len(new_vectors)} vectores.")
                    
                self.save_snapshot()
                return True
            else:
                # Si hay eliminaciones o inconsistencias de IDs, hacemos un build completo
                print("🔄 [IndexManager] Inconsistencia o eliminación detectada. Reconstruyendo index completo...")
                return self.build()
                
        except Exception as e:
            print(f"❌ [IndexManager] Error al verificar/actualizar índice: {e}")
            return False
        finally:
            session.close()
            
    def save_snapshot(self):
        """
        Guarda el estado del índice FAISS y las mappings en disco de forma segura.
        Utiliza escritura temporal y reemplazo atómico para evitar race conditions y corrupción de snapshot.
        """
        if self.index is None:
            return
            
        try:
            # Directorio base para asegurar que los archivos temporales se ubiquen en el mismo filesystem
            dir_name = os.path.dirname(os.path.abspath(INDEX_PATH))
            
            # 1. Escribir índice FAISS a archivo temporal
            tmp_index_fd, tmp_index_path = tempfile.mkstemp(dir=dir_name, suffix=".faiss")
            os.close(tmp_index_fd)  # FAISS abrirá su propio descriptor
            faiss.write_index(self.index, tmp_index_path)
            
            # Asegurar la persistencia física (fsync) de la escritura del índice FAISS
            fd_idx = os.open(tmp_index_path, os.O_RDONLY)
            try:
                os.fsync(fd_idx)
            finally:
                os.close(fd_idx)
            
            # 2. Escribir mappings JSON a archivo temporal
            tmp_map_fd, tmp_map_path = tempfile.mkstemp(dir=dir_name, suffix=".json")
            with os.fdopen(tmp_map_fd, 'w') as tmp_file:
                json.dump(self.mappings, tmp_file, indent=2)
                tmp_file.flush()
                os.fsync(tmp_file.fileno())
                
            # 3. Intercambio atómico (Rename) libre de race condition
            with self.rw_lock:
                os.replace(tmp_index_path, INDEX_PATH)
                os.replace(tmp_map_path, MAPPINGS_PATH)
                
            # Sincronizar directorio padre para garantizar la persistencia del rename en ciertos filesystems
            dir_fd = os.open(dir_name, os.O_DIRECTORY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
                
            print("💾 [IndexManager] Snapshot guardado en disco de forma atómica y segura.")
        except Exception as e:
            # Limpieza defensiva de temporales si quedan huérfanos por error
            for path in [locals().get('tmp_index_path'), locals().get('tmp_map_path')]:
                if path and os.path.exists(path):
                    try:
                        os.remove(path)
                    except OSError:
                        pass
            print(f"❌ [IndexManager] Error al guardar snapshot atómico: {e}")
            
    def load_snapshot(self) -> bool:
        """
        Carga el índice y las mappings desde el almacenamiento persistente en disco.
        Si la carga falla (ej. índice corrupto), lanza una reconstrucción automática.
        """
        if not os.path.exists(INDEX_PATH) or not os.path.exists(MAPPINGS_PATH):
            return False
            
        try:
            with self.rw_lock:
                self.index = faiss.read_index(INDEX_PATH)
                with open(MAPPINGS_PATH, "r") as f:
                    self.mappings = json.load(f)
                    
                if self.index.ntotal != len(self.mappings):
                    raise ValueError(f"Dimensión mismatch: FAISS tiene {self.index.ntotal} vectores, Mappings tiene {len(self.mappings)}")
                
                # Reconstruir firma hash local desde base de datos de forma segura
                db_count = len(self.mappings)
                db_max_id = max([m["prompt_id"] for m in self.mappings], default=0) if self.mappings else 0
                db_sum_id = sum([m["prompt_id"] for m in self.mappings]) if self.mappings else 0
                
                session = get_session()
                try:
                    db_max_emb_time = session.query(func.max(PromptEmbedding.created_at)).scalar()
                    db_max_emb_ts = db_max_emb_time.timestamp() if db_max_emb_time else 0.0
                finally:
                    session.close()
                    
                self.index_state_hash = f"{db_count}:{db_max_id}:{db_sum_id}:{db_max_emb_ts}"
                self.last_refreshed = datetime.now(timezone.utc)
                
            print(f"📂 [IndexManager] Snapshot cargado con éxito ({self.index.ntotal} vectores). Hash: {self.index_state_hash}")
            return True
        except Exception as e:
            print(f"❌ [IndexManager] Error crítico al cargar snapshot (Posible corrupción): {e}")
            with self.rw_lock:
                self.snapshot_load_failures += 1
            print("🔄 [IndexManager] Iniciando recuperación de emergencia (rebuild total)...")
            return self.build()
            
    def stats(self) -> dict:
        """
        Retorna estadísticas operativas de salud del índice y SRE metrics.
        """
        with self.rw_lock:
            return {
                "active_vectors": self.index.ntotal if self.index else 0,
                "dimension": VECTOR_DIM,
                "mappings_count": len(self.mappings),
                "state_hash": self.index_state_hash,
                "last_refreshed": self.last_refreshed.isoformat() if self.last_refreshed else None,
                "using_ann": "HNSWFlat",
                "index_file_exists": os.path.exists(INDEX_PATH),
                "index_rebuild_total": self.index_rebuild_total,
                "last_rebuild_timestamp": self.last_rebuild_timestamp.isoformat() if self.last_rebuild_timestamp else None,
                "snapshot_load_failures": self.snapshot_load_failures
            }
