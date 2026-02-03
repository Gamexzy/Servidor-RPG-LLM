# [2025-08-01] Sempre coloque os imports no topo do script.
import uvicorn
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Carrega variáveis de ambiente antes de importar os roteadores
load_dotenv() 

# Importa os roteadores
from routers import rag, state, graph, auth, library, ingest  # noqa: E402

# --- Gerenciador de Ciclo de Vida ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- STARTUP ---
    print("🚀 INICIANDO SISTEMA CRONOS (Modo Lifespan)...")
    
    # Inicializa cada módulo
    rag.init_rag_module()
    state.init_state_module()
    graph.init_graph_module()
    library.init_library_module()
    
    print("🌟 SISTEMA PRONTO E ONLINE NA PORTA 8000!")
    
    yield
    
    # --- SHUTDOWN ---
    print("🛑 Desligando sistemas...")
    graph.close_graph_module()
    print("✅ Sistemas desligados com segurança.")

# --- Configuração da App ---
app = FastAPI(
    title="Cronos Super Server", 
    version="3.3.0 - Fix de Imports e Conexão Neo4j",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registra as rotas
app.include_router(auth.router)     # /auth
app.include_router(library.router)  # /library
app.include_router(ingest.router)   # /ingest
app.include_router(rag.router)      # /query (Vector)
app.include_router(graph.router)    # /query (Graph)
app.include_router(state.router)    # /state (Legacy/Debug)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)