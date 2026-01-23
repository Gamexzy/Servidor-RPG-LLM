import logging
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from routers.graph import driver

# Configuração de Logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("library")

router = APIRouter(prefix="/library", tags=["library"])

# --- Models (Compatíveis com o Frontend React) ---
# Usamos camelCase aqui para facilitar o match com o JSON do JavaScript

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
    universeId: str
    name: str
    description: Optional[str] = ""
    archetype: Optional[str] = ""
    image: Optional[str] = ""
    stats: Optional[Dict[str, Any]] = {}
    createdAt: Optional[str] = ""

class AdventureModel(BaseModel):
    id: str
    userId: str
    universeId: str
    name: str
    description: Optional[str] = ""
    currentStep: Optional[str] = ""
    createdAt: Optional[str] = ""
    messages: Optional[List[Any]] = [] 

def init_library_module():
    logger.info("📚 [LIBRARY] Módulo de Biblioteca inicializado.")

# --- Rotas de Leitura (GET) ---

@router.get("/{user_id}")
async def get_user_library(user_id: str):
    """Retorna todos os universos, personagens e aventuras do usuário."""
    if not driver:
        raise HTTPException(status_code=503, detail="Database not connected")
    
    try:
        data = {
            "universes": [],
            "characters": [],
            "adventures": []
        }
        
        with driver.session() as session:
            # 1. Busca Universos
            result_uni = session.run("MATCH (u:Universe {userId: $userId}) RETURN u", userId=user_id)
            data["universes"] = [dict(record["u"]) for record in result_uni]
            
            # 2. Busca Personagens
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
    if not driver: raise HTTPException(status_code=503, detail="Database not connected")
    
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
        with driver.session() as session:
            session.run(cypher, item.dict())
        return {"status": "success", "id": item.id}
    except Exception as e:
        logger.error(f"Erro ao salvar universo: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/character")
async def save_character(item: CharacterModel):
    if not driver: raise HTTPException(status_code=503, detail="Database not connected")
    
    cypher = """
    MERGE (c:Character {id: $id})
    SET c.userId = $userId,
        c.universeId = $universeId,
        c.name = $name,
        c.description = $description,
        c.archetype = $archetype,
        c.image = $image,
        c.stats = $stats,
        c.createdAt = $createdAt
    RETURN c.id
    """
    try:
        with driver.session() as session:
            session.run(cypher, item.dict())
        return {"status": "success", "id": item.id}
    except Exception as e:
        logger.error(f"Erro ao salvar personagem: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/adventure")
async def save_adventure(item: AdventureModel):
    if not driver: raise HTTPException(status_code=503, detail="Database not connected")
    
    # Nota: Não salvamos 'messages' aqui por enquanto para não pesar o nó
    cypher = """
    MERGE (a:Adventure {id: $id})
    SET a.userId = $userId,
        a.universeId = $universeId,
        a.name = $name,
        a.description = $description,
        a.currentStep = $currentStep,
        a.createdAt = $createdAt
    RETURN a.id
    """
    try:
        with driver.session() as session:
            session.run(cypher, item.dict(exclude={"messages"}))
        return {"status": "success", "id": item.id}
    except Exception as e:
        logger.error(f"Erro ao salvar aventura: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- Rotas de Deleção (DELETE) - [ATUALIZADO] ---

@router.delete("/universe/{item_id}")
async def delete_universe(item_id: str, userId: str = Query(...)):
    """
    Deleta um universo e suas aventuras, mas PRESERVA os personagens (apenas desvincula).
    """
    if not driver: raise HTTPException(status_code=503, detail="Database not connected")

    # Atualizado [2025-08-01]:
    # 1. MATCH Universe: Alvo principal.
    # 2. OPTIONAL MATCH Character: Remove a propriedade 'universeId' para desvincular.
    # 3. OPTIONAL MATCH Adventure: Marca para deleção.
    # 4. DETACH DELETE: Apaga Universo e Aventuras, mas não os Personagens.
    
    cypher = """
    MATCH (u:Universe {id: $id, userId: $userId})
    
    // 1. Desvincular Personagens (Remove universeId, mantém o nó)
    OPTIONAL MATCH (c:Character {universeId: $id, userId: $userId})
    REMOVE c.universeId
    
    // 2. Coletar Aventuras para Deletar (junto com o Universo)
    WITH u
    OPTIONAL MATCH (a:Adventure {universeId: $id, userId: $userId})
    
    // 3. Deletar Universo e Aventuras
    DETACH DELETE u, a
    """
    try:
        with driver.session() as session:
            result = session.run(cypher, id=item_id, userId=userId)
            info = result.consume()
            logger.info(f"Universo {item_id} processado. Nós deletados: {info.counters.nodes_deleted}")
                
        return {"status": "deleted", "id": item_id}
    except Exception as e:
        logger.error(f"Erro ao deletar universo: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/character/{item_id}")
async def delete_character(item_id: str, userId: str = Query(...)):
    if not driver: raise HTTPException(status_code=503, detail="Database not connected")

    cypher = """
    MATCH (c:Character {id: $id, userId: $userId})
    DETACH DELETE c
    """
    try:
        with driver.session() as session:
            session.run(cypher, id=item_id, userId=userId)
        return {"status": "deleted", "id": item_id}
    except Exception as e:
        logger.error(f"Erro ao deletar personagem: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/adventure/{item_id}")
async def delete_adventure(item_id: str, userId: str = Query(...)):
    if not driver: raise HTTPException(status_code=503, detail="Database not connected")

    cypher = """
    MATCH (a:Adventure {id: $id, userId: $userId})
    DETACH DELETE a
    """
    try:
        with driver.session() as session:
            session.run(cypher, id=item_id, userId=userId)
        return {"status": "deleted", "id": item_id}
    except Exception as e:
        logger.error(f"Erro ao deletar aventura: {e}")
        raise HTTPException(status_code=500, detail=str(e))