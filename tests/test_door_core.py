"""
doorController (devices.door_core) 单元测试

运行方式（在项目根目录）:
    pytest tests/test_door_core.py -v
    pytest tests/test_door_core.py -v -k "connect"   # 只跑含 connect 的用例
"""
import pytest
from unittest.mock import patch, MagicMock

from devices.door_core import DoorController
from devices.base import DeviceStatus
from schemas.door import DoorActionCode

# ---------- Fixtures ----------

@pytest.fixture
def controller():
    """未连接的 RobotController 实例，使用显式参数避免依赖 config"""
    return DoorController(
        device_id="99",
        target_address="tcp://192.168.0.2:49202"
    )

# ---------- connect / disconnect ----------

class TestConnectDisconnect:
    """连接与断开"""

    def test_connect_success(self, controller: DoorController):
        ok = controller.connect()
        print(controller.message)
        assert ok is True
        assert controller.is_connected is True
        assert controller.status == DeviceStatus.connected
        assert "连接成功" in controller.message

    def test_disconnect_clears_state(self, controller: DoorController):
        controller.connect()
        controller.disconnect()
        assert controller.is_connected is False
        assert controller.status == DeviceStatus.disconnected
        assert "已断开连接" in controller.message

class TestGetDoorStatus:

    def test_get_door_status(self, controller: DoorController):
        controller.connect()
        result = controller.get_door_status(1)
        print(result)
        assert result.get("status") == "success"

    def test_control_door(self, controller: DoorController):
        controller.connect()
        result = controller.control_door(1, DoorActionCode.CLOSE)
        print(result)
        assert result.get("status") == "success"