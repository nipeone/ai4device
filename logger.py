import time
from datetime import datetime
from typing import Dict, Any, List
from loguru import logger
import sys


# ==========================================
# 新增: 日志管理器 (用于前端显示和loguru集成)
# ==========================================
class SystemLogger:
    def __init__(self):
        self.logs = []

        # 配置loguru日志记录到控制台和文件
        logger.remove()  # 移除默认处理器
        # 1. 控制台输出
        logger.add(
            sys.stdout,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
            level="INFO"
        )
        
        # 2. 文件输出
        logger.add(
            "logs/app_{time:YYYY-MM-DD}.log",  # 按日期命名（粒度到天）
            rotation="10 MB",                  # 单个文件达到10MB时滚动
            retention="10 days",               # 保留10天日志
            format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
            encoding="utf-8",                  # 新增：指定编码，避免中文乱码
            compression="zip",                 # 新增：过期日志自动压缩，节省空间
            enqueue=True                       # 新增：异步写入，避免阻塞程序
        )

    def log(self, msg: str, level: str = "INFO"):
        """记录日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        entry = {"time": timestamp, "level": level, "msg": msg}
        # 插入到最前面，保留最近50条
        self.logs.insert(0, entry)
        if len(self.logs) > 50:
            self.logs.pop()

        # 使用loguru记录日志
        if level.upper() == "INFO":
            logger.info(msg)
        elif level.upper() == "WARNING" or level.upper() == "WARN":
            logger.warning(msg)
        elif level.upper() == "ERROR":
            logger.error(msg)
        elif level.upper() == "DEBUG":
            logger.debug(msg)
        elif level.upper() == "CRITICAL":
            logger.critical(msg)
        else:
            logger.info(f"[{level}] {msg}")  # 默认作为info处理

    def info(self, msg: str):
        """记录信息日志"""
        self.log(msg, "INFO")

    def warning(self, msg: str):
        """记录警告日志"""
        self.log(msg, "WARNING")

    def error(self, msg: str):
        """记录错误日志"""
        self.log(msg, "ERROR")

    def debug(self, msg: str):
        """记录调试日志"""
        self.log(msg, "DEBUG")

    def critical(self, msg: str):
        """记录严重错误日志"""
        self.log(msg, "CRITICAL")

sys_logger = SystemLogger()