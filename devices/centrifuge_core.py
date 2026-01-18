import socket
import struct
import binascii
import time
from .base import ModbusControlledDevice
import config
from utils import (
    CENT_CMDS, 
    CENT_FAULT_MAP, 
    CENT_RUN_MAP, 
    CENT_ROTOR_MAP, 
    CENT_DOOR_MAP, 
    cent_format_time, 
    cent_get_value
)



class CentrifugeController(ModbusControlledDevice):
    """Modbus控制的离心机设备"""
    
    def __init__(self, device_id: str = "01", host: str = None, port: int = None, timeout: int = None):
        # 从环境变量获取配置，如果没有提供参数则使用默认值
        host = host or config.CENTRIFUGE_HOST
        port = port or config.CENTRIFUGE_PORT
        timeout = timeout or config.CENTRIFUGE_TIMEOUT
        super().__init__("modbus_centrifuge_" + device_id, device_id, host, port)
        self.timeout = timeout

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
        """构建写命令（内部方法）"""
        cmd_part = struct.pack('>BBHH', 0x01, 0x06, address, value)
        crc = self._calculate_crc(cmd_part)
        return cmd_part + crc

    def send_raw(self, hex_cmd):
        """发送原始Modbus命令并接收响应"""
        if not self.is_connected:
            return {"status": "error", "message": "设备未连接"}
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        try:
            sock.connect((self.modbus_addr, self.modbus_port))
            
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
            test_result = self.send_raw(CENT_CMDS['read_all'])
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
        
        result = self.send_raw(CENT_CMDS['start'])
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
            return False
        
        result = self.send_raw(CENT_CMDS['stop'])
        if result.get("status") == "success":
            self.message = "离心机停止成功"
            self.result = {"status": "success", "message": "停止成功"}
            return True
        else:
            self.message = f"停止失败: {result.get('message', '未知错误')}"
            self.result = {"status": "error", "message": result.get('message', '未知错误')}
            return False

    def open_door(self):
        """打开离心机门"""
        if not self.is_connected:
            self.result = {"status": "error", "message": "设备未连接"}
            return False
        result = self.send_raw(CENT_CMDS['open'])
        if result.get("status") == "success":
            self.message = "离心机门打开成功"
            self.result = {"status": "success", "message": "打开成功"}
            return True
        else:
            self.message = f"打开失败: {result.get('message', '未知错误')}"
            self.result = {"status": "error", "message": result.get('message', '未知错误')}
            return False

    def close_door(self):
        """关闭离心机门"""
        if not self.is_connected:
            self.result = {"status": "error", "message": "设备未连接"}
            return False
        result = self.send_raw(CENT_CMDS['close'])
        if result.get("status") == "success":
            self.message = "离心机门关闭成功"
            self.result = {"status": "success", "message": "关闭成功"}
            return True
        else:
            self.message = f"关闭失败: {result.get('message', '未知错误')}"
        return self.send_raw(CENT_CMDS['close'])

    def _parse_status_data(self, data_bytes):
        """解析状态数据"""
        # 当前转速
        actual_rpm = cent_get_value(data_bytes, 1)
        # 离心力
        centrifuge_force = cent_get_value(data_bytes, 2)
        # 运行时间
        run_time = cent_get_value(data_bytes, 3)
        # 故障码
        fault_code = cent_get_value(data_bytes, 4)
        # 运行状态
        run_state = cent_get_value(data_bytes, 5)
        # 门窗状态
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

    def get_status(self) -> dict:
        """获取设备状态"""
        if not self.is_connected:
            return {
                "name": self.device_name,
                "connected": self.is_connected,
                "message": "设备未连接"
            }
        
        # 读取实时状态
        result = self.send_raw(CENT_CMDS['read_all'])
        if result.get("status") == "success" and "bytes" in result:
            data = result["bytes"]
            if len(data) < 33: 
                return {
                    "name": self.device_name, 
                    "connected": self.is_connected, 
                    "message": "数据不完整"
                }
            else:
                return {
                    "name": self.device_name,
                    "connected": self.is_connected,
                    "data": self._parse_status_data(data)
                }
        else:
            return {
                "name": self.device_name,
                "connected": self.is_connected,
                "message": f"读取状态失败: {result.get('message', '未知错误')}"
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
centrifuge_controller = CentrifugeController()
