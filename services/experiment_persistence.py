"""
实验与 XRD 结果 SQLite 持久化。
- experiments：实验主表（experiment_id、phase、task_name、scheme_manifest、thermal_params、error_message、时间戳）
- xrd_results：XRD 结果表（experiment_id、sample_id、scheme_id、theta2、intensity 等）
- sample_bindings：实验-方案-样品绑定（confirm_xrd_ready 时生成 sample_id 后写入，供补充测试关联）
"""
import json
import os
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional

import config


def _db_path() -> str:
    path = getattr(config, "EXPERIMENT_DB_PATH", "assets/experiment.sqlite")
    return path


def init_experiment_db() -> None:
    """创建实验与 XRD 结果表（若不存在）。"""
    path = _db_path()
    dirname = os.path.dirname(path)
    if dirname and not os.path.isdir(dirname):
        os.makedirs(dirname, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS experiments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                experiment_id TEXT UNIQUE NOT NULL,
                task_name TEXT,
                phase TEXT NOT NULL,
                scheme_manifest TEXT,
                thermal_params TEXT,
                error_message TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS xrd_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                experiment_id TEXT NOT NULL,
                sample_id TEXT,
                scheme_id TEXT,
                scheme_index INTEGER,
                scheme_type TEXT,
                theta2 TEXT,
                intensity TEXT,
                timestamp TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (experiment_id) REFERENCES experiments(experiment_id)
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_xrd_experiment_id ON xrd_results(experiment_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_experiments_created_at ON experiments(created_at DESC)")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sample_bindings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                experiment_id TEXT NOT NULL,
                scheme_id TEXT,
                scheme_index INTEGER,
                sample_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (experiment_id) REFERENCES experiments(experiment_id)
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sample_bindings_experiment_id ON sample_bindings(experiment_id)")


def insert_experiment(
    experiment_id: str,
    task_name: Optional[str] = None,
    scheme_manifest: Optional[List[Dict[str, Any]]] = None,
    thermal_params: Optional[Dict[str, Any]] = None,
) -> None:
    """实验启动时插入一条记录，初始 phase=idle。"""
    now = datetime.utcnow().isoformat() + "Z"
    path = _db_path()
    with sqlite3.connect(path) as conn:
        conn.execute(
            """
            INSERT INTO experiments (experiment_id, task_name, phase, scheme_manifest, thermal_params, error_message, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, NULL, ?, ?)
            """,
            (
                experiment_id,
                task_name or "",
                "idle",
                json.dumps(scheme_manifest, ensure_ascii=False) if scheme_manifest else None,
                json.dumps(thermal_params, ensure_ascii=False, default=str) if thermal_params else None,
                now,
                now,
            ),
        )


def update_experiment_phase(
    experiment_id: str,
    phase: str,
    error_message: Optional[str] = None,
) -> None:
    """更新实验阶段（及可选错误信息）。"""
    now = datetime.utcnow().isoformat() + "Z"
    path = _db_path()
    with sqlite3.connect(path) as conn:
        if error_message is not None:
            conn.execute(
                "UPDATE experiments SET phase = ?, error_message = ?, updated_at = ? WHERE experiment_id = ?",
                (phase, error_message, now, experiment_id),
            )
        else:
            conn.execute(
                "UPDATE experiments SET phase = ?, updated_at = ? WHERE experiment_id = ?",
                (phase, now, experiment_id),
            )


def insert_sample_binding(
    experiment_id: str,
    sample_id: str,
    scheme_id: Optional[str] = None,
    scheme_index: Optional[int] = None,
    scheme_type: Optional[str] = None,
) -> None:
    """confirm_xrd_ready 时生成 sample_id 后写入绑定，便于与 experiment_id/scheme_id 关联及补充测试。"""
    now = datetime.utcnow().isoformat() + "Z"
    path = _db_path()
    with sqlite3.connect(path) as conn:
        conn.execute(
            """
            INSERT INTO sample_bindings (experiment_id, scheme_id, scheme_index, sample_id, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (experiment_id, scheme_id, scheme_index, sample_id, now),
        )


def get_sample_bindings(experiment_id: str) -> List[Dict[str, Any]]:
    """按 experiment_id 查询该实验的样品绑定列表（含补充测试前预绑定的 sample_id）。"""
    path = _db_path()
    with sqlite3.connect(path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT experiment_id, scheme_id, scheme_index, sample_id, created_at FROM sample_bindings WHERE experiment_id = ? ORDER BY id",
            (experiment_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def insert_xrd_results(experiment_id: str, results: List[Dict[str, Any]]) -> None:
    """实验完成时写入 XRD 结果（可多条）。"""
    if not results:
        return
    now = datetime.utcnow().isoformat() + "Z"
    path = _db_path()
    with sqlite3.connect(path) as conn:
        for r in results:
            theta2 = json.dumps(r.get("theta2"), ensure_ascii=False) if r.get("theta2") is not None else None
            intensity = json.dumps(r.get("intensity"), ensure_ascii=False) if r.get("intensity") is not None else None
            conn.execute(
                """
                INSERT INTO xrd_results (experiment_id, sample_id, scheme_id, scheme_index, scheme_type, theta2, intensity, timestamp, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    experiment_id,
                    r.get("sample_id"),
                    r.get("scheme_id"),
                    r.get("scheme_index"),
                    r.get("scheme_type"),
                    theta2,
                    intensity,
                    str(r.get("timestamp")) if r.get("timestamp") is not None else None,
                    now,
                ),
            )


def get_experiment(experiment_id: str) -> Optional[Dict[str, Any]]:
    """按 experiment_id 查询一条实验（含 thermal_params、scheme_manifest 解析）。"""
    path = _db_path()
    with sqlite3.connect(path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT experiment_id, task_name, phase, scheme_manifest, thermal_params, error_message, created_at, updated_at FROM experiments WHERE experiment_id = ?",
            (experiment_id,),
        ).fetchone()
    if not row:
        return None
    d = dict(row)
    if d.get("scheme_manifest"):
        try:
            d["scheme_manifest"] = json.loads(d["scheme_manifest"])
        except Exception:
            pass
    if d.get("thermal_params"):
        try:
            d["thermal_params"] = json.loads(d["thermal_params"])
        except Exception:
            pass
    return d


def get_xrd_results(experiment_id: str) -> List[Dict[str, Any]]:
    """按 experiment_id 查询该实验的全部 XRD 结果。"""
    path = _db_path()
    with sqlite3.connect(path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT experiment_id, sample_id, scheme_id, scheme_index, scheme_type, theta2, intensity, timestamp, created_at FROM xrd_results WHERE experiment_id = ? ORDER BY id",
            (experiment_id,),
        ).fetchall()
    out = []
    for row in rows:
        d = dict(row)
        if d.get("theta2"):
            try:
                d["theta2"] = json.loads(d["theta2"])
            except Exception:
                pass
        if d.get("intensity"):
            try:
                d["intensity"] = json.loads(d["intensity"])
            except Exception:
                pass
        out.append(d)
    return out


def list_experiments(limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    """分页查询实验列表，按创建时间倒序。"""
    path = _db_path()
    with sqlite3.connect(path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT experiment_id, task_name, phase, error_message, created_at, updated_at FROM experiments ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
    return [dict(r) for r in rows]
