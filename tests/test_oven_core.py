"""
ovenController (devices.oven_core) 单元测试

运行方式（在项目根目录）:
    pytest tests/test_oven_core.py -v
    pytest tests/test_oven_core.py -v -k "connect"   # 只跑含 connect 的用例
"""
import pytest
from unittest.mock import patch, MagicMock

from devices.oven_core import OvenController
from devices.base import DeviceStatus

# ---------- Fixtures ----------

@pytest.fixture
def controller():
    """未连接的 OvenController 实例，使用显式参数避免依赖 config"""
    return OvenController(
        device_id="99",
        req_addr="tcp://192.168.0.146:49206",
        sub_addr="tcp://192.168.0.146:49200",
        ctrl_addr="tcp://192.168.0.146:49201"
    )

# ---------- connect / disconnect ----------

class TestConnectDisconnect:
    """连接与断开"""

    def test_connect_success(self, controller: OvenController):
        ok = controller.connect()
        print(controller.message)
        assert ok is True
        assert controller.is_connected is True
        assert controller.status == DeviceStatus.connected
        assert "连接成功" in controller.message

    def test_disconnect_clears_state(self, controller: OvenController):
        controller.connect()
        controller.disconnect()
        assert controller.is_connected is False
        assert controller.status == DeviceStatus.disconnected
        assert "已断开连接" in controller.message