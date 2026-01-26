import struct
import time
import json
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, List
import sqlite3
import os

import config

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
        os.makedirs(os.path.dirname(config.FURNACE_DB_PATH))
        with sqlite3.connect(config.FURNACE_DB_PATH) as conn:
            conn.execute('''CREATE TABLE IF NOT EXISTS saved_curves (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                curve_name TEXT NOT NULL,
                slave_id INTEGER,
                points_json TEXT, 
                save_time DATETIME DEFAULT CURRENT_TIMESTAMP)''')