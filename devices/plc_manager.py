"""
PLC管理器模块
继承自base.PLCControlledDevice，提供PLC控制功能
保持向后兼容，所有原有接口保持不变
"""
from .base import PLCControlledDevice
from logger import sys_logger as logger
import config


class PLCManager(PLCControlledDevice):
    """
    PLC管理器类
    继承自PLCControlledDevice，提供完整的PLC控制功能
    """
    def __init__(self, ip=None, port=None):
        # 从环境变量获取配置，如果没有提供参数则使用默认值
        ip = ip or config.PLC_IP
        port = port or config.PLC_PORT
        # 调用父类初始化，设备名称和ID使用默认值
        super().__init__("plc_manager_01", "01", ip, port)
        self.ip = ip  # 保持向后兼容的属性名

    def try_connect(self):
        """尝试连接PLC（重写以添加日志）"""
        result = super().try_connect()
        if result and self.is_connected:
            logger.log("PLC: 连接恢复成功！", "SUCCESS")
        elif not result:
            logger.log(f"PLC: 连接失败 - {self.message}", "ERROR")
        return result

    def toggle_m(self, b, i):
        """切换M区位状态（重写以添加日志）"""
        result = super().toggle_m(b, i)
        # 可选：添加日志
        # if result:
        #     logger.log(f"PLC: 切换M{b}.{i} 成功", "INFO")
        # else:
        #     logger.log(f"PLC: 切换M{b}.{i} 失败", "ERROR")
        return result

    def pulse_m(self, b, i):
        """点动控制（重写以添加日志）"""
        result = super().pulse_m(b, i)
        # 可选：添加日志
        # if result:
        #     logger.log(f"PLC: 点动M{b}.{i} 完成", "INFO")
        # else:
        #     logger.log(f"PLC: 点动M{b}.{i} 异常中断", "ERROR")
        return result

    def write_task(self, tid, st, qty):
        """写入任务数据（重写以添加日志）"""
        result = super().write_task(tid, st, qty)
        # 可选：添加日志
        # if result:
        #     logger.log(f"PLC: 任务数据写入成功 (ID:{tid}, ST:{st}, Qty:{qty})", "INFO")
        # else:
        #     logger.log(f"PLC: 写入任务异常", "ERROR")
        return result

    # 保持向后兼容：connected属性作为is_connected的别名
    @property
    def connected(self):
        """向后兼容：connected属性"""
        return self.is_connected

    @connected.setter
    def connected(self, value):
        """向后兼容：connected属性设置器"""
        self.is_connected = value

    # client属性已经在父类PLCControlledDevice中定义，无需额外处理
    # 可以直接通过self.client访问snap7 client对象


# 创建全局实例（保持向后兼容）
plc_mgr = PLCManager()
