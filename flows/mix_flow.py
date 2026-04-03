"""
混合料工作流
"""
import time
import threading
from typing import Dict, Any, List, Optional
from datetime import datetime

from schemas.mixer import AddTaskRequest, GetTaskInfoResponse, TaskStatus
from devices.mixer_core import MixerController
from devices.mock_devices import get_mixer_controller
from logger import sys_logger as logger

class MixFlowManager:
    """配料工序工作流管理器"""

    def __init__(self, mix_controller: MixerController, logger=logger):
        self.mix_controller = mix_controller
        self.logger = logger
        self.running = False
        self._stop_requested = False  # 由 stop() 置位，run() 入口检查后清空，与 thermal_flow/xrd_flow 一致
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
        max_wait_time = 60 * 60 * 2 # 最多等待2hour

        while self.running:
            if time.time() - start_time > max_wait_time:
                self._log_step("等待任务完成超时", "ERROR")
                return False
            info =  self.mix_controller.get_task_info(task_id)
            if info.get("status") == "success":
                data: GetTaskInfoResponse = info.get("data")
                if TaskStatus(data.status) == TaskStatus.COMPLETED:
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

        return True

    def _return_with_error(self, message: str) -> dict:
        """返回错误结果"""
        self.running = False
        return {"status": False, "message": message}

    def run(self, mixer_task_model: AddTaskRequest):
        ''' 按照以下顺序执行：
        ## 执行顺序
        1. 点击创建任务时
          1. GetSetUp
        2. 点击保存任务时
          1. AddTask
          2. GetResourceInfo
          3. GetTaskInfo
          4. GetResourceInfo
          5. GetSetUp
        3. 点击启动任务时
          1. BatchCheckTask
          2. BatchStartTask
        '''

        try:
            if self._stop_requested:
                self._stop_requested = False
                return self._return_with_error("用户停止实验")
            self.running = True
            ########## 步骤0: 准备设备 ##########
            self._log_step("步骤0: 准备设备...", "INFO")
            if not self._check_device_ready():
                return self._return_with_error("设备未就绪")
            if not self.running:
                return self._return_with_error("用户停止实验")

            self._log_step("开始配料流程", "INFO")
            # if not self._wait_for_confirm("请确认配料设备就绪，然后点击确认", timeout=300):
            #     return {"status": False, "message": "配料设备就绪确认超时或取消"}

            ########## 新增步骤: SetUp  ##########
            self.mix_controller.get_setup()

            ########## 步骤1: 创建任务  ##########
            if not self.running:
                return self._return_with_error("用户停止实验")
            self._log_step("配料设备就绪，开始配料", "INFO")
            rtn = self.mix_controller.add_task(mixer_task_model)
            if rtn.get("status") != "success":
                self._log_step(f"配料任务创建失败: {rtn.get('message')}", "ERROR")
                return self._return_with_error(f"配料任务创建失败: {rtn.get('message')}")

            task_id = rtn.get("data").task_id
            self._log_step(f"新任务创建成功，task_id = {task_id}", "SUCCESS")

            resource_info = self.mix_controller.get_resource_info()
            self._log_step(f"资源信息: 获取成功", "SUCCESS")

            status = self.mix_controller.get_task_info(task_id)
            self._log_step(f"任务信息: {status}", "SUCCESS")

            resource_info = self.mix_controller.get_resource_info()
            self._log_step(f"资源信息: 获取成功", "SUCCESS")

            setup = self.mix_controller.get_setup()
            self._log_step(f"设置信息: 获取成功", "SUCCESS")


            ########## 步骤2: 等待启动配料任务 ##########
            if not self.running:
                return self._return_with_error("用户停止实验")
            self._log_step("步骤2: 等待启动配料任务...", "INFO")
            check_rtn = self.mix_controller.batch_check_task([task_id])
            if check_rtn.get("status") != "success":
                self._log_step(f"配料任务检查失败: {check_rtn.get('message')}", "ERROR")
                return self._return_with_error(f"配料任务检查失败: {check_rtn.get('message')}")
            self._log_step(f"配料任务检查成功: {check_rtn.get('data')}", "SUCCESS")

            start_rtn = self.mix_controller.batch_start_task([task_id])
            if start_rtn.get("status") != "success":
                self._log_step(f"配料任务启动失败: {start_rtn.get('message')}", "ERROR")
                return self._return_with_error(f"配料任务启动失败: {start_rtn.get('message')}")
            self._log_step(f"配料任务启动成功: {start_rtn.get('data')}", "SUCCESS")

            self._log_step("等待任务完成...", "INFO")
            if not self._wait_for_task_finished(task_id):
                self._log_step(f"任务超时: {task_id}", "ERROR")
                self.running = False
                return self._return_with_error(f"任务超时: {task_id}")

            # self._wait_for_confirm("请确认配料完成，然后点击确认", timeout=300)

            ########## 步骤3: 停止任务 ##########
            self._log_step(f"停止当前任务")
            self.mix_controller.stop_task(task_id)
            # self.mix_controller.cancel_task(mixer_task_model.task_id)
            self._log_step("配料完成，结束流程", "SUCCESS")

            self.running = False
            return {"status": True, "message": "配料流程结束"}
        except Exception as e:
            self._log_step(f"严重错误: 配料流程失败: {e}", "ERROR")
            return self._return_with_error(f"配料流程失败: {e}")
        finally:
            self.running = False

    def get_summary(self) -> dict:
        """获取配料流程总结"""
        mixer_summary = self.mix_controller.get_running_status()
        return {
            "status": True,
            "summary": {
                "mixer": mixer_summary
            }
        }

    def stop(self):
        self._stop_requested = True
        self.running = False

mix_flow_mgr = MixFlowManager(get_mixer_controller())