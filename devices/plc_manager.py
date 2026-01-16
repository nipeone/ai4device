import struct
import time
import json
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, List
from snap7 import client
from snap7.type import Area

from logger import sys_logger as logger

# ==========================================
# 0. PLC 部分 (修复连接报错 BUG)
# ==========================================
class PLCManager:
    def __init__(self, ip="192.168.0.205"):
        self.client = None
        self.ip = ip
        self.connected = False
        self.last_conn = 0

    def try_connect(self):
        # 如果已经连接，直接返回
        if self.connected and self.client: return True

        # 限制重连频率，防止报错刷屏 (3秒一次)
        if time.time() - self.last_conn < 3: return False
        self.last_conn = time.time()

        # === 核心逻辑: 每次重连必须重建对象 ===
        # 1. 彻底清理旧对象
        if self.client:
            try:
                self.client.disconnect()
                self.client.destroy()
            except:
                pass
            self.client = None

        # 2. 创建全新实例并尝试连接
        try:
            # logger.log("PLC: 正在尝试建立连接...", "WARN") # 减少日志刷屏
            self.client = client.Client()
            self.client.connect(self.ip, 0, 1, 102)
            self.connected = self.client.get_connected()
            if self.connected:
                logger.log("PLC: 连接恢复成功！", "SUCCESS")
        except Exception as e:
            self.connected = False
            logger.log(f"PLC: 连接失败 - {e}", "ERROR") # 减少日志刷屏
            try:
                if self.client: self.client.destroy()
            except:
                pass
            self.client = None

        return self.connected

    def read_m(self, b, i):
        if not self.connected or not self.client: return False
        try:
            return bool((self.client.read_area(Area.MK, 0, b, 1)[0] >> i) & 1)
        except:
            self.connected = False
            return False

    def toggle_m(self, b, i):
        """切换状态: 0->1 或 1->0 (保持模式)"""
        if not self.try_connect():
            # logger.log("PLC: 操作失败，未连接", "ERROR")
            return False
        try:
            d = self.client.read_area(Area.MK, 0, b, 1)
            v = bytearray(d)
            if (v[0] >> i) & 1:
                v[0] &= ~(1 << i)
            else:
                v[0] |= (1 << i)
            self.client.write_area(Area.MK, 0, b, v)
            # logger.log(f"PLC: 切换M{b}.{i} 成功", "INFO")
            return True
        except Exception as e:
            self.connected = False
            # logger.log(f"PLC: 切换M{b}.{i} 失败 - {e}", "ERROR")
            return False

    def pulse_m(self, b, i):
        """【新增】点动控制: 置位1 -> 等待0.5s -> 复位0 (安全模式)"""
        # 必须确保连接
        if not self.try_connect():
            # logger.log("PLC: 点动失败，未连接", "ERROR")
            return False

        try:
            # 1. 置位 (ON)
            d = self.client.read_area(Area.MK, 0, b, 1)
            v = bytearray(d)
            v[0] |= (1 << i)
            self.client.write_area(Area.MK, 0, b, v)

            # 2. 延时
            time.sleep(0.5)

            # 3. 复位 (OFF)
            d = self.client.read_area(Area.MK, 0, b, 1)
            v = bytearray(d)
            v[0] &= ~(1 << i)
            self.client.write_area(Area.MK, 0, b, v)
            # logger.log(f"PLC: 点动M{b}.{i} 完成", "INFO")
            return True
        except Exception as e:
            self.connected = False
            # logger.log(f"PLC: 点动M{b}.{i} 异常中断 - {e}", "ERROR")
            return False

    def write_task(self, tid, st, qty):
        if not self.try_connect():
            # logger.log("PLC: 写入任务失败，未连接", "ERROR")
            return False
        try:
            # 设置数据 (tid任务id/st站点/qty生产数量)
            self.client.write_area(Area.DB, 3, 0, int(tid).to_bytes(2, 'big'))
            self.client.write_area(Area.DB, 3, 2, int(st).to_bytes(2, 'big'))
            self.client.write_area(Area.DB, 3, 4, int(qty).to_bytes(2, 'big'))
            # logger.log(f"PLC: 任务数据写入成功 (ID:{tid}, ST:{st}, Qty:{qty})", "INFO")
            return True
        except Exception as e:
            self.connected = False
            # logger.log(f"PLC: 写入任务异常 - {e}", "ERROR")
            return False

    def read_db_bit(self, db, byte, bit):
        if not self.connected or not self.client: return False
        try:
            d = self.client.read_area(Area.DB, db, byte, 1)
            return bool((d[0] >> bit) & 1)
        except:
            self.connected = False
            return False

    def read_db_int(self, db, byte, size=2):
        if not self.connected or not self.client: return 0
        try:
            d = self.client.read_area(Area.DB, db, byte, size)
            return int.from_bytes(d, 'big')
        except:
            self.connected = False  # 读取失败标记断线
            return 0
        
plc_mgr = PLCManager()