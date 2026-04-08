"""
Device 层 Mock 实现：与真实设备同接口，返回成功或模拟数据，便于无硬件时跑通完整 flow。
当 config.MOCK_DEVICES=True 时，flows 注入此类实例替代真实 controller，实验流程走同一套代码路径。
Mock 执行时每次「动作」调用会随机延迟 0～20 秒，模拟设备响应时间。
"""
import os
import random
import time
from typing import Dict, Any, List, Optional
import threading
import json

from .base import DeviceStatus
from schemas.robot import RobotSystemStatus, RobotHomeStatus
from schemas.centrifuge import CentrifugeStatus, CentrifugeDoorStatus
from schemas.oven import OvenStatus, OvenActionCode, OvenLidActionCode
from schemas.oven import CurvePoint
from schemas.mixer import (
    GetTaskInfoResponse, 
    TaskSetup, 
    LayoutListItem, 
    TaskStatus, 
    AddTaskResponse, 
    GetResourceInfoResponse, 
    GetSetupResponse, 
    BatchCheckTaskResponse,
    GetChemicalsResponse
)


# Mock 动作随机延迟下限（秒）
MOCK_DELAY_MIN = 10
# Mock 动作随机延迟上限（秒）
MOCK_DELAY_MAX = 20


def _mock_delay():
    """Mock 设备动作时随机延迟 0～MOCK_DELAY_MAX 秒。"""
    time.sleep(random.uniform(MOCK_DELAY_MIN, MOCK_DELAY_MAX))


# ---------- Mock RobotController ----------
class MockRobotController:
    """PLC 机器人 Mock：connect/read_m_bytes/write_m_bytes/write_task/dispatch_task/get_system_status/get_home_status 均返回成功。"""

    def __init__(self, device_id: str = "01", plc_ip: str = None, plc_port: int = None):
        self.device_name = "mock_plc_robot_arm_" + device_id
        self.device_id = device_id
        self.is_connected = False
        self.message = "Mock 机器人"
        self.result = None
        self.status = DeviceStatus.UNKNOWN

    @property
    def connected(self):
        return self.is_connected

    def connect(self):
        _mock_delay()
        self.is_connected = True
        self.message = "Mock 机器人连接成功"
        self.status = DeviceStatus.CONNECTED
        return True

    def disconnect(self):
        self.is_connected = False
        self.message = "Mock 机器人已断开"

    def read_m_bytes(self, b: int, size: int = 1) -> bytearray:
        return bytearray(size)

    def write_m_bytes(self, b: int, v: bytearray) -> bool:
        _mock_delay()
        return True

    def get_system_status(self) -> RobotSystemStatus:
        return RobotSystemStatus.IDLE

    def get_home_status(self) -> RobotHomeStatus:
        return RobotHomeStatus.IN_HOME

    def get_task_status(self):
        from schemas.robot import RobotTaskStatus
        return RobotTaskStatus.NO_TASK

    def write_task(self, tid: int, sta: int, qty: int) -> bool:
        _mock_delay()
        return True

    def dispatch_task(self) -> bool:
        _mock_delay()
        return True

    def get_running_status(self) -> dict:
        # 与 robot_core.get_running_status 一致：PlcStatus 结构，供 thermal_flow.get_summary 的 summary.robot 使用
        return {
            "status": "success",
            "data": {
                "plc_connected": self.is_connected,
                "m_signals": [False] * 7,
                "task_data": {"tid": 0, "st": 0, "qty": 0},
                "robot": {
                    "home_status": True,
                    "fixture_status": True,
                    "system_status": RobotSystemStatus.IDLE.value,
                    "robot_status": False,
                    "task_status": 0,
                },
            },
        }

    def get_status(self) -> dict:
        return {"name": self.device_name, "connected": self.is_connected, "message": self.message}

    def get_result(self) -> dict:
        return self.result or {"status": "success", "message": self.message}

    def get_message(self) -> str:
        return self.message

    def start(self):
        self.message = "Mock 机器人就绪"
        self.result = {"status": "success", "message": self.message}

    def stop(self):
        self.message = "Mock 机器人已停止"
        self.result = {"status": "success", "message": self.message}


# ---------- Mock DoorController ----------
class MockDoorController:
    """玻璃门 Mock：connect/get_door_status/open_door/close_door 返回成功。"""

    def __init__(self, device_id: str = "01", target_address: str = None):
        self.device_name = "mock_socket_door_" + device_id
        self.device_id = device_id
        self.is_connected = False
        self.message = "Mock 门"
        self.result = None
        self.status = DeviceStatus.UNKNOWN

    def connect(self):
        _mock_delay()
        self.is_connected = True
        self.message = "Mock 门连接成功"
        self.status = DeviceStatus.CONNECTED
        return True

    def disconnect(self):
        self.is_connected = False
        self.message = "Mock 门已断开"

    def get_door_status(self, door_index: int) -> dict:
        self.result = {"status": "success", "message": "ok", "data": False}
        return self.result

    def open_door(self, door_index: int) -> dict:
        _mock_delay()
        self.result = {"status": "success", "message": "开门成功", "data": {"door": door_index}}
        return self.result

    def close_door(self, door_index: int) -> dict:
        _mock_delay()
        self.result = {"status": "success", "message": "关门成功", "data": {"door": door_index}}
        return self.result

    def get_status(self) -> dict:
        return {"name": self.device_name, "connected": self.is_connected}

    def get_result(self) -> dict:
        return self.result or {"status": "success", "message": self.message}

    def get_message(self) -> str:
        return self.message

    def start(self):
        self.result = {"status": "success", "message": "门就绪"}

    def stop(self):
        self.result = {"status": "success", "message": "门已停止"}


# ---------- Mock OvenController ----------
class MockOvenController:
    """高温炉 Mock：按 control_oven(START/STOP) 维护每炉状态，get_oven_status 返回当前状态以通过「启动后等 RUNNING、燃烧后等 STOPPED」的流程。"""

    def __init__(self, device_id: str = "01", req_addr: str = None, sub_addr: str = None, ctrl_addr: str = None):
        self.device_name = "mock_socket_oven_" + device_id
        self.device_id = device_id
        self.is_connected = False
        self.message = "Mock 高温炉"
        self.result = None
        self.status = DeviceStatus.UNKNOWN
        self._oven_status: Dict[int, OvenStatus] = {}  # oven_id -> RUNNING/STOPPED，默认 STOPPED

    def connect(self):
        _mock_delay()
        self.is_connected = True
        self.message = "Mock 高温炉连接成功"
        self.result = {"status": "success", "message": self.message}
        return True

    def disconnect(self):
        self.is_connected = False
        self.message = "Mock 高温炉已断开"

    def get_oven_status(self, oven_id: int) -> OvenStatus:
        return self._oven_status.get(oven_id, OvenStatus.STOPPED)

    def get_realtime_data(self, duration: float = 0.1) -> dict:
        return {}

    def get_device_list(self):
        return []

    def set_curve_points(self, oven_id: int, curve_points: List) -> dict:
        _mock_delay()
        self.result = {"status": "success", "message": "曲线设置成功"}
        return self.result

    def control_lid(self, oven_id: int, action_code: OvenLidActionCode) -> dict:
        _mock_delay()
        self.result = {"status": "success", "message": f"炉盖{action_code}成功"}
        return self.result

    def control_oven(self, oven_id: int, action_code: OvenActionCode) -> dict:
        _mock_delay()
        if action_code == OvenActionCode.START:
            self._oven_status[oven_id] = OvenStatus.RUNNING
        elif action_code == OvenActionCode.STOP:
            self._oven_status[oven_id] = OvenStatus.STOPPED
        self.result = {"status": "success", "message": f"炉{oven_id} {action_code}成功"}
        return self.result

    def get_running_status(self) -> dict:
        # 与 oven_core.get_running_status 一致：data 为炉子状态列表，供 thermal_flow.get_summary 的 summary.oven 使用
        return {
            "status": "success",
            "data": [
                {
                    "设备名称": f"炉{oven_id}",
                    "设备地址": oven_id,
                    "仪表型号": "858P",
                    "在线状态": "在线",
                    "实际温度": 25.0,
                    "设定温度": 100.0,
                    "状态显示": "阶段0 剩余1.0h",
                    "结束时间": "-",
                    "状态": "开始",
                    "运行曲线": "炉温曲线",
                } for oven_id in range(1, 25)
            ],
        }

    def get_status(self) -> dict:
        return {"name": self.device_name, "connected": self.is_connected}

    def get_result(self) -> dict:
        return self.result or {"status": "success", "message": self.message}

    def get_message(self) -> str:
        return self.message

    def start(self, oven_id: int):
        return self.control_oven(oven_id, OvenActionCode.START)

    def stop(self, oven_id: int):
        return self.control_oven(oven_id, OvenActionCode.STOP)


# ---------- Mock CentrifugeController ----------
class MockCentrifugeController:
    """离心机 Mock：connect/get_centrifuge_status/get_door_status/open_door/close_door/set_time/set_speed/start/stop 返回成功。"""

    def __init__(self, device_id: str = "01", host: str = None, port: int = None, timeout: int = None):
        self.device_name = "mock_modbus_centrifuge_" + device_id
        self.device_id = device_id
        self.is_connected = False
        self.message = "Mock 离心机"
        self.result = None
        self.status = DeviceStatus.UNKNOWN

    def connect(self):
        _mock_delay()
        self.is_connected = True
        self.message = "Mock 离心机连接成功"
        self.status = DeviceStatus.CONNECTED
        return True

    def disconnect(self):
        self.is_connected = False
        self.message = "Mock 离心机已断开"

    def get_centrifuge_status(self) -> CentrifugeStatus:
        return CentrifugeStatus.STOPPED

    def get_door_status(self) -> CentrifugeDoorStatus:
        return CentrifugeDoorStatus.CLOSED

    def get_running_status(self) -> dict:
        # 与 centrifuge_core._parse_status_data + get_running_status 一致，供 thermal_flow.get_summary 的 summary.centrifuge 使用
        return {
            "status": "success",
            "data": {
                "actual_rpm": 0,
                "centrifuge_force": 0,
                "run_time": 0,
                "run_state": CentrifugeStatus.STOPPED.value,
                "door_window": CentrifugeDoorStatus.CLOSED.value,
                "setted_rpm": 0,
                "setted_time": 0,
                "door_lid": 0,
                "rotor_state": 0,
                "remain_time": 0,
            },
        }

    def get_result(self) -> dict:
        if self.result is not None:
            return self.result
        return {"status": "success", "data": self.get_running_status().get("data", {})}

    def open_door(self) -> dict:
        _mock_delay()
        self.result = {"status": "success", "message": "离心机门打开成功"}
        return self.result

    def close_door(self) -> dict:
        _mock_delay()
        self.result = {"status": "success", "message": "离心机门关闭成功"}
        return self.result

    def set_time(self, time_min: int) -> dict:
        _mock_delay()
        self.result = {"status": "success", "message": f"设置时间 {time_min} 分钟"}
        return self.result

    def set_speed(self, rpm: int) -> dict:
        _mock_delay()
        self.result = {"status": "success", "message": f"设置转速 {rpm} RPM"}
        return self.result

    def start(self) -> dict:
        _mock_delay()
        self.result = {"status": "success", "message": "离心机启动成功"}
        self.status = DeviceStatus.RUNNING
        return self.result

    def stop(self) -> dict:
        _mock_delay()
        self.result = {"status": "success", "message": "离心机停止成功"}
        self.status = DeviceStatus.STOPPED
        return self.result

    def get_status(self) -> DeviceStatus:
        return self.status

    def get_message(self) -> str:
        return self.message or "Mock 离心机就绪"


# ---------- Mock XRDController ----------
class MockXRDController:
    """XRD 衍射仪 Mock：所有 API 返回成功；get_sample_status 返回允许上样/下样；get_current_acquire_data 返回模拟 2theta/intensity。"""

    def __init__(self, device_id: str = "01", host: str = None, port: int = None, timeout: int = None):
        self.device_name = "mock_socket_xrd_" + device_id
        self.device_id = device_id
        self.host = host or "127.0.0.1"
        self.port = port or 8009
        self.timeout = timeout
        self.is_connected = False
        self.message = "Mock XRD"
        self.socket = None
        self.xrd_status_cache = {}
        self._lock = threading.RLock()
        self._sample_id = None

    def connect(self):
        _mock_delay()
        self.is_connected = True
        self.message = "Mock XRD 连接成功"
        return True

    def disconnect(self):
        self.is_connected = False
        self.message = "Mock XRD 已断开"

    def get_sample_status(self) -> Dict[str, Any]:
        # 与 xrd_flow 中等待升压、电压稳定、测试完成 的判定字段一致，Mock 直接返回“就绪”便于快速通过
        return {
            "status": True,
            "Station": {"1": {"State": "Idle"}},
            "message": "ok",
            "xray status": "ready",
            "power status": True,
            "current voltage": 40.0,
            "current current": 40.0,
            "ready station": ["1", "2", "3", "4", "5"],  # 多样品时 len >= total_samples 即可通过
        }

    def get_sample_request(self) -> Dict[str, Any]:
        return {"status": True, "message": "允许上样"}

    def send_sample_ready(
        self,
        sample_id: Optional[str],
        start_theta: Optional[float],
        end_theta: Optional[float],
        increment: Optional[float],
        exp_time: Optional[float],
    ) -> Dict[str, Any]:
        _mock_delay()

        with self._lock:
            self._sample_id = sample_id

        return {"status": True, "message": "采集参数发送成功"}

    def get_sample_down(self, sample_station: int) -> Dict[str, Any]:
        _mock_delay()
        spec_folder = os.path.join("data", "spectra")
        import json
        with open(os.path.join(spec_folder, os.listdir(spec_folder)[random.randint(0, len(os.listdir(spec_folder))-1)]), "r") as f:
            spec = json.load(f)
        return {
            "status": True,
            "message": "下样成功",
            "id_number": self._sample_id,
            "2theta": spec["2theta"],
            "intensity": spec["intensity"],
            "timestamp": time.time(),
        }

    def send_sample_down_ready(self) -> Dict[str, Any]:
        _mock_delay()
        return {"status": True, "message": "下样完成"}

    def get_current_acquire_data(self) -> Dict[str, Any]:
        return {
            "status": True,
            "2theta": [10.0, 20.0, 30.0],
            "intensity": [100, 200, 150],
            "timestamp": time.time(),
        }

    def start_auto_mode(self, status: bool) -> Dict[str, Any]:
        _mock_delay()
        return {"status": True, "message": "自动模式设置成功"}

    def set_power_on(self) -> Dict[str, Any]:
        _mock_delay()
        return {"status": True, "message": "高压打开成功"}

    def set_voltage_current(self, voltage: float, current: float) -> Dict[str, Any]:
        _mock_delay()
        return {"status": True, "message": "电压电流设置成功"}

    def get_running_status(self) -> dict:
        # 与 xrd_core.get_running_status 一致：扁平 status_info，无 status/data 外壳，供 xrd_flow.get_summary 的 summary.xrd 使用
        return {
            "name": self.device_name,
            "connected": self.is_connected,
            "host": self.host,
            "port": self.port,
            "status": "idle",
            "xray_status": True,
            "power_status": True,
            "current_voltage": 40.0,
            "current_current": 40.0,
            "untest_station": [],
            "ready_station": ["1"],
        }


# ---------- Mock MixerController ----------
class MockMixerController:
    """配料设备 Mock：connect/add_task/get_task_info/batch_start_task/stop_task 返回成功；get_task_info 直接返回 COMPLETED 以便 flow 快速通过等待。"""

    def __init__(self, device_id: str = "01", api_base_url: str = None, username: str = None, password: str = None):
        self.device_name = "mock_restapi_mixer_" + device_id
        self.device_id = device_id
        self.is_connected = False
        self.message = "Mock 配料"
        self.current_task_id = None
        self.api_headers = {}

    def connect(self):
        _mock_delay()
        self.is_connected = True
        self.message = "Mock 配料设备连接成功"
        return True

    def disconnect(self):
        self.is_connected = False
        self.message = "Mock 配料已断开"

    def add_task(self, add_task_request) -> Dict[str, Any]:
        _mock_delay()
        self.current_task_id = 1
        data = AddTaskResponse(**{
            "code": 200,
            "msg": "success",
            "result": None,
            "data": None,
            "task_id": 1,
            "substance_shortage_list": {}
        })
        return {
            "status": "success",
            "data": data,
            "message": "任务创建成功",
        }

    def get_setup(self) -> Dict[str, Any]:
        _mock_delay()
        data = GetSetupResponse(**{
            "required_tray_code": False,
            "required_medium_code": False,
            "method_audit_log": True,
            "task_audit_log": True,
            "addition_timeout": 360,
            "accuracy": 0.5,
            "substance_shortage_nums": 5,
            "created_at": "2023-02-06T16:00:27",
            "updated_at": "2026-03-13T14:08:33",
            "weight_node": 45,
            "accuracy_30mL": 0.3,
            "accuracy_100mL": 0.3,
            "small_substance_shortage_nums": 100,
            "big_substance_shortage_nums": 500
        })
        return {"status": "success", "data": data, "message": "任务检查成功"}

    def get_resource_info(self) -> Dict[str, Any]:
        _mock_delay()
        data = GetResourceInfoResponse(**{
            "code": 200,
            "msg": "success",
            "result": None,
            "data": None,
            "resource_list": [
                {
                    "fid": 1,
                    "layout_code": "IPF1-1:-1",
                    "working_code": "",
                    "resource_type": "PF100M5R1C_2",
                    "substance": "",
                    "chemical_id": None,
                    "material_batch_number": None,
                    "initial_volume": 0.0,
                    "initial_weight": 0.0,
                    "cur_volume": 0.0,
                    "cur_weight": 0.0,
                    "available_volume": 0.0,
                    "available_weight": 0.0,
                    "tray_QR_code": "",
                    "QR_code": "",
                    "unit": "",
                    "source_layout_code": "IPF1-1:-1",
                    "with_magneton": False,
                    "usage_times": 0,
                    "status": 0,
                    "color": None,
                    "created_at": 1769063050,
                    "updated_at": 1773381468,
                    "with_cap": False,
                    "used": False
                },
                {
                    "fid": 17,
                    "layout_code": "IPF1-1:0",
                    "working_code": "",
                    "resource_type": "PF100M5R1C_2",
                    "substance": "Te",
                    "chemical_id": 37,
                    "material_batch_number": None,
                    "initial_volume": 0.0,
                    "initial_weight": 20000.0,
                    "cur_volume": 0.0,
                    "cur_weight": 25000.0,
                    "available_volume": 0.0,
                    "available_weight": 25000.0,
                    "tray_QR_code": "",
                    "QR_code": "",
                    "unit": "g",
                    "source_layout_code": "IPF1-1:0",
                    "with_magneton": False,
                    "usage_times": 0,
                    "status": 0,
                    "color": None,
                    "created_at": 1769064153,
                    "updated_at": 1773381468,
                    "with_cap": False,
                    "used": False
                },
                {
                    "fid": 2,
                    "layout_code": "IPF1-1:1",
                    "working_code": "",
                    "resource_type": "PF100M5R1C_2",
                    "substance": "Se",
                    "chemical_id": 45,
                    "material_batch_number": None,
                    "initial_volume": 0.0,
                    "initial_weight": 50000.0,
                    "cur_volume": 0.0,
                    "cur_weight": 36653.0,
                    "available_volume": 0.0,
                    "available_weight": 36853.0,
                    "tray_QR_code": "",
                    "QR_code": "",
                    "unit": "g",
                    "source_layout_code": "IPF1-1:1",
                    "with_magneton": False,
                    "usage_times": 0,
                    "status": 0,
                    "color": None,
                    "created_at": 1769063050,
                    "updated_at": 1774938444,
                    "with_cap": False,
                    "used": False
                },
                {
                    "fid": 3,
                    "layout_code": "IPF1-1:2",
                    "working_code": "",
                    "resource_type": "PF100M5R1C_2",
                    "substance": "Bi",
                    "chemical_id": 43,
                    "material_batch_number": None,
                    "initial_volume": 0.0,
                    "initial_weight": 50000.0,
                    "cur_volume": 0.0,
                    "cur_weight": 44656.8,
                    "available_volume": 0.0,
                    "available_weight": 44656.8,
                    "tray_QR_code": "",
                    "QR_code": "",
                    "unit": "g",
                    "source_layout_code": "IPF1-1:2",
                    "with_magneton": False,
                    "usage_times": 0,
                    "status": 0,
                    "color": None,
                    "created_at": 1769063050,
                    "updated_at": 1773381468,
                    "with_cap": False,
                    "used": False
                },
                {
                    "fid": 18,
                    "layout_code": "IPF1-1:4",
                    "working_code": "",
                    "resource_type": "PF100M5R1C_2",
                    "substance": "Ge",
                    "chemical_id": 41,
                    "material_batch_number": None,
                    "initial_volume": 0.0,
                    "initial_weight": 10000.0,
                    "cur_volume": 0.0,
                    "cur_weight": 7061.7,
                    "available_volume": 0.0,
                    "available_weight": 7061.7,
                    "tray_QR_code": "",
                    "QR_code": "",
                    "unit": "g",
                    "source_layout_code": "IPF1-1:4",
                    "with_magneton": False,
                    "usage_times": 0,
                    "status": 0,
                    "color": None,
                    "created_at": 1769064177,
                    "updated_at": 1773381468,
                    "with_cap": False,
                    "used": False
                },
                {
                    "fid": 15,
                    "layout_code": "IPF2-1:-1",
                    "working_code": "",
                    "resource_type": "PF30M5R1C_2",
                    "substance": "",
                    "chemical_id": None,
                    "material_batch_number": None,
                    "initial_volume": 0.0,
                    "initial_weight": 0.0,
                    "cur_volume": 0.0,
                    "cur_weight": 0.0,
                    "available_volume": 0.0,
                    "available_weight": 0.0,
                    "tray_QR_code": "",
                    "QR_code": "",
                    "unit": "",
                    "source_layout_code": "IPF2-1:-1",
                    "with_magneton": False,
                    "usage_times": 0,
                    "status": 0,
                    "color": None,
                    "created_at": 1769063112,
                    "updated_at": 1773380804,
                    "with_cap": False,
                    "used": False
                },
                {
                    "fid": 41,
                    "layout_code": "IPF2-1:1",
                    "working_code": "",
                    "resource_type": "PF30M5R1C_2",
                    "substance": "Ti",
                    "chemical_id": 55,
                    "material_batch_number": None,
                    "initial_volume": 0.0,
                    "initial_weight": 15000.0,
                    "cur_volume": 0.0,
                    "cur_weight": 14004.0,
                    "available_volume": 0.0,
                    "available_weight": 15000.0,
                    "tray_QR_code": "",
                    "QR_code": "",
                    "unit": "g",
                    "source_layout_code": "IPF2-1:1",
                    "with_magneton": False,
                    "usage_times": 0,
                    "status": 0,
                    "color": None,
                    "created_at": 1773380804,
                    "updated_at": 1773382957,
                    "with_cap": False,
                    "used": False
                },
                {
                    "fid": 16,
                    "layout_code": "IPF2-1:2",
                    "working_code": "",
                    "resource_type": "PF30M5R1C_2",
                    "substance": "Sb",
                    "chemical_id": 44,
                    "material_batch_number": None,
                    "initial_volume": 0.0,
                    "initial_weight": 50000.0,
                    "cur_volume": 0.0,
                    "cur_weight": 45651.2,
                    "available_volume": 0.0,
                    "available_weight": 45651.2,
                    "tray_QR_code": "",
                    "QR_code": "",
                    "unit": "g",
                    "source_layout_code": "IPF2-1:2",
                    "with_magneton": False,
                    "usage_times": 0,
                    "status": 0,
                    "color": None,
                    "created_at": 1769063112,
                    "updated_at": 1773380804,
                    "with_cap": False,
                    "used": False
                },
                {
                    "fid": 55,
                    "layout_code": "IT-1:-1",
                    "working_code": "",
                    "resource_type": "CC10R10C",
                    "substance": "",
                    "chemical_id": None,
                    "material_batch_number": None,
                    "initial_volume": 0.0,
                    "initial_weight": 0.0,
                    "cur_volume": 0.0,
                    "cur_weight": 0.0,
                    "available_volume": 0.0,
                    "available_weight": 0.0,
                    "tray_QR_code": "",
                    "QR_code": "",
                    "unit": "",
                    "source_layout_code": "IT-1:-1",
                    "with_magneton": False,
                    "usage_times": 0,
                    "status": 0,
                    "color": None,
                    "created_at": 1774938494,
                    "updated_at": 1774938494,
                    "with_cap": False,
                    "used": False
                },
                {
                    "fid": 56,
                    "layout_code": "IT-1:0",
                    "working_code": "",
                    "resource_type": "CC10R10C",
                    "substance": "",
                    "chemical_id": None,
                    "material_batch_number": None,
                    "initial_volume": 0.0,
                    "initial_weight": 0.0,
                    "cur_volume": 0.0,
                    "cur_weight": 0.0,
                    "available_volume": 0.0,
                    "available_weight": 0.0,
                    "tray_QR_code": "",
                    "QR_code": "",
                    "unit": "",
                    "source_layout_code": "IT-1:0",
                    "with_magneton": False,
                    "usage_times": 0,
                    "status": 0,
                    "color": None,
                    "created_at": 1774938494,
                    "updated_at": 1774938494,
                    "with_cap": False,
                    "used": False
                },
                {
                    "fid": 57,
                    "layout_code": "IT-1:1",
                    "working_code": "",
                    "resource_type": "CC10R10C",
                    "substance": "",
                    "chemical_id": None,
                    "material_batch_number": None,
                    "initial_volume": 0.0,
                    "initial_weight": 0.0,
                    "cur_volume": 0.0,
                    "cur_weight": 0.0,
                    "available_volume": 0.0,
                    "available_weight": 0.0,
                    "tray_QR_code": "",
                    "QR_code": "",
                    "unit": "",
                    "source_layout_code": "IT-1:1",
                    "with_magneton": False,
                    "usage_times": 0,
                    "status": 0,
                    "color": None,
                    "created_at": 1774938494,
                    "updated_at": 1774938494,
                    "with_cap": False,
                    "used": False
                },
                {
                    "fid": 58,
                    "layout_code": "IT-1:2",
                    "working_code": "",
                    "resource_type": "CC10R10C",
                    "substance": "",
                    "chemical_id": None,
                    "material_batch_number": None,
                    "initial_volume": 0.0,
                    "initial_weight": 0.0,
                    "cur_volume": 0.0,
                    "cur_weight": 0.0,
                    "available_volume": 0.0,
                    "available_weight": 0.0,
                    "tray_QR_code": "",
                    "QR_code": "",
                    "unit": "",
                    "source_layout_code": "IT-1:2",
                    "with_magneton": False,
                    "usage_times": 0,
                    "status": 0,
                    "color": None,
                    "created_at": 1774938494,
                    "updated_at": 1774938494,
                    "with_cap": False,
                    "used": False
                },
                {
                    "fid": 59,
                    "layout_code": "IT-1:10",
                    "working_code": "",
                    "resource_type": "CC10R10C",
                    "substance": "",
                    "chemical_id": None,
                    "material_batch_number": None,
                    "initial_volume": 0.0,
                    "initial_weight": 0.0,
                    "cur_volume": 0.0,
                    "cur_weight": 0.0,
                    "available_volume": 0.0,
                    "available_weight": 0.0,
                    "tray_QR_code": "",
                    "QR_code": "",
                    "unit": "",
                    "source_layout_code": "IT-1:10",
                    "with_magneton": False,
                    "usage_times": 0,
                    "status": 0,
                    "color": None,
                    "created_at": 1774938494,
                    "updated_at": 1774938494,
                    "with_cap": False,
                    "used": False
                },
                {
                    "fid": 60,
                    "layout_code": "IT-1:11",
                    "working_code": "",
                    "resource_type": "CC10R10C",
                    "substance": "",
                    "chemical_id": None,
                    "material_batch_number": None,
                    "initial_volume": 0.0,
                    "initial_weight": 0.0,
                    "cur_volume": 0.0,
                    "cur_weight": 0.0,
                    "available_volume": 0.0,
                    "available_weight": 0.0,
                    "tray_QR_code": "",
                    "QR_code": "",
                    "unit": "",
                    "source_layout_code": "IT-1:11",
                    "with_magneton": False,
                    "usage_times": 0,
                    "status": 0,
                    "color": None,
                    "created_at": 1774938494,
                    "updated_at": 1774938494,
                    "with_cap": False,
                    "used": False
                }
            ]
        })
        return {"status": "success", "data": data, "message": "任务检查成功"}

    def get_chemicals(self) -> Dict[str, Any]:
        _mock_delay()
        with open('data/mock/get_chemicallist-output.json', 'r') as f:
            data = GetChemicalsResponse(**json.load(f))
        return {"status": "success", "data": data, "message": "任务检查成功"}

    def get_task_info(self, task_id: Optional[int] = None) -> Dict[str, Any]:
        task_id = task_id or self.current_task_id or 1
        data = GetTaskInfoResponse(
            task_id=task_id,
            task_name="MockTask",
            unit_save_json="{}",
            status=TaskStatus.COMPLETED.value,
            creator="mock",
            task_begin_time=None,
            task_end_time=None,
            created_at=int(time.time()),
            updated_at=int(time.time()),
            is_audit_log=1,
            task_template_id_list=[],
            task_setup=TaskSetup(),
            unit_list=[],
        )
        return {"status": "success", "data": data, "message": "ok"}

    def batch_check_task(self, task_id_list: List[int]) -> Dict[str, Any]:
        _mock_delay()
        data = BatchCheckTaskResponse(**{
            "code": 200,
            "msg": "success",
            "result": None,
            "data": None,
            "prompt_msg": None
        })
        return {"status": "success", "data": data, "message": "任务检查成功"}

    def batch_start_task(self, task_id_list: List[int]) -> Dict[str, Any]:
        _mock_delay()
        data = {
            "code": 200,
            "msg": "success",
            "result": None,
            "data": None,
            "prompt_msg": None
        }
        return {"status": "success", "data": data, "message": "任务启动成功"}

    def stop_task(self, task_id: int) -> Dict[str, Any]:
        _mock_delay()
        return {"status": "success", "message": "任务已停止"}

    def get_running_status(self) -> dict:
        # 与 mixer_core.get_running_status 一致：有任务时返回 get_task_info 结构，供 mix_flow.get_summary 的 summary.mixer 使用
        if not self.is_connected:
            return {"status": "error", "message": "设备未连接"}
        task_id = self.current_task_id or 1
        return self.get_task_info(task_id)


# ---------- 工厂：根据 config 返回真实或 Mock 单例 ----------
def get_robot_controller():
    import config
    if getattr(config, "MOCK_DEVICES", False):
        return MockRobotController()
    from .robot_core import robot_controller
    return robot_controller


def get_door_controller():
    import config
    if getattr(config, "MOCK_DEVICES", False):
        return MockDoorController()
    from .door_core import door_controller
    return door_controller


def get_oven_controller():
    import config
    if getattr(config, "MOCK_DEVICES", False):
        return MockOvenController()
    from .oven_core import oven_controller
    return oven_controller


def get_centrifuge_controller():
    import config
    if getattr(config, "MOCK_DEVICES", False):
        return MockCentrifugeController()
    from .centrifuge_core import centrifuge_controller
    return centrifuge_controller


def get_xrd_controller():
    import config
    if getattr(config, "MOCK_DEVICES", False):
        return MockXRDController()
    from .xrd_core import xrd_controller
    return xrd_controller


def get_mixer_controller():
    import config
    if getattr(config, "MOCK_DEVICES", False):
        return MockMixerController()
    from .mixer_core import mixer_controller
    return mixer_controller
