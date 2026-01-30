"""
doorController (devices.centrifuge_core) 单元测试

运行方式（在项目根目录）:
    pytest tests/test_cent_core.py -v
    pytest tests/test_cent_core.py -v -k "connect"   # 只跑含 connect 的用例
"""
import pytest
from unittest.mock import patch, MagicMock

from devices.centrifuge_core import CentrifugeController
from devices.base import DeviceStatus
from schemas.door import DoorActionCode

@pytest.fixture
def controller():
    """未连接的 RobotController 实例，使用显式参数避免依赖 config"""
    return CentrifugeController(
        host="192.168.0.140",
        port=8000,
        timeout=10
    )

# ---------- connect / disconnect ----------

class TestConnectDisconnect:
    """连接与断开"""

    def test_connect_success(self, controller: CentrifugeController):
        ok = controller.connect()
        assert ok is True
        assert controller.is_connected is True
        assert controller.status == DeviceStatus.connected
        assert "连接成功" in controller.message
        controller.disconnect()
        assert controller.is_connected is False
        assert "断开连接" in controller.message

    def test_connect_disconnect(self, controller: CentrifugeController):
        '''try 3 times'''
        controller.connect()
        controller.disconnect()
        controller.connect()
        controller.disconnect()
        controller.connect()
        controller.disconnect()
        assert controller.is_connected is False

    def test_get_status(self, controller: CentrifugeController):
        ok = controller.connect()
        assert ok is True
        data = controller.get_running_status()
        print(data)
        assert data.get("status") == "success"
        controller.disconnect()

