from devices.oven_core import oven_controller
from schemas.oven import OvenCurveRequest, CurvePoint, OvenCurveListItem
import sqlite3
import config
import json

from logger import sys_logger as logger


class OvenService:
    def __init__(self):
        pass

    def persist_oven_curve(self, oven_id: int, curve_name: str, points: list[CurvePoint]):
        try:
            with sqlite3.connect(config.FURNACE_DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO saved_curves (oven_id, curve_name, points_json) VALUES (?, ?, ?)", 
                (oven_id, curve_name, json.dumps([p.model_dump() for p in points])))
                conn.commit()
            logger.info(f"炉子{oven_id}运行曲线保存成功")
            return True
        except Exception as e:
            logger.error(f"炉子{oven_id}运行曲线保存失败: {str(e)}")
            return False

    def get_oven_curve_by_oven_id(self, oven_id: int) -> list[CurvePoint]:
        try:
            with sqlite3.connect(config.FURNACE_DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT points_json FROM saved_curves WHERE oven_id = ?", (oven_id,))
                row = cursor.fetchone()
                points_list = json.loads(row[0])
                return [CurvePoint(**p) for p in json.loads(points_list)]
        except Exception as e:
            logger.error(f"炉子{oven_id}运行曲线获取失败: {str(e)}")
            return []

    def get_oven_curve_by_name(self, curve_name: str) -> list[CurvePoint]:
        try:
            with sqlite3.connect(config.FURNACE_DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT points_json FROM saved_curves WHERE curve_name = ?", (curve_name,))
                row = cursor.fetchone()
                points_list = json.loads(row[0])
                return [CurvePoint(**p) for p in json.loads(points_list)]
        except Exception as e:
            logger.error(f"炉子{curve_name}运行曲线获取失败: {str(e)}")
            return []

    def get_oven_curve_list(self) -> list[OvenCurveListItem]:
        try:
            with sqlite3.connect(config.FURNACE_DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, curve_name, save_time FROM saved_curves ORDER BY save_time DESC")
                rows =  cursor.fetchall()
                return [OvenCurveListItem(id=row[0], curve_name=row[1], save_time=row[2]) for row in rows]
        except Exception as e:
            logger.error(f"炉子运行曲线列表获取失败: {str(e)}")
            return []

oven_service = OvenService()