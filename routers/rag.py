import uuid
import chromadb
import torch
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List

# [2025-08-01] Sempre coloque os imports no topo do script.
from sentence_transformers import SentenceTransformer

# Alterado para atender o path /query/vector do frontend
router = APIRouter(prefix="/query", tags=["rag"])

# --- Configurações ---
MODEL_NAME = "intfloat/multilingual-e5-large"
CHROMA_PATH = "./chroma_db"

# --- Globais ---
embedding_model = None
chroma_client = None
collection = None

# --- Models ---
class VectorQuery(BaseModel):
    query: str
    universeId: str
    userId: str
    n_results: int = 5

# --- Inicialização ---
def init_rag_module():
    global embedding_model, chroma_client, collection
    print("🧠 [RAG] Inicializando módulo de memória...")
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"🔧 [RAG] Hardware: {device.upper()}")
    
    try:
        embedding_model = SentenceTransformer(MODEL_NAME, device=device)
        print("✅ [RAG] Modelo carregado.")
    except Exception as e:
        print(f"❌ [RAG] Falha ao carregar modelo: {e}")
        # Em produção, não quebre se não tiver GPU, use um modelo menor ou CPU
        raise e

    chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = chroma_client.get_or_create_collection(
        name="cronos_memory", 
        metadata={"hnsw:space": "cosine"}
    )
    print("✅ [RAG] Banco Vetorial pronto.")

# --- Funções Internas (Usadas pelo Ingest Router) ---

async def internal_ingest_text(text: str, metadata: Dict[str, Any]):
    if not collection:
        raise Exception("ChromaDB não inicializado.")
        
    doc_id = str(uuid.uuid4())
    # O modelo e5 exige prefixo 'passage:' para documentos
    emb = embedding_model.encode(f"passage: {text}").tolist()
    
    collection.add(
        ids=[doc_id],
        embeddings=[emb],
        documents=[text],
        metadatas=[metadata]
    )
    print(f"🧠 [RAG] Memória salva: {text[:40]}...")

# --- Rotas Públicas ---

@router.post("/vector")
async def query_vector(req: VectorQuery):
    try:
        # O modelo e5 exige prefixo 'query:' para buscas
        emb = embedding_model.encode(f"query: {req.query}").tolist()
        
        # Filtro de metadados: Apenas memórias deste Usuário E deste Universo
        where_filter = {
            "$and": [
                {"userId": req.userId},
                {"universeId": req.universeId}
            ]
        }
        
        res = collection.query(
            query_embeddings=[emb], 
            n_results=req.n_results,
            where=where_filter
        )
        
        docs = res['documents'][0] if res['documents'] else []
        print(f"🔍 [RAG] Busca '{req.query}' (U:{req.universeId}) -> {len(docs)} res.")
        return {"documents": docs}
    except Exception as e:
        print(f"❌ [RAG] Erro na busca: {e}")
        # Retorna lista vazia para não quebrar o jogo
        return {"documents": []}