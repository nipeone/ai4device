# 文件名：centrifuge_core.py
import socket
import struct
import binascii
import time
from .base import ModbusControlledDevice
from utils import CENT_CMDS, CENT_FAULT_MAP, CENT_RUN_MAP, CENT_ROTOR_MAP, CENT_DOOR_MAP, cent_format_time
import config


class Centrifuge(ModbusControlledDevice):
    """Modbus控制的离心机设备"""
    
    def __init__(self, device_id: str = "01", host: str = None, port: int = None, timeout: int = None):
        # 从环境变量获取配置，如果没有提供参数则使用默认值
        host = host or config.CENTRIFUGE_HOST
        port = port or config.CENTRIFUGE_PORT
        timeout = timeout or config.CENTRIFUGE_TIMEOUT
        super().__init__("modbus_centrifuge_" + device_id, device_id, 1, port)
        self.host = host
        self.timeout = timeout
        self.speed = 0
        self.runtime = 0
        self.temperature = 0.0
        self.status_code = 0
        self.fault_code = 0
        self.rotor_status = 0
        self.door_status = 0

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

    def _build_write_command(self, address, value):
        """构建写命令（内部方法）"""
        cmd_part = struct.pack('>BBHH', 0x01, 0x06, address, value)
        crc = self._calculate_crc(cmd_part)
        return cmd_part + crc
    
    def build_write_command(self, address, value):
        """构建写命令（公共方法，保持向后兼容）"""
        return self._build_write_command(address, value)

    def _send_raw(self, hex_cmd):
        """发送原始Modbus命令并接收响应"""
        if not self.is_connected:
            return {"status": "error", "message": "设备未连接"}
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        try:
            sock.connect((self.host, self.port))
            
            # 清空缓冲区
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
            
            while time.time() - start_time < self.timeout:
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
                                return {"status": "success", "hex": response_hex, "bytes": list(valid_frame)}
                        else:
                            if len(buffer) > 100:
                                buffer = buffer[-20:]
                    else:
                        if len(buffer) >= 8 and buffer.startswith(b'\x01\x06'):
                            valid_frame = buffer[:8]
                            response_hex = binascii.hexlify(valid_frame).decode('utf-8')
                            return {"status": "success", "hex": response_hex, "bytes": list(valid_frame)}
                            
                except socket.timeout:
                    break
            
            return {
                "status": "error",
                "message": f"数据对齐失败，缓冲区: {binascii.hexlify(buffer).decode('utf-8')}"
            }

        except Exception as e:
            return {"status": "error", "message": str(e)}
        finally:
            sock.close()

    def connect(self):
        """连接Modbus设备"""
        try:
            # 测试连接：发送读取命令
            test_result = self._send_raw(CENT_CMDS['read_all'])
            if test_result.get("status") == "success":
                self.is_connected = True
                self.message = "离心机连接成功"
                return True
            else:
                self.is_connected = False
                self.message = f"离心机连接失败: {test_result.get('message', '未知错误')}"
                return False
        except Exception as e:
            self.is_connected = False
            self.message = f"离心机连接异常: {str(e)}"
            return False

    def disconnect(self):
        """断开Modbus设备连接"""
        self.is_connected = False
        self.message = "离心机已断开连接"

    def start(self):
        """启动离心机"""
        if not self.is_connected:
            self.message = "设备未连接"
            self.result = {"status": "error", "message": "设备未连接"}
            return
        
        result = self._send_raw(CENT_CMDS['start'])
        if result.get("status") == "success":
            self.message = "离心机启动成功"
            self.result = {"status": "success", "message": "启动成功"}
        else:
            self.message = f"启动失败: {result.get('message', '未知错误')}"
            self.result = {"status": "error", "message": result.get('message', '未知错误')}

    def stop(self):
        """停止离心机"""
        if not self.is_connected:
            self.message = "设备未连接"
            self.result = {"status": "error", "message": "设备未连接"}
            return
        
        result = self._send_raw(CENT_CMDS['stop'])
        if result.get("status") == "success":
            self.message = "离心机停止成功"
            self.result = {"status": "success", "message": "停止成功"}
        else:
            self.message = f"停止失败: {result.get('message', '未知错误')}"
            self.result = {"status": "error", "message": result.get('message', '未知错误')}

    def open_door(self):
        """打开离心机门"""
        if not self.is_connected:
            return {"status": "error", "message": "设备未连接"}
        return self._send_raw(CENT_CMDS['open'])

    def close_door(self):
        """关闭离心机门"""
        if not self.is_connected:
            return {"status": "error", "message": "设备未连接"}
        return self._send_raw(CENT_CMDS['close'])

    def _parse_status_data(self, data_bytes):
        """解析状态数据"""
        if len(data_bytes) < 33:
            return
        
        # 解析数据（根据实际协议调整）
        # 示例解析逻辑
        self.speed = (data_bytes[3] << 8) + data_bytes[4] if len(data_bytes) > 4 else 0
        self.runtime = (data_bytes[5] << 8) + data_bytes[6] if len(data_bytes) > 6 else 0
        self.temperature = ((data_bytes[7] << 8) + data_bytes[8]) / 10.0 if len(data_bytes) > 8 else 0.0
        self.status_code = data_bytes[9] if len(data_bytes) > 9 else 0
        self.fault_code = data_bytes[10] if len(data_bytes) > 10 else 0
        self.rotor_status = data_bytes[11] if len(data_bytes) > 11 else 0
        self.door_status = data_bytes[12] if len(data_bytes) > 12 else 0

    def get_status(self) -> dict:
        """获取设备状态"""
        if not self.is_connected:
            return {
                "name": self.device_name,
                "connected": False,
                "message": "设备未连接"
            }
        
        # 读取实时状态
        result = self._send_raw(CENT_CMDS['read_all'])
        if result.get("status") == "success" and "bytes" in result:
            self._parse_status_data(result["bytes"])
        
        return {
            "name": self.device_name,
            "connected": self.is_connected,
            "speed": self.speed,
            "runtime": self.runtime,
            "runtime_formatted": cent_format_time(self.runtime),
            "temperature": self.temperature,
            "status": CENT_RUN_MAP.get(self.status_code, "未知"),
            "fault": CENT_FAULT_MAP.get(self.fault_code, "正常"),
            "rotor_status": CENT_ROTOR_MAP.get(self.rotor_status, "未知"),
            "door_status": CENT_DOOR_MAP.get(self.door_status, "未知")
        }

    def get_result(self) -> dict:
        """获取设备结果"""
        return self.result if self.result else {
            "status": "idle",
            "message": "无操作结果"
        }

    def get_message(self) -> str:
        """获取设备消息"""
        return self.message if self.message else "设备就绪"


# 创建全局实例（保持向后兼容）
cent_sender = Centrifuge()
