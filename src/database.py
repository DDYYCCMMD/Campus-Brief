"""
database.py — SQLite 持久化层
保存用户生成的 Action Card 历史记录
"""

import sqlite3
import json
import os
from datetime import datetime

_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
os.makedirs(_DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(_DATA_DIR, "campusbrief.db")


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """初始化数据库表"""
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                input_preview TEXT  NOT NULL,
                task_type     TEXT  NOT NULL,
                result_json   TEXT  NOT NULL,
                created_at    TEXT  NOT NULL
            )
        """)
        conn.commit()


def save_result(input_text: str, task_type: str, result: dict) -> int:
    """保存一条生成记录，返回 id"""
    preview = (input_text[:120] + "...") if len(input_text) > 120 else input_text
    preview = preview.replace("\n", " ").strip()
    with _connect() as conn:
        cursor = conn.execute(
            "INSERT INTO history (input_preview, task_type, result_json, created_at) VALUES (?, ?, ?, ?)",
            (preview, task_type, json.dumps(result, ensure_ascii=False), datetime.now().strftime("%Y-%m-%d %H:%M")),
        )
        conn.commit()
        return cursor.lastrowid


def get_history(limit: int = 50) -> list:
    """获取最近的历史记录（不含完整 result_json）"""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, input_preview, task_type, created_at FROM history ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_record(record_id: int) -> dict | None:
    """获取单条完整记录"""
    with _connect() as conn:
        row = conn.execute("SELECT * FROM history WHERE id = ?", (record_id,)).fetchone()
        if not row:
            return None
        d = dict(row)
        try:
            d["result"] = json.loads(d.pop("result_json"))
        except (json.JSONDecodeError, TypeError):
            d["result"] = {"error": "Corrupted record", "task_type": "notice"}
        return d


def delete_record(record_id: int):
    """删除一条记录"""
    with _connect() as conn:
        conn.execute("DELETE FROM history WHERE id = ?", (record_id,))
        conn.commit()


def clear_history():
    """清空全部历史"""
    with _connect() as conn:
        conn.execute("DELETE FROM history")
        conn.commit()
