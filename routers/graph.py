import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
from neo4j import GraphDatabase

router = APIRouter(prefix="/graph", tags=["graph"])

# --- Configuração ---
# Lê do ambiente ou usa padrão
URI = os.getenv("NEO4J_URI", "neo4j://localhost:7687")
USER = os.getenv("NEO4J_USER", "neo4j")
PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

driver = None

class GraphQuery(BaseModel):
    cypher: str
    params: Dict[str, Any] = {}

def init_graph_module():
    global driver
    print("🕸️ [GRAPH] Conectando ao Neo4j...")
    try:
        driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))
        driver.verify_connectivity()
        print("✅ [GRAPH] Conexão estabelecida.")
    except Exception as e:
        print(f"⚠️ [GRAPH] Aviso: Não foi possível conectar ao Neo4j ({e}).")

def close_graph_module():
    if driver:
        driver.close()

@router.post("/query")
async def run_cypher(req: GraphQuery):
    if not driver:
        raise HTTPException(503, "Banco de Grafos desconectado.")
    
    try:
        # Executa query e retorna lista de dicionários
        records, summary = driver.execute_query(req.cypher, req.params, database_="neo4j")
        results = [dict(record) for record in records]
        print(f"🕸️ [GRAPH] Query executada: {len(results)} registros.")
        return {"results": results}
    except Exception as e:
        print(f"❌ [GRAPH] Erro Cypher: {e}")
        raise HTTPException(500, str(e))