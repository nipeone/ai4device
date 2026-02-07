"""
XRDController (devices.xrd_core) 单元测试

运行方式（在项目根目录）:
    pytest tests/test_xrd_core.py -v
    pytest tests/test_xrd_core.py -v -k "connect"   # 只跑含 connect 的用例
"""
import pytest
from unittest.mock import patch, MagicMock

from devices.xrd_core import XRDController
from devices.base import DeviceStatus


# ---------- Fixtures ----------

@pytest.fixture
def xrd():
    """未连接的 XRDController 实例，使用显式参数避免依赖 config"""
    return XRDController(
        device_id="99",
        host="192.168.0.144",
        port=8009,
        timeout=10
    )

# ---------- connect / disconnect ----------

class TestConnectDisconnect:
    """连接与断开"""

    def test_connect_success(self, xrd: XRDController):
        ok = xrd.connect()
        assert ok is True
        assert xrd.is_connected is True
        assert xrd.status == DeviceStatus.CONNECTED
        assert "连接成功" in xrd.message

    def test_disconnect_clears_state(self, xrd: XRDController):
        xrd.connect()
        xrd.disconnect()
        assert xrd.is_connected is False
        assert xrd.status == DeviceStatus.DISCONNECTED
        assert "已断开连接" in xrd.message