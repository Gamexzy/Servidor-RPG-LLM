import os
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, Any, List
from neo4j import GraphDatabase

# [2025-08-01] Sempre coloque os imports no topo do script.

# Alterado para atender o path /query/graph do frontend
router = APIRouter(prefix="/query", tags=["graph"])

# --- Configuração ---
# A leitura do os.getenv acontece no momento do import.
# Por isso o load_dotenv() deve ocorrer antes do import deste arquivo no main.py.
URI = os.getenv("NEO4J_URI")
USER = os.getenv("NEO4J_USER")
PASSWORD = os.getenv("NEO4J_PASSWORD")

driver = None

class GraphEntityQuery(BaseModel):
    entity: str
    universeId: str
    userId: str
    depth: int = 1

def init_graph_module():
    global driver
    print("🕸️ [GRAPH] Conectando ao Neo4j...")
    
    # [DEBUG] Mostra quais credenciais estão sendo usadas de fato
    # (Útil para confirmar se o .env foi carregado corretamente)
    print(f"🕸️ [GRAPH] Configuração -> URI: '{URI}' | User: '{USER}'")

    try:
        driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))
        driver.verify_connectivity()
        print("✅ [GRAPH] Conexão estabelecida.")
    except Exception as e:
        print(f"⚠️ [GRAPH] Aviso: Não foi possível conectar ao Neo4j ({e}).")

def close_graph_module():
    if driver:
        driver.close()

# --- Funções Internas ---

async def internal_ingest_edges(edges: List[Dict[str, Any]], universe_id: str, user_id: str):
    if not driver:
        return
    
    # Prepara os dados: garante que 'properties' seja um dict válido para o APOC não falhar
    prepared_edges = []
    for edge in edges:
        e_copy = edge.copy()
        if "properties" not in e_copy or e_copy["properties"] is None:
            e_copy["properties"] = {}
        prepared_edges.append(e_copy)

    # Query Cypher otimizada para Merge (Upsert) em lote
    # Requer plugin APOC instalado no Neo4j (apoc.create.relationship)
    cypher = """
    MATCH (u:Universe {id: $universeId})
    UNWIND $edges AS edge
    MERGE (s:Entity {name: edge.subject, universeId: $universeId, userId: $userId})
    MERGE (o:Entity {name: edge.object, universeId: $universeId, userId: $userId})
    
    MERGE (u)-[:CONTAINS]->(s)
    MERGE (u)-[:CONTAINS]->(o)
    
    WITH s, o, edge
    CALL apoc.create.relationship(s, edge.relation, edge.properties, o) YIELD rel
    RETURN count(rel) as rel_count
    """
    
    try:
        with driver.session() as session:
            result = session.run(cypher, {
                "edges": prepared_edges,
                "universeId": universe_id,
                "userId": user_id
            })
            summary = result.single()
            count = summary["rel_count"] if summary else 0
            print(f"🕸️ [GRAPH] {count} arestas processadas (Lote otimizado).")
            
    except Exception as e:
        print(f"❌ [GRAPH] Erro ao ingerir arestas (Verifique se o APOC está instalado): {e}")

# --- Rotas ---

@router.post("/graph")
async def query_graph_context(req: GraphEntityQuery):
    if not driver:
        return {"edges": []}
    
    # Busca nós conectados à entidade especificada
    cypher = """
    MATCH (n:Entity {name: $entity, universeId: $universeId, userId: $userId})-[r]-(m:Entity)
    RETURN n.name as subject, type(r) as relation, m.name as object, properties(r) as props
    LIMIT 50
    """
    
    try:
        records, summary = driver.execute_query(
            cypher, 
            {"entity": req.entity, "universeId": req.universeId, "userId": req.userId}, 
            database_="neo4j"
        )
        
        results = []
        for record in records:
            results.append({
                "subject": record["subject"],
                "relation": record["relation"],
                "object": record["object"],
                "properties": record["props"]
            })
            
        print(f"🕸️ [GRAPH] Busca '{req.entity}' -> {len(results)} conexões.")
        return {"edges": results}
    except Exception as e:
        print(f"❌ [GRAPH] Erro Cypher: {e}")
        return {"edges": []}

# --- Execução Standalone (Manutenção) ---

def reset_database():
    if not driver:
        print("❌ [GRAPH] Driver não conectado.")
        return
    
    print("\n⚠️  PERIGO: Isso apagará TODOS os nós e relacionamentos do Neo4j!")
    confirm = input("Digite 'DELETAR' para confirmar: ")
    
    if confirm == "DELETAR":
        try:
            with driver.session() as session:
                session.run("MATCH (n) DETACH DELETE n")
            print("✅ [GRAPH] Banco de dados limpo com sucesso (MATCH (n) DETACH DELETE n).")
        except Exception as e:
            print(f"❌ [GRAPH] Erro ao resetar: {e}")
    else:
        print("❌ Operação cancelada.")

if __name__ == "__main__":
    # Permite rodar este arquivo diretamente para manutenção
    from dotenv import load_dotenv
    
    # Carrega variáveis de ambiente (assume que .env está na raiz do projeto)
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))
    
    # Atualiza credenciais (pois foram lidas como None no topo do script antes do load_dotenv)
    URI = os.getenv("NEO4J_URI")
    USER = os.getenv("NEO4J_USER")
    PASSWORD = os.getenv("NEO4J_PASSWORD")
    
    init_graph_module()
    
    while True:
        print("\n--- 🛠️  Menu de Manutenção Neo4j ---")
        print("1. Resetar Banco de Dados (Apagar Tudo)")
        print("2. Sair")
        
        opt = input("Escolha uma opção: ")
        1
        if opt == "1":
            reset_database()
        elif opt == "2":
            close_graph_module()
            print("Saindo...")
            break
        else:
            print("Opção inválida.")