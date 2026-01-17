import time
from .base import PLCControlledDevice
from utils import CENT_CMDS, CENT_FAULT_MAP, CENT_RUN_MAP, CENT_ROTOR_MAP, CENT_DOOR_MAP, cent_format_time
import config

class RobotController(PLCControlledDevice):
    """PLC控制的机器人手臂设备"""
    
    def __init__(self, device_id: str = "01", plc_ip: str = None, plc_port: int = None):
        # 从环境变量获取配置，如果没有提供参数则使用默认值
        plc_ip = plc_ip or config.PLC_IP
        plc_port = plc_port or config.PLC_PORT
        super().__init__("plc_robot_arm_" + device_id, device_id, plc_ip, plc_port)

    def get_status(self) -> dict:
        """获取 PLC 连接及机器人状态。
        第 1 个值 (Index 0): 对应 M10.0 (任务下发) -> false (未触发)。
        第 2 个值 (Index 1): 对应 M10.1 (任务清除) -> false。
        第 3 个值 (Index 2): 对应 M10.2 (开玻璃门) -> false。
        第 4 个值 (Index 3): 对应 M10.3 (开加热炉) -> false。
        第 5 个值 (Index 4): 对应 M10.4 (开离心机门) -> false。
        第 6 个值 (Index 5): 对应 M10.5 (机器人停止) -> true。(触发)。
         DB1.218.0 (原点状态) - 1=原点。
         DB1.218.1 (夹具状态) - 1=打开。
         DB1.242 (系统状态) - 0=断线, 1=空闲, 2=执行中, 3=完成, 4=失败。
         DB2.40 (任务状态) - 0=无任务, 1=有任务。"""
        if not self.is_connected:
            return {
                "name": self.device_name,
                "connected": False,
                "message": "设备未连接"
            }
        return {
        "PLC连接状态": self.is_connected,
        "M 区控制信号状态": [self.read_m(10, i) for i in range(7)],
        "任务数据": {
            "工号": self.read_db_int(3, 0),
            "工位类型/炉号": self.read_db_int(3, 2),
            "数量": self.read_db_int(3, 4)
        },
        "robot": {
            "原点状态": self.read_db_bit(1, 218, 0),
            "夹具状态": self.read_db_bit(1, 218, 1),
            "系统状态": self.read_db_int(1, 242, 4),
            "机器人启动/暂停": self.read_db_bit(2, 18, 4),
            "任务状态": self.read_db_int(2, 40, 4)
        }
    }

    def get_home_status(self):
        """获取原点状态: DB1.218.0 (原点状态) 
        - 1=原点
        - 0=非原点
        """
        return self.read_db_bit(1, 218, 0)

    def get_task_status(self):
        """获取任务状态: DB2.40 (任务状态) 
        - 0=无任务
        - 1=有任务
        """
        return self.read_db_int(2, 40, 4)

    def get_system_status(self):
        """获取系统状态: DB1.242 (系统状态) 
        - 0=断线
        - 1=空闲
        - 2=执行中
        - 3=完成
        - 4=失败
        """
        return self.read_db_int(1, 242, 4)

    def get_robot_status(self):
        """获取机器人状态: DB2.18.4 (机器人启动/暂停) 
        - 1=启动
        - 0=暂停
        """
        return self.read_db_bit(2, 18, 4)

    def reset_robot(self):
        """机器人复位
        对应 DB2.18.0 (机器人复位)。瞬动控制，用于清除机器人报警。
        """
        return self.pulse_db(2, 18)

    def toggle_robot(self):
        """机器人启动/暂停
        对应 DB2.18.4 (机器人启动/暂停)。反转控制，切换机器人的运行/暂停状态。
        """
        if not self.connect():
            return False
        d = self.read_db_bytes(2, 18, 1)
        v = bytearray(d)
        if (v[0] >> 4) & 1:
            v[0] &= ~(1 << 4)
        else:
            v[0] |= (1 << 4)
        self.write_db_bytes(2, 18, v)
        return True

    def toggle_m_10(self, bit: int):
        """翻转M10.x区信号。
        在bit输入位地址(0 - 5)，执行后将对应的M10.x信号取反。
        M10.0	任务下发	标签3	反转控制
        M10.1	任务清除	标签8	反转控制
        M10.2	开玻璃门	标签7	反转控制
        M10.3   开加热炉    标签1   反转控制
        M10.4   开离心机门  标签2   反转控制
        M10.5	机器人停止	标签13	反转控制。"""
        if not self.connect():
            return False
        return self.toggle_m(10, bit)

    def write_task(self, tid, st, qty):
        """写入任务数据到DB3
        - tid: 任务ID DB3.0
        - st: 站点 DB3.2
        - qty: 生产数量 DB3.4
        """
        if not self.connect():
            return False
        # 设置数据 (tid任务id/st站点/qty生产数量)
        self.write_db_int(3, 0, tid, size=2)
        self.write_db_int(3, 2, st, size=2)
        self.write_db_int(3, 4, qty, size=2)
        return True

robot_controller = RobotController()