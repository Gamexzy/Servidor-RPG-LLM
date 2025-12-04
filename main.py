import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Importa os roteadores (seus módulos)
from routers import rag, state, graph

# --- Gerenciador de Ciclo de Vida (Substitui on_event) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- STARTUP (Executado ao ligar) ---
    print("🚀 INICIANDO SISTEMA CRONOS (Modo Lifespan)...")
    
    # Inicializa cada módulo
    # RAG: Carrega modelo na GPU
    rag.init_rag_module()
    
    # State: Verifica tabelas SQLite
    state.init_state_module()
    
    # Graph: Conecta ao Neo4j
    graph.init_graph_module()
    
    print("🌟 SISTEMA PRONTO E ONLINE NA PORTA 8000!")
    
    yield  # O servidor roda aqui enquanto estiver ligado
    
    # --- SHUTDOWN (Executado ao desligar) ---
    print("🛑 Desligando sistemas...")
    graph.close_graph_module()
    print("✅ Sistemas desligados com segurança.")

# --- Configuração da App ---
# Passamos a função 'lifespan' aqui na criação do app
app = FastAPI(
    title="Cronos Super Server", 
    version="3.1.0",
    lifespan=lifespan
)

# Configuração de CORS (Permite acesso do React/Ngrok)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registra as rotas
app.include_router(rag.router)
app.include_router(state.router)
app.include_router(graph.router)

if __name__ == "__main__":
    # Roda o servidor
    uvicorn.run(app, host="0.0.0.0", port=8000)