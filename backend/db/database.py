import sqlite3
from typing import Any, Dict, List, Optional
from config import DB_PATH

def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def fetch_one(sql: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(sql, params)
        row = cur.fetchone()
        return dict(row) if row else None

def fetch_all(sql: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(sql, params)
        rows = cur.fetchall()
        return [dict(r) for r in rows]
