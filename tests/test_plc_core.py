"""
robotController (devices.xrd_core) 单元测试

运行方式（在项目根目录）:
    pytest tests/test_plc_core.py -v
    pytest tests/test_plc_core.py -v -k "connect"   # 只跑含 connect 的用例
"""
import pytest
from unittest.mock import patch, MagicMock

from devices.robot_core import RobotController
from devices.base import DeviceStatus

# ---------- Fixtures ----------

@pytest.fixture
def xrd():
    """未连接的 RobotController 实例，使用显式参数避免依赖 config"""
    return RobotController(
        device_id="99",
        host="192.168.0.205",
        port=102,
        timeout=10
    )