import time
import threading
from typing import Dict, Any, List, Optional
from datetime import datetime

from devices.cent_core import cent_controller, CentController
from logger import sys_logger as logger

class CentrifugeFlowManager:
    """离心机工序工作流管理器"""
    def __init__(self, cent_controller: CentController, logger=logger):
        self.cent_controller = cent_controller
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

    def stop(self):
        self.running = False

    def _log_step(self, message: str, level: str = "INFO"):
        """记录步骤日志"""
        self.current_step_info = message
        self.logger.log(f"[离心机流程] {message}", level)

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

    def door_status(status):
        '''解析门窗状态
        
        door_window
            1 open
            0 close
        '''
        is_open = status.get("door_window") == 1 
        return is_open


    def run(self):

        # 1. 连接
        success = self.cent_controller.connect()
        if not success:
            print(self.cent_controller.message)
            return

        # 2. 开盖
        d = self.cent_controller.open_door()
        print(f"开盖结果：{d}")

        time.sleep(1)

        # 3. 检查盖状态
        # TODO
        status = self.cent_controller.get_running_status()

        print(f"开盖后的状态：{status}")

        # 4. 放样
        # TODO

        # 5. 关盖
        d = self.cent_controller.close_door()
        print(f"关盖结果：{d}")

        time.sleep(3)

        # 6. 检查盖状态
        # TODO
        status = self.cent_controller.get_running_status()
        print(f"关盖后的状态：{status}")

        # 等待离心机盖关闭才能往后执行
        while(not self.cent_controller.door_is_closed):
            # 如果一直开着
            time.sleep(0.1)


        # 7.1 设置速度
        self.cent_controller.set_speed(500)
        self.cent_controller.set_time(120)

        time.sleep(5)

        status = self.cent_controller.get_running_status()
        print(f"启动前状态：{status}")

        # 7. 启动
        d = self.cent_controller.start()
        print(f"启动结果：{d}")

        time.sleep(5)

        for _ in range(5):
            status = self.cent_controller.get_running_status()
            print(f"运行中状态：{status}")
            time.sleep(2)
        
        # 8.
        time.sleep(120)

        d =self.cent_controller.stop()
        print(f"停止结果：{d}")

        status = self.cent_controller.get_running_status()
        print(f"停止后状态：{status}")

        time.sleep(5)
        status = self.cent_controller.get_running_status()
        print(f"停止后5s状态：{status}")

        if status["status"] == "success":
            status["data"]["run_state"]

        # # 9. 开盖
        self.cent_controller.open_door()

        # # 10. 检查盖状态
        status = self.cent_controller.get_running_status()
        print(f"最后的状态：{status}")

        # 11. 下样
        # TODO