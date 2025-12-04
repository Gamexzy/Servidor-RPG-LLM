import sqlite3
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any

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
    # Cria tabela de exemplo (Player) se não existir
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS player (
            id TEXT PRIMARY KEY, 
            name TEXT, 
            status TEXT, 
            location TEXT, 
            inventory TEXT
        )
    ''')
    conn.commit()
    conn.close()
    print("✅ [STATE] SQLite pronto.")

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
        # Tenta UPDATE
        cols_set = ", ".join([f"{k} = ?" for k in req.data.keys()])
        values = list(req.data.values())
        values.append(req.condition_id)
        
        sql_update = f"UPDATE {req.table} SET {cols_set} WHERE id = ?"
        cursor.execute(sql_update, values)
        
        # Se nada mudou, faz INSERT
        if cursor.rowcount == 0:
            # Prepara dados para insert (incluindo o ID da condição)
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