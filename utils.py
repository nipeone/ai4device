import struct
import time
import json
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, List

# 全局变量定义
CENT_CMDS = {
    "start": bytes([0x01, 0x06, 0x20, 0x00, 0x00, 0x01, 0x43, 0xCA]),
    "stop": bytes([0x01, 0x06, 0x20, 0x00, 0x00, 0x02, 0x03, 0xCB]),
    "open": bytes([0x01, 0x06, 0x20, 0x01, 0x00, 0x01, 0x12, 0x0A]),
    "close": bytes([0x01, 0x06, 0x20, 0x01, 0x00, 0x02, 0x52, 0x0B]),
    "read_all": bytes([0x01, 0x03, 0x22, 0x00, 0x00, 0x0E, 0xCE, 0x76])
}


def cent_format_time(s):
    m, s = divmod(s, 60);
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"


# 故障和状态映射
CENT_FAULT_MAP = {0: "系统正常", 1: "转子不平衡", 4: "伺服控制器故障", 5: "离心机门未关"}
CENT_RUN_MAP = {0: "状态未知", 1: "已停止", 2: "运行中"}
CENT_ROTOR_MAP = {0: "不定态", 1: "加速中", 2: "恒速运行", 3: "降速中", 4: "定位中"}
CENT_DOOR_MAP = {1: "门窗开启", 2: "门窗关闭"}