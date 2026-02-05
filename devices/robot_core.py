import time
from enum import Enum

from .base import PLCControlledDevice
import config

from schemas.robot import PlcStatus, TaskData, RobotSystemStatus, RobotWorkingStatus, RobotHomeStatus, RobotTaskStatus, RobotActionCode, RobotStatus

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
        第 3 个值 (Index 2): 对应 M10.2 (开高温炉门) -> false。
        第 4 个值 (Index 3): 对应 M10.3 (开高温炉盖) -> false。
        第 5 个值 (Index 4): 对应 M10.4 (开离心机门) -> false。
        第 6 个值 (Index 5): 对应 M10.5 (机器人停止) -> true。(触发)。
         DB1.218.0 (原点状态) - 1=原点。
         DB1.218.1 (夹具状态) - 1=打开。
         DB1.242 (系统状态) - 0=断线, 1=空闲, 2=执行中, 3=完成, 4=失败。
         DB2.40 (任务状态) - 0=无任务, 1=有任务。"""
        if not self.is_connected:
            return {
                "status": "error",
                "message": "设备未连接"
            }
        return {
            "status": "success",
            "data": PlcStatus(
                plc_connected=self.is_connected,
                m_signals=[self.read_m(10, i) for i in range(7)],
                task_data=TaskData(
                    tid=self.read_db_int(3, 0),
                    st=self.read_db_int(3, 2),
                    qty=self.read_db_int(3, 4)
                ),
                robot=RobotStatus(
                    home_status=self.read_db_bit(1, 218, 0),
                    fixture_status=self.read_db_bit(1, 218, 1),
                    system_status=self.read_db_int(1, 242, 4),
                    robot_status=self.read_db_bit(2, 18, 4),
                    task_status=self.read_db_int(2, 40, 4)
                )
            )
        }

    def get_home_status(self) -> RobotHomeStatus:
        """获取原点状态: DB1.218.0 (原点状态) 
        - 0=非原点
        - 1=在原点
        """
        return RobotHomeStatus(self.read_db_bit(1, 218, 0))

    def get_task_status(self) -> RobotTaskStatus:
        """获取任务状态: DB2.40 (任务状态) 
        - NO_TASK: 无任务
        - HAS_TASK: 有任务
        """
        return RobotTaskStatus(self.read_db_int(2, 40, 4))

    def get_system_status(self) -> RobotSystemStatus:
        """获取系统状态: DB1.242 (系统状态) 
        - DISCONNECTED: 断线(0)
        - IDLE: 空闲
        - RUNNING: 运行中
        - COMPLETED: 完成
        - FAILED: 失败
        """
        return RobotSystemStatus(self.read_db_int(1, 242, 4))

    def get_robot_working_status(self) -> RobotWorkingStatus:
        """获取机器人状态: DB2.18.4 (机器人启动/暂停) 
        - STARTED: 启动
        - PAUSED: 暂停
        """
        return RobotWorkingStatus(self.read_db_bit(2, 18, 4))

    def reset_robot(self) -> bool:
        """机器人复位
        对应 DB2.18.0 (机器人复位)。瞬动控制，用于清除机器人报警。
        """
        return self.pulse_db(2, 18)

    def toggle_robot(self) -> bool:
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

    def toggle_m_10(self, bit: int) -> bool:
        """翻转M10.x区信号。
        在bit输入位地址(0 - 5)，执行后将对应的M10.x信号取反。
        - M10.0	任务下发	标签3	反转控制
        - M10.1	任务清除	标签8	反转控制
        - M10.2	开高温炉门	标签7	反转控制
        - M10.3 开高温炉盖  标签1   反转控制
        - M10.4 开离心机门  标签2   反转控制
        - M10.5	机器人停止	标签13	反转控制。"""
        if not self.connect():
            return False
        return self.toggle_m(10, bit)

    def dispatch_task(self) -> bool:
        """下发任务
        - M10.0 是启动信号
        """
        if not self.connect():
            return False
        return self.pulse_m(10, 0)

    def write_task(self, tid: int, sta: int, qty: int) -> bool:
        """写入任务数据到DB3
        - tid: 任务ID DB3.0
        - sta: 站点(货架号) DB3.2
        - qty: 数量 DB3.4
        """
        if not self.connect():
            return False
        # 设置数据 (tid任务id/st站点/qty生产数量)
        self.write_db_int(3, 0, tid, size=2)
        self.write_db_int(3, 2, sta, size=2)
        self.write_db_int(3, 4, qty, size=2)
        return True

robot_controller = RobotController()