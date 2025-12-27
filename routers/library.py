import sqlite3
import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional

# [2025-08-01] Sempre coloque os imports no topo do script.

router = APIRouter(prefix="/library", tags=["library"])

LIBRARY_DB_PATH = "./user_library.db"

# --- Inicialização ---
def init_library_module():
    print("📚 [LIBRARY] Inicializando biblioteca do usuário...")
    conn = sqlite3.connect(LIBRARY_DB_PATH)
    cursor = conn.cursor()
    
    # Universos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS universes (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            data_json TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Personagens
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS characters (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            data_json TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Aventuras (Metadados)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS adventures (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            data_json TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

# --- Rotas ---

@router.get("/{user_id}")
async def get_library(user_id: str):
    conn = sqlite3.connect(LIBRARY_DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # Busca Universos
        cursor.execute("SELECT data_json FROM universes WHERE user_id = ?", (user_id,))
        universes = [json.loads(row['data_json']) for row in cursor.fetchall()]
        
        # Busca Personagens
        cursor.execute("SELECT data_json FROM characters WHERE user_id = ?", (user_id,))
        characters = [json.loads(row['data_json']) for row in cursor.fetchall()]
        
        # Busca Aventuras
        cursor.execute("SELECT data_json FROM adventures WHERE user_id = ?", (user_id,))
        adventures = [json.loads(row['data_json']) for row in cursor.fetchall()]
        
        return {
            "universes": universes,
            "characters": characters,
            "adventures": adventures
        }
    finally:
        conn.close()

@router.post("/universe")
async def save_universe(data: Dict[str, Any]):
    user_id = data.get('userId')
    u_id = data.get('id')
    
    conn = sqlite3.connect(LIBRARY_DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO universes (id, user_id, data_json) VALUES (?, ?, ?)",
        (u_id, user_id, json.dumps(data))
    )
    conn.commit()
    conn.close()
    return {"status": "saved"}

@router.post("/character")
async def save_character(data: Dict[str, Any]):
    user_id = data.get('userId')
    c_id = data.get('id')
    
    conn = sqlite3.connect(LIBRARY_DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO characters (id, user_id, data_json) VALUES (?, ?, ?)",
        (c_id, user_id, json.dumps(data))
    )
    conn.commit()
    conn.close()
    return {"status": "saved"}

@router.post("/adventure")
async def save_adventure(data: Dict[str, Any]):
    user_id = data.get('userId')
    a_id = data.get('id')
    
    conn = sqlite3.connect(LIBRARY_DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO adventures (id, user_id, data_json) VALUES (?, ?, ?)",
        (a_id, user_id, json.dumps(data))
    )
    conn.commit()
    conn.close()
    return {"status": "saved"}