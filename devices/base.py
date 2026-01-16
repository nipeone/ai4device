from abc import ABC, abstractmethod
import requests  # REST API库（需安装：pip install requests）
# PLC/Modbus可根据实际库替换（如pymodbus、pycomm3）
from datetime import datetime

# ===================== 1. 设备基类（所有设备的通用接口） =====================
class BaseDevice(ABC):
    """设备抽象基类：定义所有设备必须实现的核心接口"""
    def __init__(self, device_name: str, control_type: str, device_id: str):
        # 通用属性：设备名称、控制方式、唯一编号
        self.device_name = device_name  # 如 "plc_robot_arm_01"
        self.control_type = control_type      # 如 "PLC" / "Modbus" / "Serial" / "RESTAPI"
        self.device_id = device_id            # 如 "01"
        self.is_connected = False             # 设备连接状态
        self.result = None                    # 设备结果
        self.message = None                   # 设备消息

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
    """PLC控制设备的通用逻辑"""
    def __init__(self, device_name: str, device_id: str, plc_ip: str, plc_port: int):
        super().__init__(device_name, "PLC", device_id)
        self.plc_ip = plc_ip
        self.plc_port = plc_port
        self.plc_client = None  # PLC客户端对象（需替换为实际PLC库）

    def connect(self):
        """PLC设备通用连接逻辑"""
        try:
            # 实际项目中替换为PLC库的连接代码（如pycomm3）
            # self.plc_client = LogixDriver(self.plc_ip, self.plc_port)
            # self.plc_client.open()
            self.is_connected = True
            print(f"[{self.device_name}] PLC设备连接成功")
        except Exception as e:
            print(f"[{self.device_name}] PLC设备连接失败：{e}")
            self.is_connected = False

    def disconnect(self):
        """PLC设备通用断开逻辑"""
        if self.is_connected and self.plc_client:
            # self.plc_client.close()
            self.is_connected = False
            print(f"[{self.device_name}] PLC设备断开连接")

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

class SerialControlledDevice(BaseDevice):
    """串口控制设备的通用逻辑"""
    def __init__(self, device_name: str, device_id: str, serial_port: str, baudrate: int):
        super().__init__(device_name, "Serial", device_id)
        self.serial_port = serial_port  # 串口名：如 "COM3" / "/dev/ttyUSB0"
        self.baudrate = baudrate        # 波特率：如 9600
        self.serial_client = None       # 串口客户端对象

    def connect(self):
        """串口设备通用连接逻辑"""
        try:
            self.serial_client = serial.Serial(
                port=self.serial_port,
                baudrate=self.baudrate,
                timeout=1
            )
            self.is_connected = True
            print(f"[{self.device_name}] 串口设备连接成功")
        except Exception as e:
            print(f"[{self.device_name}] 串口设备连接失败：{e}")
            self.is_connected = False

    def disconnect(self):
        """串口设备通用断开逻辑"""
        if self.is_connected and self.serial_client:
            self.serial_client.close()
            self.is_connected = False
            print(f"[{self.device_name}] 串口设备断开连接")

class RestAPIControlledDevice(BaseDevice):
    """REST API控制设备的通用逻辑"""
    def __init__(self, device_name: str, device_id: str, api_base_url: str):
        super().__init__(device_name, "RESTAPI", device_id)
        self.api_base_url = api_base_url  # API基础地址：如 "http://192.168.1.100/api/v1"
        self.api_token = None             # API认证令牌（按需添加）

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

# ===================== 3. 具体设备类（实现特有逻辑） =====================
class RobotArm(PLCControlledDevice):
    """PLC控制的机械臂（具体设备）"""
    def __init__(self):
        # 实例名遵循：控制方式_设备类型_编号
        super().__init__("plc_robot_arm_01", "01", "192.168.1.20", 502)
        self.grip_force = 0  # 机械臂特有属性：抓取力

    def start(self):
        """机械臂启动逻辑（特有）"""
        if self.is_connected:
            print(f"[{self.device_name}] 机械臂启动，开始抓取物料")
            # 实际PLC控制指令：如写入寄存器控制机械臂启动

    def stop(self):
        """机械臂停止逻辑（特有）"""
        if self.is_connected:
            print(f"[{self.device_name}] 机械臂停止，释放物料")

    def get_status(self) -> dict:
        """获取机械臂状态（特有）"""
        return {
            "name": self.device_name,
            "connected": self.is_connected,
            "grip_force": self.grip_force,
            "position": "X:100,Y:200,Z:50"  # 示例位置信息
        }

class Centrifuge(ModbusControlledDevice):
    """Modbus控制的离心机（具体设备）"""
    def __init__(self):
        super().__init__("modbus_centrifuge_01", "01", 1, 502)
        self.speed = 0  # 离心机特有属性：转速

    def start(self):
        if self.is_connected:
            self.speed = 3000  # 设置转速
            print(f"[{self.device_name}] 离心机启动，转速：{self.speed} rpm")

    def stop(self):
        if self.is_connected:
            self.speed = 0
            print(f"[{self.device_name}] 离心机停止")

    def get_status(self) -> dict:
        return {
            "name": self.equipment_name,
            "connected": self.is_connected,
            "speed": self.speed,
            "temperature": 45.2  # 示例温度信息
        }

class HighTempFurnace(SerialControlledDevice):
    """串口控制的高温炉（具体设备）"""
    def __init__(self):
        super().__init__("serial_high_temp_furnace_01", "01", "COM3", 9600)
        self.temperature = 0  # 高温炉特有属性：温度

    def start(self):
        if self.is_connected:
            self.temperature = 800  # 设置目标温度
            print(f"[{self.equipment_name}] 高温炉启动，目标温度：{self.temperature}℃")

    def stop(self):
        if self.is_connected:
            self.temperature = 0
            print(f"[{self.equipment_name}] 高温炉停止，开始降温")

    def get_status(self) -> dict:
        return {
            "name": self.equipment_name,
            "connected": self.is_connected,
            "temperature": self.temperature,
            "door_status": "closed"  # 示例炉门状态
        }

class MixerMachine(RestAPIControlledDevice):
    """REST API控制的配料机（具体设备）"""
    def __init__(self):
        super().__init__("restapi_batching_machine_01", "01", "http://192.168.1.30/api/v1")
        self.material_ratio = {"A": 0.3, "B": 0.7}  # 配料机特有属性：物料配比

    def start(self):
        if self.is_connected:
            # 实际API请求：启动配料
            # requests.post(f"{self.api_base_url}/start", json=self.material_ratio)
            print(f"[{self.equipment_name}] 配料机启动，配比：{self.material_ratio}")

    def stop(self):
        if self.is_connected:
            # requests.post(f"{self.api_base_url}/stop")
            print(f"[{self.equipment_name}] 配料机停止")

    def get_status(self) -> dict:
        # 实际API请求：获取状态
        # response = requests.get(f"{self.api_base_url}/status")
        return {
            "name": self.equipment_name,
            "connected": self.is_connected,
            "material_ratio": self.material_ratio,
            "progress": 75  # 示例配料进度
        }

# ===================== 4. 实例化与使用示例 =====================
if __name__ == "__main__":
    # 1. 创建设备实例（命名符合规范）
    plc_robot_arm_01 = RobotArm()
    modbus_centrifuge_01 = Centrifuge()
    serial_high_temp_furnace_01 = HighTempFurnace()
    restapi_batching_machine_01 = MixerMachine()

    # 2. 统一管理所有设备（基类接口一致，可批量操作）
    device_list = [
        plc_robot_arm_01,
        modbus_centrifuge_01,
        serial_high_temp_furnace_01,
        restapi_batching_machine_01
    ]

    # 3. 批量连接、启动、查询状态
    for eq in device_list:
        eq.connect()
        eq.start()
        print(f"设备状态：{eq.get_status()}\n")

    # 4. 批量停止、断开
    for eq in device_list:
        eq.stop()
        eq.disconnect()