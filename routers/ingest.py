from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from . import rag, state, graph

# [2025-08-01] Sempre coloque os imports no topo do script.

router = APIRouter(prefix="/ingest", tags=["ingest"])

# --- Models (Espelhando types.ts do Frontend) ---

class VectorData(BaseModel):
    text: str
    type: str  # 'turn' | 'lore' | 'intro'
    location: str

class SqlData(BaseModel):
    playerStatus: Any
    inventory: List[str]
    worldState: Any

class GraphEdge(BaseModel):
    subject: str
    relation: str
    object: str
    properties: Optional[Dict[str, Any]] = None

class UnifiedIngestPayload(BaseModel):
    userId: str
    universeId: str
    turnId: int
    timestamp: str
    vectorData: VectorData
    sqlData: SqlData
    graphData: List[GraphEdge]

# --- Rota de Ingestão Unificada ---

@router.post("/unified")
async def ingest_unified(payload: UnifiedIngestPayload):
    """
    Recebe o payload completo do turno e distribui para os sistemas apropriados.
    """
    print(f"📥 [INGEST] Recebendo turno {payload.turnId} de {payload.userId}...")
    errors = []

    # 1. Ingestão Semântica (ChromaDB)
    try:
        # Monta metadados para filtro futuro
        metadata = {
            "userId": payload.userId,
            "universeId": payload.universeId,
            "turnId": payload.turnId,
            "type": payload.vectorData.type,
            "location": payload.vectorData.location,
            "timestamp": payload.timestamp
        }
        await rag.internal_ingest_text(payload.vectorData.text, metadata)
    except Exception as e:
        print(f"❌ [INGEST] Erro Vector: {e}")
        errors.append(f"Vector Error: {str(e)}")

    # 2. Ingestão Estruturada (SQLite - Logs)
    try:
        await state.internal_log_turn(
            payload.userId, 
            payload.universeId, 
            payload.turnId, 
            payload.sqlData.dict()
        )
    except Exception as e:
        print(f"❌ [INGEST] Erro SQL: {e}")
        errors.append(f"SQL Error: {str(e)}")

    # 3. Ingestão de Relacionamentos (Neo4j - Graph)
    if payload.graphData:
        try:
            edges_dicts = [edge.dict() for edge in payload.graphData]
            await graph.internal_ingest_edges(
                edges_dicts, 
                payload.universeId, 
                payload.userId
            )
        except Exception as e:
            print(f"❌ [INGEST] Erro Graph: {e}")
            errors.append(f"Graph Error: {str(e)}")

    if errors:
        return {"status": "partial_success", "errors": errors}
    
    print("✅ [INGEST] Turno processado com sucesso.")
    return {"status": "success"}