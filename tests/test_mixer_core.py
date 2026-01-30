"""
MixerController (devices.mixer_core) 单元测试

运行方式（在项目根目录）:
    pytest tests/test_mixer_core.py -v
    pytest tests/test_mixer_core.py -v -k "connect"   # 只跑含 connect 的用例
"""
import pytest
from unittest.mock import patch, MagicMock

from devices.mixer_core import MixerController
from devices.base import DeviceStatus
from schemas.mixer import AddTaskRequest


# ---------- Fixtures ----------

@pytest.fixture
def api_base():
    """配料 API 基础地址（测试用）"""
    return "http://192.168.3.5:4669"


@pytest.fixture
def mixer(api_base):
    """未连接的 MixerController 实例，使用显式参数避免依赖 config"""
    return MixerController(
        device_id="99",
        api_base_url=api_base,
        username="admin",
        password="admin"
    )


@pytest.fixture
def token_response():
    """connect 成功时的 Token 响应"""
    return MagicMock(
        status_code=200,
        json=lambda: {
            "access_token": "fake_token_123",
            "token_type": "Bearer"
        }
    )


# ---------- 初始化与属性 ----------

class TestMixerControllerInit:
    """初始化与属性"""

    def test_init_with_params(self, api_base):
        c = MixerController(
            device_id="01",
            api_base_url=api_base,
            username="u",
            password="p"
        )
        assert c.device_id == "01"
        assert c.device_name == "restapi_mixer_01"
        assert c.api_base_url == api_base
        assert c.username == "u"
        assert c.password == "p"
        assert c.is_connected is False
        assert c.current_task_id is None
        assert c.api_headers.get("Authorization") == ""

    def test_init_default_auth_headers(self, mixer):
        assert mixer.api_headers == {
            "Content-Type": "application/json",
            "Authorization": ""
        }


# ---------- connect / disconnect ----------

class TestConnectDisconnect:
    """连接与断开"""

    def test_connect_success(self, mixer: MixerController):
        # with patch("devices.mixer_core.requests.post", return_value=token_response):
        ok = mixer.connect()
        assert ok is True
        assert mixer.is_connected is True
        assert mixer.status == DeviceStatus.connected
        assert mixer.api_token_type == "bearer"
        assert "连接成功" in mixer.message

    def test_connect_fail_status_code(self, mixer):
        resp = MagicMock(status_code=401, json=lambda: {})
        with patch("devices.mixer_core.requests.post", return_value=resp):
            ok = mixer.connect()
        assert ok is False
        assert mixer.is_connected is False
        assert "获取Token失败" in mixer.message

    def test_connect_request_exception(self, mixer):
        import requests
        with patch("devices.mixer_core.requests.post", side_effect=requests.exceptions.ConnectionError("network error")):
            ok = mixer.connect()
        assert ok is False
        assert mixer.is_connected is False
        assert "network error" in mixer.message

    def test_disconnect_clears_state(self, mixer, token_response):
        with patch("devices.mixer_core.requests.post", return_value=token_response):
            mixer.connect()
        mixer.disconnect()
        assert mixer.is_connected is False
        assert mixer.api_token is None
        assert mixer.api_token_type is None
        assert mixer.api_headers == {}
        assert mixer.status == DeviceStatus.disconnected
        assert "已断开连接" in mixer.message


# ---------- get_task_info ----------

class TestGetTaskInfo:
    """获取任务信息"""

    def test_get_task_info_when_disconnected(self, mixer: MixerController):
        out = mixer.get_task_info(task_id=150)
        assert out["status"] == "error"
        assert "未连接" in out["message"]

    def test_get_task_info_success(self, mixer: MixerController):
        ok = mixer.connect()
        assert ok is True
        out = mixer.get_task_info(task_id=150)
        assert out["status"] == "success"
        assert out["data"].task_id == 150
        assert out["data"].status == 0

# ---------- add_task ----------

class TestAddTask:
    """创建任务"""

    def test_add_task_when_disconnected(self, mixer:MixerController):
        out = mixer.add_task(AddTaskRequest(task_name="t1"))
        assert out["status"] == "error"
        assert "未连接" in out["message"]

    def test_add_task_success(self, mixer: MixerController):
        ok = mixer.connect()
        assert ok is True
        out = mixer.add_task(AddTaskRequest(task_name="t1"))
        assert out["status"] == "success"
        mixer.get_task_info(out["data"].task_id)
        assert mixer.current_task_id == out["data"].task_id
        assert mixer.current_task_status == 0

    

