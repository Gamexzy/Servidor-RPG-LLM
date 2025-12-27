import sqlite3
import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any

# [2025-08-01] Sempre coloque os imports no topo do script.

router = APIRouter(prefix="/state", tags=["state"])

SQLITE_PATH = "./world_state.db"

# --- Models ---
class StateUpdate(BaseModel):
    table: str
    data: Dict[str, Any]
    condition_id: str

# --- Inicialização ---
def init_state_module():
    print("📊 [STATE] Verificando banco de dados SQLite...")
    conn = sqlite3.connect(SQLITE_PATH)
    cursor = conn.cursor()
    
    # Tabela de Player (Legado/Simples)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS player (
            id TEXT PRIMARY KEY, 
            name TEXT, 
            status TEXT, 
            location TEXT, 
            inventory TEXT
        )
    ''')
    
    # Tabela de Logs de Turnos (Novo)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS turn_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            universe_id TEXT,
            turn_id INTEGER,
            data_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ [STATE] SQLite pronto.")

# --- Funções Internas ---

async def internal_log_turn(user_id: str, universe_id: str, turn_id: int, data: Dict[str, Any]):
    conn = sqlite3.connect(SQLITE_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO turn_logs (user_id, universe_id, turn_id, data_json) VALUES (?, ?, ?, ?)",
            (user_id, universe_id, turn_id, json.dumps(data))
        )
        conn.commit()
        print(f"📊 [STATE] Log do turno {turn_id} salvo.")
    except Exception as e:
        print(f"❌ [STATE] Erro ao salvar log: {e}")
        raise e
    finally:
        conn.close()

# --- Rotas ---

@router.get("/player/{player_id}")
async def get_player_state(player_id: str):
    conn = sqlite3.connect(SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM player WHERE id = ?", (player_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return {}

@router.post("/update")
async def update_state(req: StateUpdate):
    """Upsert genérico (Atualiza se existe, insere se não)."""
    conn = sqlite3.connect(SQLITE_PATH)
    cursor = conn.cursor()
    
    try:
        cols_set = ", ".join([f"{k} = ?" for k in req.data.keys()])
        values = list(req.data.values())
        values.append(req.condition_id)
        
        sql_update = f"UPDATE {req.table} SET {cols_set} WHERE id = ?"
        cursor.execute(sql_update, values)
        
        if cursor.rowcount == 0:
            insert_data = req.data.copy()
            if 'id' not in insert_data:
                insert_data['id'] = req.condition_id
                
            cols_ins = ", ".join(insert_data.keys())
            placeholders = ", ".join(["?" for _ in insert_data])
            vals_ins = list(insert_data.values())
            
            sql_ins = f"INSERT INTO {req.table} ({cols_ins}) VALUES ({placeholders})"
            cursor.execute(sql_ins, vals_ins)
            
        conn.commit()
        print(f"📊 [STATE] '{req.table}' atualizada para ID {req.condition_id}.")
        return {"status": "success"}
    except Exception as e:
        print(f"❌ [STATE] Erro SQL: {e}")
        raise HTTPException(500, str(e))
    finally:
        conn.close()