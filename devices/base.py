from abc import ABC, abstractmethod
import requests  # REST API库（需安装：pip install requests）
# PLC/Modbus可根据实际库替换（如pymodbus、pycomm3）
from datetime import datetime
import time
from enum import Enum

# PLC通信库（snap7）
try:
    from snap7 import client
    from snap7.type import Area
    SNAP7_AVAILABLE = True
except ImportError:
    client = None
    Area = None
    SNAP7_AVAILABLE = False

class DeviceStatus(Enum):
    idle = "就绪"
    connected = "已连接"
    disconnected = "未连接"
    running = "运行中"
    paused = "暂停"
    cancelled = "已取消"
    completed = "已完成"
    error = "错误"
    timeout = "超时"
    abnormal = "异常"
    unknown = "未知"

# ===================== 1. 设备基类（所有设备的通用接口） =====================
class BaseDevice(ABC):
    """设备抽象基类：定义所有设备必须实现的核心接口"""
    def __init__(self, device_name: str, control_type: str, device_id: str):
        # 通用属性：设备名称、控制方式、唯一编号
        self.device_name = device_name  # 如 "plc_robot_arm_01"
        self.control_type = control_type      # 如 "PLC" / "Modbus" / "Socket" / "RESTAPI"
        self.device_id = device_id            # 如 "01"
        self.is_connected = False             # 设备连接状态
        self.result = None                    # 设备结果
        self.message = None                   # 设备消息
        self.status = DeviceStatus.unknown    # 设备状态: 默认未知

    @abstractmethod
    def connect(self):
        """连接设备（子类必须实现）"""
        pass

    @abstractmethod
    def disconnect(self):
        """断开设备（子类必须实现）"""
        pass

    @abstractmethod
    def start(self):
        """启动设备（子类必须实现）"""
        pass

    @abstractmethod
    def stop(self):
        """停止设备（子类必须实现）"""
        pass

    @abstractmethod
    def get_status(self) -> dict:
        """获取设备状态（子类必须实现），返回状态字典"""
        pass

    @abstractmethod
    def get_result(self) -> dict:
        """获取设备结果（子类必须实现），返回结果字典"""
        pass

    @abstractmethod
    def get_message(self) -> str:
        """获取设备消息（子类必须实现），返回消息字符串"""
        pass

# ===================== 2. 控制方式中间类（封装通用控制逻辑） =====================
class PLCControlledDevice(BaseDevice):
    """PLC控制设备的通用逻辑（基于snap7库）"""
    def __init__(self, device_name: str, device_id: str, plc_ip: str, plc_port: int = 102):
        super().__init__(device_name, "PLC", device_id)
        self.plc_ip = plc_ip
        self.plc_port = plc_port
        self.client = None  # snap7客户端对象
        self.last_conn = 0  # 上次连接尝试时间（用于限制重连频率）

    def try_connect(self):
        """尝试连接PLC（带重连频率限制）"""
        # 如果已经连接，直接返回
        if self.is_connected and self.client:
            return True

        # 限制重连频率，防止报错刷屏 (3秒一次)
        if time.time() - self.last_conn < 3:
            return False
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
        if not SNAP7_AVAILABLE:
            self.is_connected = False
            self.message = "snap7库未安装"
            return False

        try:
            self.client = client.Client()
            self.client.connect(self.plc_ip, 0, 1, self.plc_port)
            self.is_connected = self.client.get_connected()
            if self.is_connected:
                self.message = f"PLC设备连接成功: {self.plc_ip}:{self.plc_port}"
                return True
            else:
                self.message = "PLC连接失败：无法建立连接"
                return False
        except Exception as e:
            self.is_connected = False
            self.message = f"PLC设备连接失败: {str(e)}"
            try:
                if self.client:
                    self.client.destroy()
            except:
                pass
            self.client = None
            return False

    def connect(self):
        """连接PLC设备（实现抽象方法）"""
        return self.try_connect()

    def disconnect(self):
        """断开PLC设备连接"""
        if self.client:
            try:
                self.client.disconnect()
                self.client.destroy()
            except:
                pass
            self.client = None
        self.is_connected = False
        self.message = "PLC设备已断开连接"

    def read_m(self, b, i):
        """读取M区位状态"""
        if not self.is_connected or not self.client:
            return False
        try:
            return bool((self.client.read_area(Area.MK, 0, b, 1)[0] >> i) & 1)
        except:
            self.is_connected = False
            return False

    def read_m_bytes(self, b)->bytearray:
        """读取M区字节数据"""
        if not self.is_connected or not self.client:
            return bytearray()
        try:
            return self.client.read_area(Area.MK, 0, b, 1)
        except:
            self.is_connected = False
            return bytearray()

    def write_m_bytes(self, b:int, v:bytearray)->bool:
        """写入M区字节数据"""
        if not self.is_connected or not self.client:
            return False
        try:
            self.client.write_area(Area.MK, 0, b, v)
            return True
        except:
            self.is_connected = False
            return False

    def toggle_m(self, b, i):
        """切换M区位状态: 0->1 或 1->0 (保持模式)"""
        if not self.connect():
            return False
        try:
            d = self.client.read_area(Area.MK, 0, b, 1)
            v = bytearray(d)
            if (v[0] >> i) & 1:
                v[0] &= ~(1 << i)
            else:
                v[0] |= (1 << i)
            self.client.write_area(Area.MK, 0, b, v)
            return True
        except Exception as e:
            self.is_connected = False
            return False

    def pulse_m(self, b, i):
        """M区点动控制: 置位1 -> 等待0.5s -> 复位0 (安全模式)"""
        if not self.connect():
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
            return True
        except Exception as e:
            self.is_connected = False
            return False

    def pulse_db(self, db, byte):
        """DB区点动控制: 置位1 -> 等待0.5s -> 复位0 (安全模式)"""
        if not self.connect():
            return False
        try:
            # 1. 置位 (ON)
            self.client.write_area(Area.DB, db, byte, b'\x01')

            # 2. 延时
            time.sleep(0.5)

            # 3. 复位 (OFF)
            self.client.write_area(Area.DB, db, byte, b'\x00')
            return True
        except Exception as e:
            self.is_connected = False
            return False

    def write_db_int(self, db, byte, value, size=1):
        """写入DB区数据"""
        if not self.connect():
            return False
        try:
            self.client.write_area(Area.DB, db, byte, int(value).to_bytes(size, 'big'))
            return True
        except Exception as e:
            self.is_connected = False
            return False

    def write_db_bytes(self, db, byte, value: bytearray):
        """写入DB区字节数据, value为bytearray类型"""
        if not self.connect():
            return False
        try:
            self.client.write_area(Area.DB, db, byte, value)
            return True
        except Exception as e:
            self.is_connected = False
            return False

    def read_db_bit(self, db, byte, bit):
        """读取DB区位状态"""
        if not self.is_connected or not self.client:
            return False
        try:
            d = self.client.read_area(Area.DB, db, byte, 1)
            return bool((d[0] >> bit) & 1)
        except:
            self.is_connected = False
            return False

    def read_db_int(self, db, byte, size=2):
        """读取DB区整数值"""
        if not self.is_connected or not self.client:
            return 0
        try:
            d = self.client.read_area(Area.DB, db, byte, size)
            return int.from_bytes(d, 'big')
        except:
            self.is_connected = False
            return 0

    def read_db_bytes(self, db, byte, size)->bytearray:
        if not self.is_connected or not self.client:
            return bytearray()
        try:
            d = self.client.read_area(Area.DB, db, byte, size)
            return d
        except:
            self.is_connected = False
            return bytearray()

    def start(self):
        """启动设备（PLC设备通常通过任务控制，此方法可被子类重写）"""
        if self.is_connected:
            self.message = "PLC设备就绪"
            self.result = {"status": "success", "message": "PLC设备就绪"}
        else:
            self.message = "PLC设备未连接"
            self.result = {"status": "error", "message": "PLC设备未连接"}

    def stop(self):
        """停止设备"""
        self.message = "PLC设备已停止"
        self.result = {"status": "success", "message": "PLC设备已停止"}

    def get_status(self) -> dict:
        """获取设备状态"""
        return {
            "name": self.device_name,
            "connected": self.is_connected,
            "ip": self.plc_ip,
            "port": self.plc_port,
            "message": self.message,
            "status": self.status
        }

    def get_result(self) -> dict:
        """获取设备结果"""
        return self.result if self.result else {
            "status": self.status,
            "message": self.message
        }

    def get_message(self) -> str:
        """获取设备消息"""
        return self.message

class ModbusControlledDevice(BaseDevice):
    """Modbus控制设备的通用逻辑"""
    def __init__(self, device_name: str, device_id: str, modbus_addr: int, modbus_port: int):
        super().__init__(device_name, "Modbus", device_id)
        self.modbus_addr = modbus_addr
        self.modbus_port = modbus_port
        self.modbus_client = None  # Modbus客户端对象（需替换为pymodbus）

    def connect(self):
        """Modbus设备通用连接逻辑"""
        try:
            # 实际项目中替换为pymodbus的TCP/UDP连接代码
            # from pymodbus.client import ModbusTcpClient
            # self.modbus_client = ModbusTcpClient('localhost', port=self.modbus_port)
            # self.modbus_client.connect()
            self.is_connected = True
            print(f"[{self.device_name}] Modbus设备连接成功")
        except Exception as e:
            print(f"[{self.device_name}] Modbus设备连接失败：{e}")
            self.is_connected = False

    def disconnect(self):
        """Modbus设备通用断开逻辑"""
        if self.is_connected and self.modbus_client:
            # self.modbus_client.close()
            self.is_connected = False
            print(f"[{self.device_name}] Modbus设备断开连接")

class SocketControlledDevice(BaseDevice):
    """Socket/ZMQ控制设备的通用逻辑"""
    def __init__(self, device_name: str, device_id: str, socket_address: str):
        super().__init__(device_name, "Socket", device_id)
        self.socket_address = socket_address  # Socket地址：如 "tcp://127.0.0.1:49202"
        self.context = None  # ZMQ Context对象
        self.socket = None  # ZMQ Socket对象

    def connect(self):
        """Socket设备通用连接逻辑（子类需要实现具体连接测试）"""
        # 子类需要实现具体的连接测试逻辑
        self.is_connected = True
        print(f"[{self.device_name}] Socket设备连接成功")

    def disconnect(self):
        """Socket设备通用断开逻辑"""
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
        if self.context:
            try:
                self.context.term()
            except:
                pass
        self.socket = None
        self.context = None
        self.is_connected = False
        print(f"[{self.device_name}] Socket设备断开连接")

class RestAPIControlledDevice(BaseDevice):
    """REST API控制设备的通用逻辑"""
    def __init__(self, device_name: str, device_id: str, api_base_url: str):
        super().__init__(device_name, "RESTAPI", device_id)
        self.api_base_url = api_base_url  # API基础地址：如 "http://192.168.1.100/api/v1"
        self.api_token = None             # API认证令牌
        self.api_token_type = None        # API认证令牌类型
        self.api_headers = {}             # API认证头部

    def connect(self):
        """REST API设备通用连接逻辑（实际为认证/可达性检测）"""
        try:
            # 检测API是否可达
            response = requests.get(f"{self.api_base_url}/health", timeout=5)
            if response.status_code == 200:
                self.is_connected = True
                print(f"[{self.device_name}] REST API设备连接成功")
            else:
                raise Exception(f"API健康检查失败，状态码：{response.status_code}")
        except Exception as e:
            print(f"[{self.device_name}] REST API设备连接失败：{e}")
            self.is_connected = False

    def disconnect(self):
        """REST API设备通用断开逻辑（无实际连接，仅标记状态）"""
        self.is_connected = False
        print(f"[{self.device_name}] REST API设备断开连接")
