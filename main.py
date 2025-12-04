import os
import uuid
import uvicorn
import chromadb
import torch
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer

# --- Configurações ---
# Modelo multilingue otimizado (intfloat/multilingual-e5-large)
# Ele é excelente para PT-BR e roda bem na RTX 3060
MODEL_NAME = "intfloat/multilingual-e5-large"
CHROMA_PATH = "./chroma_db"
SERVER_PORT = 8000

# --- Inicialização da App ---
app = FastAPI(title="Cronos RAG Server", version="1.0.0")

# CORS: Importante! Permite que seu Front (AI Studio/Localhost) converse com este servidor
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Globais ---
embedding_model = None
chroma_client = None
collection = None

# --- Schemas de Dados ---
class IngestRequest(BaseModel):
    text: str
    metadata: Dict[str, Any]

class QueryRequest(BaseModel):
    query: str
    n_results: int = 3

class QueryResponse(BaseModel):
    documents: List[str]

# --- Eventos de Ciclo de Vida ---
@app.on_event("startup")
async def startup_event():
    global embedding_model, chroma_client, collection
    
    print("--- INICIANDO SERVIDOR RAG (CRONOS) ---")
    
    # 1. Configurar Dispositivo (Prioridade GPU)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"🔧 Hardware de Aceleração: {device.upper()}")
    
    if device == "cuda":
        print(f"   GPU Detectada: {torch.cuda.get_device_name(0)}")
        try:
            vram = torch.cuda.get_device_properties(0).total_memory / 1e9
            print(f"   VRAM Disponível: {vram:.2f} GB")
        except:
            pass
    
    # 2. Carregar Modelo de Embedding
    print(f"📥 Carregando modelo '{MODEL_NAME}'... (Aguarde o download na 1ª vez)")
    try:
        embedding_model = SentenceTransformer(MODEL_NAME, device=device)
        print("✅ Modelo carregado e pronto para inferência.")
    except Exception as e:
        print(f"❌ Erro crítico ao carregar modelo: {e}")
        raise e

    # 3. Inicializar Banco Vetorial (Persistente)
    print(f"💾 Conectando ao ChromaDB em '{CHROMA_PATH}'...")
    chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
    
    # Cria ou recupera a coleção de memória
    collection = chroma_client.get_or_create_collection(
        name="cronos_memory",
        metadata={"hnsw:space": "cosine"} 
    )
    print(f"✅ Banco de dados conectado. Memórias armazenadas: {collection.count()}")

# --- Rotas da API ---

@app.get("/health")
async def health_check():
    """Verifica status e hardware."""
    return {
        "status": "online", 
        "device": str(embedding_model.device) if embedding_model else "unknown",
        "memories_count": collection.count() if collection else 0
    }

@app.post("/ingest")
async def ingest_memory(request: IngestRequest):
    """Recebe narrativa do jogo e salva no banco vetorial."""
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Texto vazio.")

    try:
        doc_id = str(uuid.uuid4())
        # Prefixo 'passage:' é exigido pelo modelo e5 para documentos
        text_to_embed = f"passage: {request.text}"
        embedding = embedding_model.encode(text_to_embed).tolist()
        
        collection.add(
            ids=[doc_id],
            embeddings=[embedding],
            documents=[request.text],
            metadatas=[request.metadata]
        )
        
        print(f"🧠 [MEMÓRIA] Ingerida: {request.text[:40]}...")
        return {"status": "success", "id": doc_id}

    except Exception as e:
        print(f"❌ Erro na ingestão: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query", response_model=QueryResponse)
async def query_memory(request: QueryRequest):
    """Busca memórias relevantes."""
    try:
        # Prefixo 'query:' é exigido pelo modelo e5 para buscas
        query_to_embed = f"query: {request.query}"
        query_embedding = embedding_model.encode(query_to_embed).tolist()
        
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=request.n_results
        )
        
        documents = results['documents'][0] if results['documents'] else []
        print(f"🔍 [BUSCA] '{request.query}' -> {len(documents)} resultados.")
        return {"documents": documents}

    except Exception as e:
        print(f"❌ Erro na busca: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    # Roda em todas as interfaces de rede local
    uvicorn.run(app, host="0.0.0.0", port=SERVER_PORT)