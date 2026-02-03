# [2025-08-01] Sempre coloque os imports no topo do script.
import logging
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

class CharacterModel(BaseModel):
    id: str
    userId: str
    # universeId removido: O personagem agora é um Template Global
    name: str
    description: Optional[str] = ""
    archetype: Optional[str] = ""
    image: Optional[str] = ""
    stats: Optional[Dict[str, Any]] = {}
    createdAt: Optional[str] = ""

class AdventureModel(BaseModel):
    id: str
    userId: str
    universeId: str # Onde a aventura acontece
    characterId: str # Qual template de personagem está sendo usado
    name: str
    description: Optional[str] = ""
    currentStep: Optional[str] = ""
    createdAt: Optional[str] = ""
    messages: Optional[List[Any]] = [] 

def init_library_module():
    logger.info("📚 [LIBRARY] Módulo de Biblioteca inicializado (v3 - 3 Pilares).")

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
            result_uni = session.run("MATCH (u:Universe {userId: $userId}) RETURN u", userId=user_id)
            data["universes"] = [dict(record["u"]) for record in result_uni]
            
            # 2. Busca Personagens (Agora são globais/templates)
            result_char = session.run("MATCH (c:Character {userId: $userId}) RETURN c", userId=user_id)
            data["characters"] = [dict(record["c"]) for record in result_char]

            # 3. Busca Aventuras
            result_adv = session.run("MATCH (a:Adventure {userId: $userId}) RETURN a", userId=user_id)
            data["adventures"] = [dict(record["a"]) for record in result_adv]
            
        return data
        
    except Exception as e:
        logger.error(f"Erro ao buscar biblioteca: {e}")
        return {"universes": [], "characters": [], "adventures": []}

# --- Rotas de Escrita (POST) ---

@router.post("/universe")
async def save_universe(item: UniverseModel):
    if not graph.driver: raise HTTPException(status_code=503, detail="Database not connected")
    
    cypher = """
    MERGE (u:Universe {id: $id})
    SET u.userId = $userId,
        u.name = $name,
        u.description = $description,
        u.genre = $genre,
        u.image = $image,
        u.createdAt = $createdAt
    RETURN u.id
    """
    try:
        with graph.driver.session() as session:
            session.run(cypher, item.dict())
        return {"status": "success", "id": item.id}
    except Exception as e:
        logger.error(f"Erro ao salvar universo: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/character")
async def save_character(item: CharacterModel):
    if not graph.driver: raise HTTPException(status_code=503, detail="Database not connected")
    
    # Atualizado: Cria personagem sem vínculo com universo (Template)
    cypher = """
    MERGE (c:Character {id: $id})
    SET c.userId = $userId,
        c.name = $name,
        c.description = $description,
        c.archetype = $archetype,
        c.image = $image,
        c.stats = $stats,
        c.createdAt = $createdAt
    RETURN c.id
    """
    try:
        with graph.driver.session() as session:
            session.run(cypher, item.dict())
        return {"status": "success", "id": item.id}
    except Exception as e:
        logger.error(f"Erro ao salvar personagem: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/adventure")
async def save_adventure(item: AdventureModel):
    if not graph.driver: raise HTTPException(status_code=503, detail="Database not connected")
    
    # Atualizado: A Aventura agora é o nó que conecta o Personagem ao Universo
    cypher = """
    MERGE (a:Adventure {id: $id})
    SET a.userId = $userId,
        a.name = $name,
        a.description = $description,
        a.currentStep = $currentStep,
        a.createdAt = $createdAt,
        a.universeId = $universeId,
        a.characterId = $characterId
    
    WITH a
    MATCH (u:Universe {id: $universeId})
    MATCH (c:Character {id: $characterId})
    
    MERGE (a)-[:HAPPENS_IN]->(u)
    MERGE (a)-[:USES_TEMPLATE]->(c)
    
    RETURN a.id
    """
    try:
        with graph.driver.session() as session:
            # exclude={"messages"} pois mensagens não vão pro grafo dessa forma
            session.run(cypher, item.dict(exclude={"messages"}))
        return {"status": "success", "id": item.id}
    except Exception as e:
        logger.error(f"Erro ao salvar aventura: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- Rotas de Deleção (DELETE) ---

@router.delete("/universe/{item_id}")
async def delete_universe(item_id: str, userId: str = Query(...)):
    if not graph.driver: raise HTTPException(status_code=503, detail="Database not connected")
    
    # Deleta universo e suas aventuras, mas PRESERVA os personagens (templates)
    cypher = """
    MATCH (u:Universe {id: $id, userId: $userId})
    OPTIONAL MATCH (a:Adventure {universeId: $id, userId: $userId})
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
    if not graph.driver: raise HTTPException(status_code=503, detail="Database not connected")

    # Deleta o template. (Futuramente: avisar se há aventuras ativas usando ele)
    cypher = """
    MATCH (c:Character {id: $id, userId: $userId})
    DETACH DELETE c
    """
    try:
        with graph.driver.session() as session:
            session.run(cypher, id=item_id, userId=userId)
        return {"status": "deleted", "id": item_id}
    except Exception as e:
        logger.error(f"Erro ao deletar personagem: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/adventure/{item_id}")
async def delete_adventure(item_id: str, userId: str = Query(...)):
    if not graph.driver: raise HTTPException(status_code=503, detail="Database not connected")

    cypher = """
    MATCH (a:Adventure {id: $id, userId: $userId})
    DETACH DELETE a
    """
    try:
        with graph.driver.session() as session:
            session.run(cypher, id=item_id, userId=userId)
        return {"status": "deleted", "id": item_id}
    except Exception as e:
        logger.error(f"Erro ao deletar aventura: {e}")
        raise HTTPException(status_code=500, detail=str(e))