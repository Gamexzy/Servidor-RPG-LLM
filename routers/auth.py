from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# [2025-08-01] Sempre coloque os imports no topo do script.

router = APIRouter(prefix="/auth", tags=["auth"])

class AuthRequest(BaseModel):
    username: str
    password: str
    email: str = None

@router.post("/login")
async def login(req: AuthRequest):
    # Mock de login - aceita qualquer usuário por enquanto
    print(f"🔑 [AUTH] Login solicitado: {req.username}")
    return {
        "userId": f"user_{req.username}",
        "token": "mock-jwt-token-123",
        "username": req.username
    }

@router.post("/register")
async def register(req: AuthRequest):
    print(f"📝 [AUTH] Registro solicitado: {req.username}")
    return {
        "userId": f"user_{req.username}",
        "status": "created"
    }