"""
配置文件
从环境变量中加载配置，支持 .env 文件
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# 加载 .env 文件
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

# ===================== 应用配置 =====================
APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("APP_PORT", "8113"))
APP_DEBUG = os.getenv("APP_DEBUG", "False").lower() == "true"

# ===================== PLC 配置 =====================
PLC_IP = os.getenv("PLC_IP", "192.168.0.205")
PLC_PORT = int(os.getenv("PLC_PORT", "102"))

# ===================== 离心机配置 =====================
CENTRIFUGE_HOST = os.getenv("CENTRIFUGE_HOST", "192.168.0.140")
CENTRIFUGE_PORT = int(os.getenv("CENTRIFUGE_PORT", "8000"))
CENTRIFUGE_TIMEOUT = int(os.getenv("CENTRIFUGE_TIMEOUT", "5"))

# ===================== 防护门配置 =====================
DOOR_TARGET_ADDRESS = os.getenv("DOOR_TARGET_ADDRESS", "tcp://127.0.0.1:49202")

# ===================== 高温炉配置 =====================
FURNACE_REQ_ADDR = os.getenv("FURNACE_REQ_ADDR", "tcp://127.0.0.1:49206")
FURNACE_SUB_ADDR = os.getenv("FURNACE_SUB_ADDR", "tcp://127.0.0.1:49200")
FURNACE_CTRL_ADDR = os.getenv("FURNACE_CTRL_ADDR", "tcp://127.0.0.1:49201")

# ===================== 高温炉曲线点地址配置 =====================
FURNACE_DB_PATH = os.getenv("FURNACE_DB_PATH", "assets/oven_curve.sqlite")

# ===================== 实验与 XRD 结果持久化 =====================
EXPERIMENT_DB_PATH = os.getenv("EXPERIMENT_DB_PATH", "assets/experiment.sqlite")

# ===================== 配料设备配置 =====================
MIXER_API_BASE_URL = os.getenv("MIXER_API_BASE_URL", "http://127.0.0.1:4669")
MIXER_USERNAME = os.getenv("MIXER_USERNAME", "admin")
MIXER_PASSWORD = os.getenv("MIXER_PASSWORD", "admin")
MIXER_TIMEOUT = int(os.getenv("MIXER_TIMEOUT", "30"))

# ===================== XRD设备配置 =====================
XRD_HOST = os.getenv("XRD_HOST", "192.168.8.127")
XRD_PORT = int(os.getenv("XRD_PORT", "8009"))
XRD_TIMEOUT = int(os.getenv("XRD_TIMEOUT", "5"))

# ===================== 日志配置 =====================
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "logs/app.log")

# ===================== 其他配置 =====================
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

# ===================== 本地测试 / Mock 模式 =====================
# 设为 true 时，实验流程不连接真实设备，各子流程（配料/热处理/XRD）仅模拟成功，用于本地完整跑通 API
MOCK_DEVICES = os.getenv("MOCK_DEVICES", "false").lower() in ("true", "1", "yes")
MOCK_STEP_DELAY = float(os.getenv("MOCK_STEP_DELAY", "1.0"))  # 每步模拟耗时（秒），便于观察阶段切换
# 加热炉启动/停止后，等待状态变为 RUNNING/STOPPED 的超时（秒）。多炉并行时设备响应快慢不一，过短易误报「启动后状态异常」
OVEN_STATUS_TRANSITION_TIMEOUT_SEC = float(os.getenv("OVEN_STATUS_TRANSITION_TIMEOUT_SEC", "120"))
# 燃烧等待时间上限（秒），0 表示不设上限、按曲线真实时长等待。本地/Mock 时可设 BURN_WAIT_CAP_SEC=30 避免长时间阻塞
BURN_WAIT_CAP_SEC = float(os.getenv("BURN_WAIT_CAP_SEC", "0"))
# XRD 等待时间上限（秒），0 表示不设上限。作用于：等待测试完成、等待升压、等待电压电流稳定。Mock 时可设 10~20 避免长时间阻塞
XRD_WAIT_CAP_SEC = float(os.getenv("XRD_WAIT_CAP_SEC", "0"))
