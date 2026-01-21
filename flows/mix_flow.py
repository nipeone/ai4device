"""
混合料工作流
"""
import time
import threading
from typing import Dict, Any, List, Optional
from datetime import datetime

from devices.mixer_core import MixerController, mixer_controller
from logger import sys_logger as logger

class MixFlowManager:
    """混合料工作流管理器"""

    def __init__(self, mix_controller: MixerController, logger=logger):
        self.mix_controller = mix_controller
        self.logger = logger
        self.running = False
        self.current_step_info = "就绪"
        self.thread = None
        
        # 确认信号事件（用于人工确认步骤）
        self.confirm_event = threading.Event()
        self.confirm_event.set()  # 默认设置为True
        
    def user_confirm(self):
        """前端调用的确认方法"""
        self.logger.log(">>> 人工已确认，流程继续 <<<", "SUCCESS")
        self.confirm_event.set()
        
    def _log_step(self, message: str, level: str = "INFO"):
        """记录步骤日志"""
        self.current_step_info = message
        self.logger.log(f"[配料流程] {message}", level)
        
    def _wait_for_confirm(self, message: str, timeout: Optional[float] = None):
        """等待人工确认"""
        self._log_step(f"等待确认: {message}", "WARN")
        self.confirm_event.clear()
        
        start_time = time.time()
        while not self.confirm_event.is_set():
            if not self.running:
                return False
            if timeout and (time.time() - start_time) > timeout:
                self._log_step(f"确认超时: {message}", "ERROR")
                return False
            time.sleep(0.5)
        
        self._log_step(f"确认通过: {message}", "SUCCESS")
        return True
    
    def _check_device_ready(self) -> bool:
        """检查设备是否就绪"""


mix_flow_manager = MixFlowManager(mixer_controller)