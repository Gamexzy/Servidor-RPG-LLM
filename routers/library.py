# [2025-08-01] Sempre coloque os imports no topo do script.
import logging
import json
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from routers import graph # Importa o módulo para acesso dinâmico ao driver

# Configuração de Logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("library")

router = APIRouter(prefix="/library", tags=["library"])

# --- Models (Atualizados para Arquitetura de 3 Pilares) ---

class UniverseModel(BaseModel):
    id: str
    userId: str
    name: str
    description: Optional[str] = ""
    genre: Optional[str] = ""
    image: Optional[str] = ""
    createdAt: Optional[str] = ""
    # Novos campos (Frontend v3)
    physics: Optional[List[str]] = []
    knownTruths: Optional[List[str]] = []
    chronicles: Optional[List[Any]] = []
    champions: Optional[List[Any]] = []
    worlds: Optional[List[Any]] = []
    structure: Optional[str] = "singular_world"
    navigationMethod: Optional[str] = "physical"
    magicSystem: Optional[str] = ""
    cosmology: Optional[str] = ""
    graphContext: Optional[List[Dict[str, Any]]] = []

class CharacterModel(BaseModel):
    id: str
    userId: str
    name: str
    description: Optional[str] = ""
    archetype: Optional[str] = ""
    image: Optional[str] = ""
    stats: Optional[Dict[str, Any]] = {}
    adventuresPlayed: Optional[int] = 0
    createdAt: Optional[str] = ""
    graphContext: Optional[List[Dict[str, Any]]] = []

class AdventureModel(BaseModel):
    id: str
    userId: str
    universeId: str # Onde a aventura acontece
    characterId: str # Qual template de personagem está sendo usado
    name: str
    description: Optional[str] = ""
    currentStep: Optional[str] = ""
    createdAt: Optional[str] = ""
    # Novos campos de metadados
    characterName: Optional[str] = ""
    universeName: Optional[str] = ""
    universeGenre: Optional[str] = ""
    lastLocation: Optional[str] = ""
    startDate: Optional[str] = ""
    messages: Optional[List[Any]] = [] 
    graphContext: Optional[List[Dict[str, Any]]] = []

def init_library_module():
    logger.info("📚 [LIBRARY] Módulo de Biblioteca inicializado (v3 - 3 Pilares).")

# --- Helpers ---

async def process_graph_context(context: List[Dict], universe_id: str, user_id: str):
    """Transforma o contexto do frontend (source/target) para o formato do graph ingest (subject/object)."""
    if not context or not graph.driver:
        return
    
    edges = []
    for item in context:
        # Mapeia source->subject, target->object
        edges.append({
            "subject": item.get("source"),
            "relation": item.get("relation"),
            "object": item.get("target"),
            "properties": {}
        })
    
    # Chama o ingestor interno do módulo graph
    await graph.internal_ingest_edges(edges, universe_id, user_id)

# --- Rotas de Leitura (GET) ---

@router.get("/{user_id}")
async def get_user_library(user_id: str):
    """Retorna todos os universos, personagens (templates) e aventuras do usuário."""
    if not graph.driver:
        raise HTTPException(status_code=503, detail="Database not connected")
    
    try:
        data = {
            "universes": [],
            "characters": [],
            "adventures": []
        }
        
        with graph.driver.session() as session:
            # 1. Busca Universos
            result_uni = session.run("MATCH (user:User {userId: $userId})-[:CREATED]->(u:Universe) RETURN u", userId=user_id)
            data["universes"] = [dict(record["u"]) for record in result_uni]
            
            # 2. Busca Personagens (Agora são globais/templates)
            result_char = session.run("MATCH (user:User {userId: $userId})-[:CREATED]->(c:Character) RETURN c", userId=user_id)
            data["characters"] = [dict(record["c"]) for record in result_char]

            # 3. Busca Aventuras
            result_adv = session.run("MATCH (user:User {userId: $userId})-[:PLAYS]->(a:Adventure) RETURN a", userId=user_id)
            data["adventures"] = [dict(record["a"]) for record in result_adv]
            
        return data
        
    except Exception as e:
        logger.error(f"Erro ao buscar biblioteca: {e}")
        return {"universes": [], "characters": [], "adventures": []}

# --- Rotas de Escrita (POST) ---

@router.post("/universe")
async def save_universe(item: UniverseModel):
    if not graph.driver:
        raise HTTPException(status_code=503, detail="Database not connected")
    
    cypher = """
    MATCH (user:User {userId: $userId})
    MERGE (u:Universe {id: $id})
    SET u.name = $name,
        u.description = $description,
        u.genre = $genre,
        u.image = $image,
        u.createdAt = $createdAt,
        u.physics = $physics,
        u.knownTruths = $knownTruths,
        u.structure = $structure,
        u.navigationMethod = $navigationMethod,
        u.magicSystem = $magicSystem,
        u.cosmology = $cosmology,
        u.chronicles = $chroniclesStr,
        u.champions = $championsStr,
        u.worlds = $worldsStr
    
    MERGE (user)-[:CREATED]->(u)
    RETURN u.id
    """
    try:
        # Prepara dados (Serializa listas complexas para string JSON)
        params = item.dict()
        params["chroniclesStr"] = json.dumps(item.chronicles)
        params["championsStr"] = json.dumps(item.champions)
        params["worldsStr"] = json.dumps(item.worlds)

        with graph.driver.session() as session:
            session.run(cypher, params)
        
        # Processa o contexto de grafo (se houver)
        if item.graphContext:
            await process_graph_context(item.graphContext, item.id, item.userId)
            
        return {"status": "success", "id": item.id}
    except Exception as e:
        logger.error(f"Erro ao salvar universo: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/character")
async def save_character(item: CharacterModel):
    if not graph.driver:
        raise HTTPException(status_code=503, detail="Database not connected")
    
    # Atualizado: Cria personagem sem vínculo com universo (Template)
    cypher = """
    MATCH (user:User {userId: $userId})
    MERGE (c:Character {id: $id})
    SET c.name = $name,
        c.description = $description,
        c.archetype = $archetype,
        c.image = $image,
        c.stats = $stats,
        c.createdAt = $createdAt,
        c.adventuresPlayed = $adventuresPlayed
        
    MERGE (user)-[:CREATED]->(c)
    
    RETURN c.id
    """
    try:
        # Prepara dados (Serializa dict para string JSON)
        params = item.dict()
        params["stats"] = json.dumps(item.stats)

        with graph.driver.session() as session:
            session.run(cypher, params)

        # Processa o contexto de grafo (se houver)
        if item.graphContext:
            await process_graph_context(item.graphContext, "GLOBAL", item.userId)

        return {"status": "success", "id": item.id}
    except Exception as e:
        logger.error(f"Erro ao salvar personagem: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/adventure")
async def save_adventure(item: AdventureModel):
    if not graph.driver:
        raise HTTPException(status_code=503, detail="Database not connected")
    
    # Atualizado: A Aventura agora é o nó que conecta o Personagem ao Universo
    cypher = """
    MATCH (user:User {userId: $userId})
    MATCH (u:Universe {id: $universeId})
    MATCH (c:Character {id: $characterId})
    
    MERGE (a:Adventure {id: $id})
    SET a.name = $name,
        a.description = $description,
        a.currentStep = $currentStep,
        a.createdAt = $createdAt,
        a.characterName = $characterName,
        a.universeName = $universeName,
        a.universeGenre = $universeGenre,
        a.lastLocation = $lastLocation,
        a.startDate = $startDate
    
    // Conecta tudo
    MERGE (user)-[:PLAYS]->(a)
    MERGE (a)-[:HAPPENS_IN]->(u)
    MERGE (a)-[:USES_TEMPLATE]->(c)
    
    RETURN a.id
    """
    try:
        with graph.driver.session() as session:
            # exclude={"messages"} pois mensagens não vão pro grafo dessa forma
            session.run(cypher, item.dict(exclude={"messages"}))
            
        # Processa o contexto de grafo (se houver)
        if item.graphContext:
            await process_graph_context(item.graphContext, item.universeId, item.userId)
            
        return {"status": "success", "id": item.id}
    except Exception as e:
        logger.error(f"Erro ao salvar aventura: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- Rotas de Deleção (DELETE) ---

@router.delete("/universe/{item_id}")
async def delete_universe(item_id: str, userId: str = Query(...)):
    if not graph.driver:
        raise HTTPException(status_code=503, detail="Database not connected")
    
    # Deleta universo e suas aventuras, mas PRESERVA os personagens (templates)
    cypher = """
    MATCH (user:User {userId: $userId})-[:CREATED]->(u:Universe {id: $id})
    OPTIONAL MATCH (a:Adventure)-[:HAPPENS_IN]->(u)
    DETACH DELETE u, a
    """
    try:
        with graph.driver.session() as session:
            result = session.run(cypher, id=item_id, userId=userId)
            result.consume()
            logger.info(f"Universo {item_id} deletado.")
        return {"status": "deleted", "id": item_id}
    except Exception as e:
        logger.error(f"Erro ao deletar universo: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/character/{item_id}")
async def delete_character(item_id: str, userId: str = Query(...)):
    if not graph.driver:
        raise HTTPException(status_code=503, detail="Database not connected")

    # Deleta o template. (Futuramente: avisar se há aventuras ativas usando ele)
    cypher = """
    MATCH (u:User {userId: $userId})-[r:CREATED]->(c:Character {id: $id})
    DELETE r
    """
    try:
        with graph.driver.session() as session:
            session.run(cypher, id=item_id, userId=userId)
        return {"status": "archived", "id": item_id}
    except Exception as e:
        logger.error(f"Erro ao deletar personagem: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/adventure/{item_id}")
async def delete_adventure(item_id: str, userId: str = Query(...)):
    if not graph.driver:
        raise HTTPException(status_code=503, detail="Database not connected")

    cypher = """
    MATCH (a:Adventure {id: $id})
    WHERE EXISTS {
        MATCH (user:User {userId: $userId})-[:PLAYS]->(a)
    }
    DETACH DELETE a
    """
    try:
        with graph.driver.session() as session:
            session.run(cypher, id=item_id, userId=userId)
        return {"status": "deleted", "id": item_id}
    except Exception as e:
        logger.error(f"Erro ao deletar aventura: {e}")
        raise HTTPException(status_code=500, detail=str(e))