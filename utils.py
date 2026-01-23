import struct
import time
import json
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, List

def cent_format_time(s):
    '''格式化时间'''
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"

def cent_get_value(data, i):
    '''获取数据'''
    return struct.unpack('>H', bytes(data[3 + i * 2:3 + i * 2 + 2]))[0]