import struct
import time
import json
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, List
import sqlite3
import os
import time
from functools import wraps
from typing import Callable, Dict, Any
from logger import sys_logger as logger

import config

def generate_unit_id():
    time.sleep(0.001)
    return f"unit-{hex(int(time.time() * 1000))[2:]}" 

def cent_format_time(s):
    '''格式化时间'''
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"

def cent_get_value(data, i):
    '''获取数据'''
    return struct.unpack('>H', bytes(data[3 + i * 2:3 + i * 2 + 2]))[0]

def initialize_oven_curve_db():
    """初始化数据库表结构"""
    if not os.path.exists(config.FURNACE_DB_PATH):
        os.makedirs(os.path.dirname(config.FURNACE_DB_PATH), exist_ok=True)
        try:
            with sqlite3.connect(config.FURNACE_DB_PATH) as conn:
                conn.execute('''CREATE TABLE IF NOT EXISTS saved_curves (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    curve_name TEXT NOT NULL,
                    slave_id INTEGER,
                    points_json TEXT, 
                    save_time DATETIME DEFAULT CURRENT_TIMESTAMP)''')
        except Exception as e:
            logger.error(f"初始化炉子运行曲线数据库表结构失败: {str(e)}")

def retry_on_failure(
    max_retries: int = 2,
    delay: float = 0.5,
    status_key: str = "status",
    success_value: str = "success",
    log_func: Callable[[str, str], None] = None,  # 接收 (msg, level)
):
    """
    装饰器：对返回 dict 的函数进行重试，直到成功或达到最大重试次数。
    
    :param max_retries: 最大重试次数（总调用次数 = 1 + max_retries）
    :param delay: 每次重试前的延迟（秒）
    :param status_key: 判断是否成功的字段名
    :param success_value: 成功时该字段的值
    :param log_func: 日志记录函数，签名为 log_func(message: str, level: str)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Dict[str, Any]:
            last_result = None
            for attempt in range(max_retries + 1):
                result = func(*args, **kwargs)
                last_result = result

                if isinstance(result, dict) and result.get(status_key) == success_value:
                    return result

                if isinstance(result, bool) and result:
                    return result

                # 非最后一次尝试，记录警告并重试
                if attempt < max_retries:
                    msg = f"{func.__name__} 第 {attempt + 1} 次失败: {result.get('message', 'Unknown error')}"
                    if log_func:
                        log_func(msg, "WARNING")
                    time.sleep(delay)
                else:
                    # 最后一次失败
                    msg = f"{func.__name__} 重试 {max_retries} 次后仍失败: {result.get('message', 'Unknown error')}"
                    if log_func:
                        log_func(msg, "ERROR")

            # 返回最终失败结果（也可包装为统一格式）
            if isinstance(last_result, dict):
                return {
                    "status": last_result.get(status_key),
                    "message": f"{func.__name__} failed after {max_retries} retries: {last_result.get('message', 'Unknown')}"
                }
            else:
                return False
        return wrapper
    return decorator