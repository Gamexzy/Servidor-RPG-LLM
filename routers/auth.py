import logging
import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from routers.graph import driver

# [2025-08-01] Sempre coloque os imports no topo do script.

# Configuração de Logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("auth")

router = APIRouter(prefix="/auth", tags=["auth"])

class AuthRequest(BaseModel):
    username: str
    password: str
    email: str = None

@router.post("/login")
async def login(req: AuthRequest):
    if not driver:
        raise HTTPException(status_code=503, detail="Database not connected")

    print(f"🔑 [AUTH] Login solicitado: {req.username}")
    
    # Busca o usuário pelo nome exato
    cypher = """
    MATCH (u:User {username: $username})
    RETURN u.userId as userId, u.password as password, u.username as username
    """
    
    try:
        with driver.session() as session:
            result = session.run(cypher, username=req.username)
            record = result.single()
            
            if not record:
                raise HTTPException(status_code=401, detail="Usuário não encontrado")
            
            # Verificação de senha
            # OBS: Para produção, use hash (bcrypt/argon2) em vez de texto puro
            stored_password = record["password"]
            if stored_password != req.password:
                raise HTTPException(status_code=401, detail="Senha incorreta")
            
            # Login Sucesso
            logger.info(f"Usuário logado: {req.username}")
            return {
                "userId": record["userId"],
                "token": f"mock-jwt-token-{record['userId']}", # Placeholder para JWT futuro
                "username": record["username"]
            }
            
    except Exception as e:
        logger.error(f"Erro no login: {e}")
        # Se já for HTTPException, relança
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail="Erro interno no servidor")

@router.post("/register")
async def register(req: AuthRequest):
    if not driver:
        raise HTTPException(status_code=503, detail="Database not connected")

    print(f"📝 [AUTH] Registro solicitado: {req.username}")
    
    # Gera um ID único para o novo usuário
    new_user_id = str(uuid.uuid4())
    
    check_cypher = "MATCH (u:User {username: $username}) RETURN u"
    
    create_cypher = """
    CREATE (u:User {
        userId: $userId,
        username: $username,
        password: $password,
        email: $email,
        createdAt: datetime()
    })
    RETURN u.userId as userId
    """
    
    try:
        with driver.session() as session:
            # 1. Verifica se usuário já existe
            if session.run(check_cypher, username=req.username).single():
                raise HTTPException(status_code=400, detail="Nome de usuário já existe")
            
            # 2. Cria novo usuário no Neo4j
            session.run(create_cypher, {
                "userId": new_user_id,
                "username": req.username,
                "password": req.password, # Armazenando simples por enquanto (protótipo)
                "email": req.email or ""
            })
            
            logger.info(f"Usuário criado com sucesso: {req.username} ({new_user_id})")
            
            return {
                "userId": new_user_id,
                "status": "created",
                "message": "Usuário registrado com sucesso"
            }
            
    except Exception as e:
        logger.error(f"Erro no registro: {e}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))