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
# 可以添加其他配置项
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
