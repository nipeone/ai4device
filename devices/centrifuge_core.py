import socket
import struct
import binascii
import time
from typing import Literal
from .base import ModbusControlledDevice, DeviceStatus
import config
from utils import (
    cent_format_time, 
    cent_get_value,
    retry_on_failure
)
from schemas.centrifuge import CentrifugeActionCode, CentrifugeDoorStatus, CentrifugeStatus

# 全局变量定义
CENT_CMDS = {
    "start": bytes([0x01, 0x06, 0x20, 0x00, 0x00, 0x01, 0x43, 0xCA]),
    "stop": bytes([0x01, 0x06, 0x20, 0x00, 0x00, 0x02, 0x03, 0xCB]),
    "open": bytes([0x01, 0x06, 0x20, 0x01, 0x00, 0x01, 0x12, 0x0A]),
    "close": bytes([0x01, 0x06, 0x20, 0x01, 0x00, 0x02, 0x52, 0x0B]),
    "read_all": bytes([0x01, 0x03, 0x22, 0x00, 0x00, 0x0E, 0xCE, 0x76])
}

# 故障和状态映射
CENT_FAULT_MAP = {0: "系统正常", 1: "转子不平衡", 4: "伺服控制器故障", 5: "离心机门未关"}
CENT_RUN_MAP = {0: "状态未知", 1: "已停止", 2: "运行中"}
CENT_ROTOR_MAP = {0: "不定态", 1: "加速中", 2: "恒速运行", 3: "降速中", 4: "定位中"}
CENT_DOOR_MAP = {1: "门窗开启", 2: "门窗关闭"}
CENT_LID_MAP = {1: "门盖开启", 2: "门盖关闭"}

class CentrifugeController(ModbusControlledDevice):
    """Modbus控制的离心机设备"""
    
    def __init__(self, device_id: str = "01", host: str = None, port: int = None, timeout: int = None):
        # 从环境变量获取配置，如果没有提供参数则使用默认值
        host = host or config.CENTRIFUGE_HOST
        port = port or config.CENTRIFUGE_PORT
        timeout = timeout or config.CENTRIFUGE_TIMEOUT
        super().__init__("modbus_centrifuge_" + device_id, device_id, host, port)
        self.timeout = timeout
        self.sock = None

    def _calculate_crc(self, data):
        """计算Modbus CRC校验码"""
        crc = 0xFFFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x0001:
                    crc >>= 1
                    crc ^= 0xA001
                else:
                    crc >>= 1
        return struct.pack('<H', crc)

    def build_write_command(self, address, value):
        """
        自动生成写入指令
        address: 寄存器地址 (比如设置转速是 0x2101)
        value: 要设置的值 (比如 1500)
        """
        # 协议格式：地址(1B) + 功能码06(1B) + 寄存器地址(2B) + 数据(2B)
        # 离心机地址是 0x01
        cmd_part = struct.pack('>BBHH', 0x01, 0x06, address, value)
        crc = self._calculate_crc(cmd_part)
        return cmd_part + crc

    def send_raw(self, hex_cmd):
        """发送原始Modbus命令并接收响应（短连接模式，防止 WinError 10053）"""
        # 每次调用重新建立连接
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)

        try:
            # 连接设备
            sock.connect((self.modbus_addr, self.modbus_port))
            
            # 清空缓冲区（防止读到脏数据）
            sock.settimeout(0.1)
            try:
                while sock.recv(1024):
                    pass
            except:
                pass
            sock.settimeout(self.timeout)

            # 发送指令
            sock.sendall(hex_cmd)

            # 接收数据
            buffer = b''
            start_time = time.time()
            expected_header = b'\x01\x03\x1C'
            is_read_cmd = (hex_cmd[1] == 0x03)
            
            while time.time() - start_time < 6:
                try:
                    chunk = sock.recv(1024)
                    if not chunk:
                        break
                    buffer += chunk
                    
                    if is_read_cmd:
                        start_idx = buffer.find(expected_header)
                        if start_idx != -1:
                            buffer = buffer[start_idx:]
                            if len(buffer) >= 33:
                                valid_frame = buffer[:33]
                                response_hex = binascii.hexlify(valid_frame).decode('utf-8')
                                self.result = {"status": "success", "hex": response_hex, "bytes": list(valid_frame)}
                                return self.result
                        else:
                            if len(buffer) > 100:
                                buffer = buffer[-20:]
                    else:
                        if len(buffer) >= 8 and buffer.startswith(b'\x01\x06'):
                            valid_frame = buffer[:8]
                            response_hex = binascii.hexlify(valid_frame).decode('utf-8')
                            self.result = {"status": "success", "hex": response_hex, "bytes": list(valid_frame)}
                            return self.result
                            
                except socket.timeout:
                    break
            
            self.result = {
                "status": "error",
                "message": f"数据对齐失败，缓冲区: {binascii.hexlify(buffer).decode('utf-8')}"
            }
            return self.result

        except Exception as e:
            self.result = {"status": "error", "message": f"通信异常: {str(e)}"}
            return self.result

        finally:
            # 核心修复点：无论成功失败，每次通信结束后必须彻底关闭 Socket
            sock.close()

    def connect(self):
        """测试连接Modbus设备"""
        # 由于改用短连接，这里只需要发一条测试指令即可验证连通性
        test_result = self.send_raw(CENT_CMDS['read_all'])
        if test_result.get("status") == "success":
            self.is_connected = True
            self.message = "离心机连接成功"
            self.status = DeviceStatus.CONNECTED
            return True
        else:
            self.is_connected = False
            self.message = f"离心机连接失败: {test_result.get('message', '未知错误')}"
            self.status = DeviceStatus.DISCONNECTED
            return False

    def disconnect(self):
        """断开Modbus设备连接"""

        if self.sock:
            self.sock.close()
            self.sock = None
        self.is_connected = False
        self.message = "离心机已断开连接"
        self.status = DeviceStatus.DISCONNECTED

    @retry_on_failure(max_retries=3, delay=1.0, status_key="status", success_value="success")
    def start(self):
        """启动离心机"""
        #if not self.is_connected:
        #    self.message = "设备未连接"
        #    self.result = {"status": "error", "message": "设备未连接"}
        #    self.status = DeviceStatus.DISCONNECTED
        #    return self.result
        
        result = self.send_raw(CENT_CMDS['start'])
        if result.get("status") == "success":
            self.message = "离心机启动成功"
            self.result = {"status": "success", "message": "启动成功"}
            self.status = DeviceStatus.RUNNING
            return self.result
        else:
            self.message = f"启动失败: {result.get('message', '未知错误')}"
            self.result = {"status": "error", "message": result.get('message', '未知错误')}
            self.status = DeviceStatus.ERROR
            return self.result

    @retry_on_failure(max_retries=3, delay=1.0, status_key="status", success_value="success")
    def stop(self):
        """停止离心机"""
        #if not self.is_connected:
        #    self.message = "设备未连接"
        #    self.result = {"status": "error", "message": "设备未连接"}
        #    self.status = DeviceStatus.DISCONNECTED
        #    return self.result
        
        result = self.send_raw(CENT_CMDS['stop'])
        if result.get("status") == "success":
            self.message = "离心机停止成功"
            self.result = {"status": "success", "message": "停止成功"}
            self.status = DeviceStatus.STOPPED
            return self.result
        else:
            self.message = f"停止失败: {result.get('message', '未知错误')}"
            self.result = {"status": "error", "message": result.get('message', '未知错误')}
            self.status = DeviceStatus.ERROR
            return self.result

    @retry_on_failure(max_retries=3, delay=1.0, status_key="status", success_value="success")
    def open_door(self):
        """打开离心机门"""
        #if not self.is_connected:
        #    self.result = {"status": "error", "message": "设备未连接"}
        #    self.status = DeviceStatus.DISCONNECTED
        #    return self.result
        result = self.send_raw(CENT_CMDS['open'])
        if result.get("status") == "success":
            self.message = "离心机门打开成功"
            self.result = {"status": "success", "message": "打开成功"}
            return self.result
        else:
            self.message = f"打开失败: {result.get('message', '未知错误')}"
            self.result = {"status": "error", "message": result.get('message', '未知错误')}
            self.status = DeviceStatus.ERROR
            return self.result

    @retry_on_failure(max_retries=3, delay=1.0, status_key="status", success_value="success")
    def close_door(self):
        """关闭离心机门"""
        #if not self.is_connected:
        #    self.result = {"status": "error", "message": "设备未连接"}
        #    self.status = DeviceStatus.DISCONNECTED
        #    return self.result
        result = self.send_raw(CENT_CMDS['close'])
        if result.get("status") == "success":
            self.message = "离心机门关闭成功"
            self.result = {"status": "success", "message": "关闭成功"}
            return self.result
        else:
            self.message = f"关闭失败: {result.get('message', '未知错误')}"
            self.result = {"status": "error", "message": result.get('message', '未知错误')}
            self.status = DeviceStatus.ERROR
            return self.result

    @retry_on_failure(max_retries=3, delay=1.0, status_key="status", success_value="success")
    def control_centrifuge(self, action: CentrifugeActionCode) -> dict:
        """控制离心机"""
        #if not self.is_connected:
        #    self.result = {"status": "error", "message": "设备未连接"}
        #    self.status = DeviceStatus.DISCONNECTED
        #    return self.result
        
        result = self.send_raw(CENT_CMDS[action.name.lower()])
        if result.get("status") == "success":
            self.message = f"离心机{action}操作成功"
            self.result = {"status": "success", "message": f"操作成功"}
            return self.result
        else:
            self.message = f"离心机{action}操作失败: {result.get('message', '未知错误')}"
            self.result = {"status": "error", "message": result.get('message', '未知错误')}
            self.status = DeviceStatus.ERROR
            return self.result

    @retry_on_failure(max_retries=3, delay=1.0, status_key="status", success_value="success")
    def set_speed(self, rpm: int):
        """设置转速"""
        #if not self.is_connected:
        #    self.result = {"status": "error", "message": "设备未连接"}
        #    self.status = DeviceStatus.DISCONNECTED
        #    return self.result
        result = self.send_raw(self.build_write_command(0x2101, rpm))
        if result.get("status") == "success":
            self.message = f"设置转速成功: {rpm} RPM"
            self.result = {"status": "success", "message": f"设置转速成功: {rpm} RPM"}
            self.status = DeviceStatus.RUNNING
            return self.result
        else:
            self.message = f"设置转速失败: {result.get('message', '未知错误')}"
            self.result = {"status": "error", "message": result.get('message', '未知错误')}
            self.status = DeviceStatus.ERROR
            return self.result

    @retry_on_failure(max_retries=3, delay=1.0, status_key="status", success_value="success")
    def set_time(self, time: int):
        """设置时间，单位：秒"""
        #if not self.is_connected:
        #    self.result = {"status": "error", "message": "设备未连接"}
        #    self.status = DeviceStatus.DISCONNECTED
        #    return self.result
        result = self.send_raw(self.build_write_command(0x2102, time))
        if result.get("status") == "success":
            self.message = f"设置时间成功: {time} 秒"
            self.result = {"status": "success", "message": f"设置时间成功: {time} 秒"}
            self.status = DeviceStatus.RUNNING
            return self.result
        else:
            self.message = f"设置时间失败: {result.get('message', '未知错误')}"
            self.result = {"status": "error", "message": result.get('message', '未知错误')}
            self.status = DeviceStatus.ERROR
            return self.result

    def _parse_status_data(self, data_bytes):
        """解析状态数据
        
        - 面板数据
            - 当前转速 actual_rpm
            - 剩余时间 remain_time
            - 运行状态 run_state
            - 机器状态文字 rotor_state
        - 门状态对比
            - 1_门窗状态(2206H) door_window
        - 安全监控
            - 故障状态 fault_code
            - 最终判定安全 safe_status
        - 详细参数
            - 实际转速_raw actual_rpm
            - 实际离心力 centrifuge_force
            - 设置转速 setted_rpm
            - 设置时间 setted_time
            - 运行时间 run_time
        """
        # 当前转速
        actual_rpm = cent_get_value(data_bytes, 1)
        # 离心力
        centrifuge_force = cent_get_value(data_bytes, 2)
        # 运行时间
        run_time = cent_get_value(data_bytes, 3)
        # 故障码
        fault_code = cent_get_value(data_bytes, 4)
        # 运行状态 0 unkown 1 stopped, 2 running
        run_state = cent_get_value(data_bytes, 5)
        # 门窗状态 0 unknown, 1 opened, 2 closed
        door_window = cent_get_value(data_bytes, 6)
        # 设置转速
        setted_rpm = cent_get_value(data_bytes, 8)
        # 设置时间
        setted_time = cent_get_value(data_bytes, 9)
        # 门盖状态
        door_lid = cent_get_value(data_bytes, 11)
        # 机器状态
        rotor_state = cent_get_value(data_bytes, 12)
        # 剩余时间
        remain_time = cent_get_value(data_bytes, 13)

        return {
            "actual_rpm": actual_rpm,
            "centrifuge_force": centrifuge_force,
            "run_time": run_time,
            "fault_code": fault_code,
            "run_state": run_state,
            "door_window": door_window,
            "setted_rpm": setted_rpm,
            "setted_time": setted_time,
            "door_lid": door_lid,
            "rotor_state": rotor_state,
            "remain_time": remain_time
        }

    def get_status(self) -> DeviceStatus:
        """获取设备状态信息"""
        return self.status


    @property
    def door_is_closed(self) -> bool:
        ''''获取离心机门窗状态

        door_window
            - 0 开关过程中的中间状态
            - 1 打开
            - 2 关闭

        :return: True open, False close
        '''
        status = self.get_running_status()
        if status.get("status") == "success":
            return status.get("data")["door_window"] == CentrifugeDoorStatus.CLOSED.value
        else:
            return False

    def get_door_status(self) -> CentrifugeDoorStatus:
        """获取离心机门窗状态"""
        status = self.get_running_status()
        if status.get("status") == "success":
            val = status.get("data").get("door_window", 0)
            try:
                # 尝试安全转换
                return CentrifugeDoorStatus(val)
            except ValueError:
                # 如果遇到 15552 这种非标数值，当作"未知/中间状态"处理，防止崩溃
                return CentrifugeDoorStatus.UNKNOWN
        else:
            return CentrifugeDoorStatus.UNKNOWN

    def get_centrifuge_status(self) -> CentrifugeStatus:
        """获取离心机运行状态"""
        status = self.get_running_status()
        if status.get("status") == "success":
            val = status.get("data").get("run_state", 0)
            try:
                # 尝试安全转换
                return CentrifugeStatus(val)
            except ValueError:
                # 同样防护运行状态
                return CentrifugeStatus.UNKNOWN
        else:
            return CentrifugeStatus.UNKNOWN

    def get_running_status(self) -> dict:
        """获取设备运行状态信息"""
        #if not self.is_connected:
        #    return {"status": "error", "message": "设备未连接"}
        
        # 读取实时状态
        result = self.get_result()
        if result.get("status") == "success":
            return {"status": "success", "data": result.get("data")}
        else:
            return {"status": "error", "message": result.get("message", "未知错误")}

    def get_result(self) -> dict:
        """获取设备状态结果"""
        # 【修改点1】删除 if not self.is_connected: 的判断，直接尝试通信
        
        # 读取实时状态
        result = self.send_raw(CENT_CMDS['read_all'])
        if result.get("status") == "success" and "bytes" in result:
            data = result["bytes"]
            if len(data) < 33:
                self.result = {"status": "error", "message": "数据不完整"}
            else:
                # 【修改点2】确保传给解析函数的是 bytes 对象，防止 struct.unpack 报错
                if isinstance(data, list):
                    data = bytes(data)
                
                self.result = {"status": "success", "data": self._parse_status_data(data)}
        else:
            self.result = {"status": "error", "message": f"读取状态失败: {result.get('message', '未知错误')}"}

        return self.result

    def get_message(self) -> str:
        """获取设备消息"""
        return self.message if self.message else "设备就绪"


# 创建全局实例（保持向后兼容）
centrifuge_controller = CentrifugeController()
