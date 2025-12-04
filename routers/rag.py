import uuid
import chromadb
import torch
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
from sentence_transformers import SentenceTransformer

# Cria o "Roteador" (como se fosse um mini-app)
router = APIRouter(prefix="/rag", tags=["rag"])

# --- Configurações ---
MODEL_NAME = "intfloat/multilingual-e5-large"
CHROMA_PATH = "./chroma_db"

# --- Globais ---
embedding_model = None
chroma_client = None
collection = None

# --- Models ---
class RagIngest(BaseModel):
    text: str
    metadata: Dict[str, Any]

class RagQuery(BaseModel):
    query: str
    n_results: int = 3

# --- Inicialização (Chamada pelo main.py) ---
def init_rag_module():
    global embedding_model, chroma_client, collection
    print("🧠 [RAG] Inicializando módulo de memória...")
    
    # 1. GPU Setup
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"🔧 [RAG] Hardware: {device.upper()}")
    
    # 2. Carregar Modelo
    try:
        embedding_model = SentenceTransformer(MODEL_NAME, device=device)
        print("✅ [RAG] Modelo carregado.")
    except Exception as e:
        print(f"❌ [RAG] Falha ao carregar modelo: {e}")
        raise e

    # 3. ChromaDB
    chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = chroma_client.get_or_create_collection(
        name="cronos_memory", 
        metadata={"hnsw:space": "cosine"}
    )
    print("✅ [RAG] Banco Vetorial pronto.")

# --- Rotas ---

@router.post("/ingest")
async def ingest_memory(req: RagIngest):
    try:
        doc_id = str(uuid.uuid4())
        # O modelo e5 exige prefixo 'passage:'
        emb = embedding_model.encode(f"passage: {req.text}").tolist()
        
        collection.add(
            ids=[doc_id],
            embeddings=[emb],
            documents=[req.text],
            metadatas=[req.metadata]
        )
        print(f"🧠 [RAG] Ingestão: {req.text[:30]}...")
        return {"status": "success", "id": doc_id}
    except Exception as e:
        raise HTTPException(500, str(e))

@router.post("/query")
async def query_memory(req: RagQuery):
    try:
        # O modelo e5 exige prefixo 'query:'
        emb = embedding_model.encode(f"query: {req.query}").tolist()
        
        res = collection.query(
            query_embeddings=[emb], 
            n_results=req.n_results
        )
        
        docs = res['documents'][0] if res['documents'] else []
        print(f"🔍 [RAG] Busca por '{req.query}' -> {len(docs)} resultados.")
        return {"documents": docs}
    except Exception as e:
        raise HTTPException(500, str(e))