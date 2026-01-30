"""
混合料工作流
"""
import time
import threading
from typing import Dict, Any, List, Optional
from datetime import datetime

from schemas.mixer import AddTaskRequest, GetTaskInfoResponse
from devices.mixer_core import MixerController, mixer_controller
from logger import sys_logger as logger

class MixFlowManager:
    """配料工序工作流管理器"""

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
    
    def _wait_for_task_finished(self, task_id: int, check_interval: float = 5.0):
        """等待任务完成"""
        self._log_step(f"等待任务完成: {task_id}", "INFO")
        start_time = time.time()
        max_wait_time = 60 * 60 * 2 # 最多等待1hour

        while self.running:
            if time.time() - start_time > max_wait_time:
                self._log_step("等待任务完成超时", "ERROR")
                return False
            info =  self.mix_controller.get_task_info(task_id)
            if info.get("status") == "success":
                data: GetTaskInfoResponse = info.get("data")
                if data.status == 2:
                    self._log_step(f"任务完成: {task_id}", "SUCCESS")
                    return True
                else:
                    self._log_step(f"任务进行中: {task_id}", "INFO")

            time.sleep(check_interval)
        return False

    def _check_device_ready(self) -> bool:
        """检查设备是否就绪"""
        if not self.mix_controller.is_connected:
            self._log_step("设备未连接，尝试连接...", "WARN")
            if not self.mix_controller.connect():
                self._log_step(f"设备连接失败: {self.mix_controller.message}", "ERROR")
                return False
            else:
                self._log_step("设备连接成功")
        self.running = True
        return True

    def run(self, mixer_task_model: AddTaskRequest):

        ########## 步骤0: 准备设备 ##########
        self._log_step("步骤0: 准备设备...", "INFO")
        if not self._check_device_ready():
            return {"status": False, "message": "设备未就绪"}

        self._log_step("开始配料流程", "INFO")
        # if not self._wait_for_confirm("请确认配料设备就绪，然后点击确认", timeout=300):
        #     return {"status": False, "message": "配料设备就绪确认超时或取消"}

        ########## 步骤1: 创建任务  ##########
        self._log_step("配料设备就绪，开始配料", "INFO")
        rtn = self.mix_controller.add_task(mixer_task_model)
        if rtn.get("status") != "success":
            self._log_step(f"配料任务创建失败: {rtn.get('message')}", "ERROR")
            return {"status": False, "message": f"配料任务创建失败: {rtn.get('message')}"}

        task_id = rtn.get("data").task_id
        self._log_step(f"新任务创建成功，task_id = {task_id}", "SUCCESS")

        status = self.mix_controller.get_task_info(task_id)
        self._log_step(f"任务信息: {status}", "SUCCESS")

        ########## 步骤2: 等待启动配料任务 ##########
        self._log_step("步骤2: 等待启动配料任务...", "INFO")
        self.mix_controller.batch_start_task([task_id])
        if rtn.get("status") != "success":
            self._log_step(f"配料任务启动失败: {rtn.get('message')}", "ERROR")
            return {"status": False, "message": f"配料任务启动失败: {rtn.get('message')}"}
        self._log_step(f"配料任务启动成功: {rtn.get('data')}", "SUCCESS")

        self._log_step("等待任务完成...", "INFO")
        if not self._wait_for_task_finished(task_id):
            self._log_step(f"任务超时: {task_id}", "ERROR")
            self.running = False
            return {"status": False, "message": f"任务超时: {task_id}"}

        # self._wait_for_confirm("请确认配料完成，然后点击确认", timeout=300)

        ########## 步骤3: 停止任务 ##########
        self._log_step(f"停止当前任务")
        self.mix_controller.stop_task(mixer_task_model.task_id)
        # self.mix_controller.cancel_task(mixer_task_model.task_id)
        self._log_step("配料完成，结束流程", "SUCCESS")

        self.running = False
        return {"status": True, "message": "配料流程结束"}

mix_flow_mgr = MixFlowManager(mixer_controller)