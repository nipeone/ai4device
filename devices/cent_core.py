from typing import Literal, Optional
from datetime import datetime, timedelta
import zmq
import json
import time
import struct

from logger import sys_logger as logger
from .base import SocketControlledDevice, DeviceStatus
from schemas.oven import CurvePoint
from utils import retry_on_failure
import config

from schemas.centrifuge import (
    CentrifugeActionCode, 
    CentrifugeDoorStatus, 
    CentrifugeStatus,
    CentrifugeRotorStatus
)

'''
    [0] 0x01: 功能码（1:写操作，0:读操作）
    [1] 1: Slave ID
    [2] 0x20: 寄存器地址高位
    [3] 0x00: 寄存器地址低位
    [4] 0x00: 操作参数高位
    [5] 0x01: 操作参数低位
'''
CENT_CMDS = {
    "start": bytes([0x01, 1, 0x20, 0x00, 0, 1]),
    "stop": bytes([0x01, 1, 0x20, 0x00, 0, 2]),
    "open": bytes([0x01, 1, 0x20, 0x01, 0, 1]),
    "close": bytes([0x01, 1, 0x20, 0x01, 0, 2]),
    "clear": bytes([0x01, 1, 0x20, 0x02, 0, 1])
}

# 故障和状态映射
CENT_FAULT_MAP = {0: "系统正常", 1: "转子不平衡", 4: "伺服控制器故障", 5: "离心机门未关"}
CENT_RUN_MAP = {0: "状态未知", 1: "已停止", 2: "运行中"}
CENT_ROTOR_MAP = {0: "不定态", 1: "加速中", 2: "恒速运行", 3: "降速中", 4: "定位中"}
CENT_DOOR_MAP = {1: "门窗开启", 2: "门窗关闭"}
CENT_LID_MAP = {1: "门盖开启", 2: "门盖关闭"}

class CentController(SocketControlledDevice):
    """Socket（ZMQ）控制的离心机设备"""

    def __init__(self, 
                device_id: str = "03", 
                sub_addr: str = None,
                req_addr: str = None,
                topic: str = b"Centrifuge"):
        self.REQ_ADDR = req_addr or config.CENTRIFUGE_REQ_ADDR
        self.SUB_ADDR = sub_addr or config.CENTRIFUGE_SUB_ADDR
        self.SUB_TOPIC = topic
        super().__init__("socket_cent_" + device_id, device_id, self.REQ_ADDR)
        self._socket_timeout = 1000  # 设置默认超时时间
        self.cent_status_cache = {}  # 缓存离心机状态
        self.cent_status = CentrifugeStatus.STOPPED
        self.cent_status_time = datetime.now()
        self.cent_status_timeout = 10  # 离心机状态超时时间
        self.realtime_data = {}
        self.status = DeviceStatus.UNKNOWN


    def connect(self):
        """连接ZMQ设备"""

        if self.is_connected:
            return True

        # 短连接模式下不发送未知探测指令，connect仅做逻辑连接
        req_context, req_socket = self._create_socket(zmq.REQ, 1000)
        try:
            
            req_socket.connect(self.REQ_ADDR)
            logger.debug(f"成功连接离心机：{self.REQ_ADDR}")
            
            self.is_connected = True
            self.message = "离心机设备连接成功"
            self.result = {"status": "success", "message": self.message}
            self.status = DeviceStatus.CONNECTED
            return True
        except Exception as e:
            self.is_connected = False
            self.message = f"离心机设备连接失败: {str(e)}"
            self.result = {"status": "error", "message": self.message}
            self.status = DeviceStatus.DISCONNECTED
            return False
        finally:
            if req_socket:
                req_socket.close()
            if req_context:
                req_context.term()

    def disconnect(self):
        """断开ZMQ设备连接"""
        # 清理SUB socket

        # 调用父类方法清理主socket
        super().disconnect()
        self.message = "离心机设备已断开连接"
        self.result = {"status": "success", "message": self.message}
        self.status = DeviceStatus.DISCONNECTED
        return True

    def send_raw_command(self, payload: bytes, timeout_ms=1000) -> bool:
        """
        发送原始命令到离心机
        
        参数:
            payload: 要发送的二进制数据
            timeout_ms: 超时时间(毫秒)
            
        返回:
            bool: 命令是否成功执行
        """
        if not self.is_connected and not self.connect():
            self.message = "离心机设备未连接"
            self.result = {"status": "error", "message": self.message}
            return self.result

        ctx, sock = self._create_socket(zmq.REQ, timeout_ms)
        sock.connect(self.REQ_ADDR)
        
        try:
            sock.send(payload)
            # C# 用 TryReceiveFrameString -> 返回 "True"/"False"
            resp = sock.recv_string()
            if resp == "True":
                self.message = "离心机命令发送成功"
                self.result = {"status": "success", "message": self.message}
                return self.result
            else:
                self.message = "离心机命令发送失败"
                self.result = {"status": "error", "message": self.message}
                return self.result
        except Exception as e:
            self.message = f"发送命令失败: {e}"
            self.result = {"status": "error", "message": f"发送命令失败: {e}"}
            return self.result
        finally:
            sock.close()
            ctx.term()

    def set_parameter(self, cmd_high, cmd_low, value):
        """
        设置离心机参数
        
        参数:
            cmd_high: 命令高位字节
            cmd_low: 命令低位字节
            value: 参数值(0-65535)
            
        返回:
            bool: 操作是否成功
        """
        val_bytes = struct.pack('>H', int(value) & 0xFFFF)
        payload = bytes([0x01, 1, cmd_high, cmd_low]) + val_bytes
        return self.send_raw_command(payload)

    @retry_on_failure(max_retries=3, delay=1.0, status_key="status", success_value="success")
    def start(self):
        """启动离心机"""
        # 启动离心机前需要清除故障码
        self.clear_error()
        return self.send_raw_command(CENT_CMDS["start"])

    @retry_on_failure(max_retries=3, delay=1.0, status_key="status", success_value="success")
    def stop(self):
        """停止离心机"""
        return self.send_raw_command(CENT_CMDS["stop"])

    @retry_on_failure(max_retries=3, delay=1.0, status_key="status", success_value="success")
    def open_door(self):
        """打开离心机门窗"""
        realtime_data = self.get_realtime_data()
        if realtime_data:
            run_state = realtime_data.get("run_state", 0)
            rotor_state = realtime_data.get("rotor_state", 0)

            if run_state == CentrifugeStatus.RUNNING.value or rotor_state in [1, 2, 3]:
                self.message = f"安全拦截: 离心机转子尚未完全静止 (机器状态码:{rotor_state})，严禁开盖！"
                self.result = {"status": "error", "message": self.message}
                return self.result

        return self.send_raw_command(CENT_CMDS["open"])

    @retry_on_failure(max_retries=3, delay=1.0, status_key="status", success_value="success")
    def close_door(self):
        """关闭离心机门窗"""
        return self.send_raw_command(CENT_CMDS["close"])

    @retry_on_failure(max_retries=3, delay=1.0, status_key="status", success_value="success")
    def clear_error(self):
        """清除离心机故障码"""
        return self.send_raw_command(CENT_CMDS["clear"])

    @retry_on_failure(max_retries=3, delay=1.0, status_key="status", success_value="success")
    def control_centrifuge(self, action: CentrifugeActionCode) -> dict:
        """控制离心机"""
        return self.send_raw_command(CENT_CMDS[action.name.lower()])

    @retry_on_failure(max_retries=3, delay=1.0, status_key="status", success_value="success")
    def set_speed(self, rpm: int):
        """设置转速"""
        return self.set_parameter(0x21, 0x01, rpm)

    @retry_on_failure(max_retries=3, delay=1.0, status_key="status", success_value="success")
    def set_time(self, seconds: int):
        """设置时间；单位：秒"""
        return self.set_parameter(0x21, 0x02, seconds)

    def parse_frame(self, data: bytes) -> dict:
        """解析状态数据
        
        - 面板数据
            - 实际运行转速 actual_rpm
            - 剩余时间 remain_time
            - 运行状态 run_state
            - 转子状态 rotor_state
        - 门状态对比
            - 1_门窗状态(2206H) door_window
        - 安全监控
            - 故障状态 fault_code
        - 详细参数
            - 实际运行转速 actual_rpm
            - 实际运行离心力 centrifuge_force
            - 用户设置的转速 setted_rpm
            - 用户设置的时间 setted_time
            - 实际运行时间 run_time
        """

        def u16(hi, lo): return (hi << 8) + lo
        if not data or len(data) < 36:
            return None
        d = {}
        # 实际转子工号
        d['num'] = u16(data[0], data[1])
        # 实际运行转速
        d['actual_rpm'] = u16(data[2], data[3])
        # 实际运行时间
        d['run_time'] = u16(data[4], data[5])
        # 实际运行离心力
        d['centrifuge_force'] = u16(data[34], data[35])
        # 故障码 0 正常 1 转子不平衡 4 伺服控制器故障 5 离心机门窗未关
        d['fault_code'] = u16(data[8], data[9])
        # 运行状态 0 unkown 1 离心机停止, 2 离心机运行
        d['run_state'] = u16(data[10], data[11])
        # 门窗状态 0 unknown, 1 离心机门窗开, 2 离心机门窗关
        d['door_window'] = u16(data[12], data[13])
        # 用户设置的转子工号
        d['setted_num'] = u16(data[14], data[15])
        # 用户设置的转速
        d['setted_rpm'] = u16(data[16], data[17])
        # 用户设置的时间
        d['setted_time'] = u16(data[18], data[19])
        # 门盖状态 1 门盖开, 2 门盖关
        d['door_lid'] = u16(data[22], data[23])
        # 转子状态 0 unkown, 1 加速, 2 恒速, 3 减速, 4 定速
        d['rotor_state'] = u16(data[24], data[25])
        # 剩余时间
        d['remain_time'] = u16(data[26], data[27])

        return d

    def get_status(self) -> DeviceStatus:
        return self.status

    def get_realtime_data(self, duration=10.0):
        """获取实时数据"""
        ctx, sock = self._create_socket(zmq.SUB)
        sock.setsockopt(zmq.SUBSCRIBE, self.SUB_TOPIC)
        sock.connect(self.SUB_ADDR)

        latest_data = None
        try:
            time.sleep(0.1) # 等待连接建立

            start_time = time.time()
            while time.time() - start_time < duration:
                if sock.poll(10):
                    try:
                        parts = sock.recv_multipart(flags=zmq.NOBLOCK)
                        if len(parts) >= 2:
                            topic, payload = parts[0], parts[1]
                            if topic == self.SUB_TOPIC:
                                latest_data = self.parse_frame(payload)
                    except zmq.Again:
                        continue
                    except Exception as e:
                        print(f"离心机实时数据获取失败: {e}")
                        return latest_data
        except Exception as e:
            print(f"离心机实时数据获取失败: {e}")
            return latest_data
        finally:
            sock.close()
            ctx.term()
        self.realtime_data = latest_data
        return latest_data

    @property
    def door_is_closed(self) -> bool:
        """获取离心机门窗状态"""
        realtime_data = self.get_realtime_data()
        if realtime_data:
            return realtime_data.get("door_window") == CentrifugeDoorStatus.CLOSED.value
        else:
            return False

    def get_door_status(self) -> CentrifugeDoorStatus:
        """获取离心机门窗状态"""
        realtime_data = self.get_realtime_data()
        if realtime_data:
            val = realtime_data.get("door_window", 0)
            try:
                return CentrifugeDoorStatus(val)
            except ValueError:
                return CentrifugeDoorStatus.UNKNOWN
        else:
            return CentrifugeDoorStatus.UNKNOWN

    def get_centrifuge_status(self) -> CentrifugeStatus:
        """获取离心机运行状态"""
        realtime_data = self.get_realtime_data()
        if realtime_data:
            val = realtime_data.get("run_state", 0)
            try:
                return CentrifugeStatus(val)
            except ValueError:
                return CentrifugeStatus.UNKNOWN
        else:
            return CentrifugeStatus.UNKNOWN

    def get_running_status(self) -> dict:
        """获取离心机运行状态"""
        realtime_data = self.get_realtime_data()
        if realtime_data:
            return {"status": "success", "data": realtime_data}
        else:
            return {"status": "error", "message": "获取离心机运行状态失败"}

    def get_result(self) -> dict:
        """获取离心机运行状态"""
        realtime_data = self.get_realtime_data()
        if realtime_data:
            self.result = {"status": "success", "data": realtime_data}  
            return self.result
        else:
            self.result = {"status": "error", "message": "获取离心机运行状态失败"}
            return self.result

    def get_message(self) -> str:
        """获取离心机消息"""
        return self.message if self.message else "离心机设备就绪"

# 创建全局实例（保持向后兼容）
cent_controller = CentController()