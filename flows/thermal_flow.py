import struct
from typing import Optional
import time
import json
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, List
from snap7.type import Area

from logger import sys_logger as logger
from devices.robot_core import RobotController
from devices.door_core import DoorController
from devices.centrifuge_core import CentrifugeController
from devices.oven_core import OvenController, OvenLidActionCode, OvenActionCode

class ThermalFlowManager:
    """高温炉、离心机热处理工序工作流管理器"""
    def __init__(self, robot_controller: RobotController,
            door_controller: DoorController, 
            centrifuge_controller: CentrifugeController, 
            oven_controller: OvenController, 
            logger=logger):
        self.robot_controller = robot_controller
        self.door_controller = door_controller
        self.centrifuge_controller = centrifuge_controller
        self.oven_controller = oven_controller
        self.logger = logger
        self.task_queue = []
        self.running = False
        self.current_step_info = "就绪"

        # === 新增：确认信号事件 ===
        self.confirm_event = threading.Event()
        self.confirm_event.set()  # 默认设置为True，以免不需确认的任务卡住

        # 炉子ID -> 玻璃门ID 的映射表
        self.OVEN_TO_DOOR = {}
        for i in [1, 2, 7, 8]: self.OVEN_TO_DOOR[i] = 2
        for i in [3, 4, 5, 6]: self.OVEN_TO_DOOR[i] = 1
        for i in [9, 10, 15, 16]: self.OVEN_TO_DOOR[i] = 4
        for i in [11, 12, 13, 14]: self.OVEN_TO_DOOR[i] = 3
        for i in [17, 18, 23, 24]: self.OVEN_TO_DOOR[i] = 6
        for i in [19, 20, 21, 22]: self.OVEN_TO_DOOR[i] = 5

        self.thread = threading.Thread(target=self._worker, daemon=True)
        self.thread.start()

    def get_door_by_oven(self, oven_id):
        return self.OVEN_TO_DOOR.get(oven_id, 0)

    def user_confirm(self):
        """前端调用的确认方法"""
        self.logger.log(">>> 人工已确认门盖状态，流程继续 <<<", "SUCCESS")
        self.confirm_event.set()

    def _log_step(self, message: str, level: str = "INFO"):
        """记录步骤日志"""
        self.current_step_info = message
        self.logger.log(f"[热处理流程] {message}", level)

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

    def load(self, shelf_id, oven_id, qty):
        """上料流程（货架 -> 炉子）
        执行后系统将自动打开对应炉盖与门，并暂停等待人工确认。

        :param shelf_id: 货架ID
        :param oven_id: 炉子ID
        :param qty: 数量
        """
        self.task_queue = []
        # === 步骤 1: 货架取 ===
        self.task_queue.append({
            'tid': 1, 'st': shelf_id, 'qty': qty,
            'auto_device': None, 'dev_id': 0, 'door_id': 0,
            'desc': '1.货架取',
            'check_home': False,  # <--- 新增这行：设为False表示不等待回原点
            'need_confirm': False  # <--- 新增标记
        })

        door_id = self.get_door_by_oven(oven_id)
        # 任务5: 炉子放 (需要自动收尾)
        self.task_queue.append({
            'tid': 5, 'st': oven_id, 'qty': qty,
            'auto_device': 'oven_complex', 'dev_id': oven_id, 'door_id': door_id,
            'desc': f'2.炉子放(炉{oven_id}/门{door_id})',
            'check_home': True,
            'need_confirm': True
        })
        self.running = True
        self.logger.log(f"流程A启动: 货架{shelf_id} -> 炉子{oven_id}", "INFO")

    def fire(self):
        """启动高温炉"""
        self._log_step("热处理完成，结束流程", "SUCCESS")

    def unload(self, oven_id, slot_id, shelf_id):
        """出料流程（炉子 -> 离心机 -> 货架）。
        流程包含三次暂停，需配合确认接口使用。
        
        :param oven_id: 炉子ID
        :param slot_id: 槽位号
        :param shelf_id: 货架号
        """
        self.task_queue = []
        door_id = self.get_door_by_oven(oven_id)
        # === 步骤 1: 炉子取 ===
        self.task_queue.append({
            'tid': 6, 'st': oven_id, 'qty': slot_id,
            'auto_device': 'oven_complex', 'dev_id': oven_id, 'door_id': door_id,
            'desc': f'1.炉子取(炉{oven_id}/门{door_id})',
            'check_home': False,
            'need_confirm': True  # <---【第1次确认点】
        })
        # === 步骤 2: 离心机放  ===
        self.task_queue.append({
            'tid': 3, 'st': 3, 'qty': 3,
            'auto_device': 'cent',  # 触发自动开离心机门
            'dev_id': 0,
            'door_id': 0,
            'desc': '2.离心机放',
            'check_home': False,
            'need_confirm': True  # <---【第2次确认点】
        })
        # === 步骤 3: 离心机取 ===
        self.task_queue.append({
            'tid': 4, 'st': 4, 'qty': 4,
            'auto_device': 'cent',  # 再次触发开门(防止中途关过)
            'dev_id': 0,
            'door_id': 0,
            'desc': '3.离心机取',
            'check_home': False,
            'need_confirm': True  # <---【第3次确认点】

        })
        # === 步骤 4: 货架放 (无确认，直接放) ===
        self.task_queue.append({
            'tid': 2, 'st': shelf_id, 'qty': shelf_id,
            'auto_device': None,
            'dev_id': 0,
            'door_id': 0,
            'desc': '4.货架放',
            'check_home': True,
            'need_confirm': False
        })
        self.running = True
        self.logger.log(f"流程B启动: 炉子{oven_id} -> 货架{shelf_id}", "INFO")

    def run(self):
        #########################################################
        # 1. 上料 #
        #########################################################
        # TODO 怎么获取货架、炉子、数量？
        shelf_id = 1; oven_id = 1; qty = 1; 
        self.load(shelf_id, oven_id, qty)
        self.user_confirm()
        #########################################################
        # 2. 下料 #
        #########################################################
        # TODO 怎么获取炉子、槽位、货架号？
        oven_id = 1; slot_id = 1; shelf_id = 1; 
        self.unload(oven_id, slot_id, shelf_id)
        self.user_confirm()
        self._log_step("热处理完成，结束流程", "SUCCESS")

    def _worker(self):
        """后台线程"""

        while True:
            time.sleep(1)

            if not self.running or not self.task_queue:
                self.current_step_info = "流程结束或未启动"
                if self.running:
                    self.logger.log("所有任务流程已结束", "SUCCESS")
                    self.running = False
                continue

            # 初始检查，避免忙碌时下发
            if not self.robot_controller.connect():
                continue

            # 假设 DB1.242=1 表示空闲
            # sys_status = self.robot_controller.read_db_int(1, 242, 4)
            sys_status = self.robot_controller.get_system_status()
            if sys_status != 1:
                continue

            task = self.task_queue.pop(0)
            self.current_step_info = f"正在执行: {task['desc']}"
            self.logger.log(f"任务开始: {task['desc']}", "INFO")

            # ====================================================
            # 1. 直接下发任务并启动机器人 (模拟Utils逻辑)
            # ====================================================
            # 2. 设置任务数据
            if not self.robot_controller.write_task(task['tid'], task['st'], task['qty']):
                self.logger.log(f"严重错误: 任务数据写入失败，终止当前任务", "ERROR")
                # 任务失败，不应继续
                continue

            time.sleep(0.5)

            # 3. 启动点动 (发送启动信号)
            if not self.robot_controller.dispatch_task():
                self.logger.log(f"严重错误: 机器人启动信号发送失败，流程终止", "ERROR")
                continue

            print(f"PLC任务 {task['desc']} 已启动，等待完成及回原点...")

            # ===============================================
            # 新增步骤：必须先确认为"运行中"，防止假完成
            # ===============================================
            wait_run_start = time.time()
            is_started = False
            self.logger.log("正在等待机器人响应启动指令...", "INFO")

            while time.time() - wait_run_start < 10:  # 最多等10秒让它动起来
                if not self.robot_controller.connect():
                    time.sleep(1)
                    continue

                # 读取状态: 2=执行中
                s = self.robot_controller.get_system_status()
                if s == 2:
                    is_started = True
                    self.logger.log("机器人已开始运行 (状态变更为2)", "INFO")
                    break
                time.sleep(0.5)

            # 【核心修改】如果10秒内机器人没动，认为任务失败，中止！
            if not is_started:
                self.logger.log("严重错误: 机器人未响应启动指令(超时10s)，任务中止", "ERROR")
                continue  # 跳过后续等待，直接结束当前任务（不进入假完成状态）

            # ====================================================
            # 2. 中途介入: 如果需要自动设备操作 (开门 + 确认 + 信号发送)
            # ====================================================
            if task.get('auto_device'):
                # 2.1 自动开启硬件
                try:
                    if task['auto_device'] == 'oven_complex':
                        self.logger.log(f"自动动作: 打开炉盖{task['dev_id']}及玻璃门{task['door_id']}", "INFO")
                        self.oven_controller.control_lid(task['dev_id'], OvenLidActionCode.open)
                        if task['door_id'] > 0:
                            self.door_controller.send_command(task['door_id'], 'open')

                    elif task['auto_device'] == 'cent':
                        self.logger.log("自动动作: 打开离心机门", "INFO")
                        self.centrifuge_controller.open_door()
                except Exception as e:
                    self.logger.log(f"设备自动控制失败: {e}", "ERROR")

                # 2.2 等待人工确认
                if task.get('need_confirm', False):
                    if not self._wait_for_confirm(f"检查炉{task['dev_id']}门盖状态", timeout=300):
                        continue

                    if not self.running: continue  # 停止后的清理

                # 2.3 发送PLC确认信号 (M10.x) - 模拟Utils的交互
                # 任务5,6 (Oven) 需要 M10.2 (Glass) 和 M10.3 (Oven)
                # 任务3,4 (Cent) 需要 M10.4 (Cent)
                try:
                    if self.robot_controller.connect():
                        v = self.robot_controller.read_m_bytes(10)

                        if task['auto_device'] == 'oven_complex':
                            # 置位 M10.2 (Bit 2) 和 M10.3 (Bit 3)
                            v[0] |= (1 << 2)
                            v[0] |= (1 << 3)
                            self.logger.log("已发送: 炉门/盖开启确认信号 (M10.2/M10.3)", "INFO")

                        elif task['auto_device'] == 'cent':
                            # 置位 M10.4 (Bit 4)
                            v[0] |= (1 << 4)
                            self.logger.log("已发送: 离心机门开启确认信号 (M10.4)", "INFO")

                        self.robot_controller.write_m_bytes(10, v)
                except Exception as e:
                    self.logger.log(f"发送PLC许可信号失败: {e}", "ERROR")

            # ===============================================
            # 修改后的安全等待逻辑
            # ===============================================
            idle_stable_start = 0
            self.logger.log(f"等待任务完成: {task['desc']} (等待回原点信号...)", "INFO")
            # === 修改点 2：获取当前任务是否强制要求回原点，默认为 True ===
            need_home_check = task.get('check_home', True)
            while True:
                # 1. 优先处理断线
                if not self.robot_controller.connected:
                    self.logger.log("流程暂停: PLC连接断开，正在尝试重连...", "WARN")
                    self.robot_controller.connect()
                    time.sleep(1)
                    idle_stable_start = 0
                    continue

                # 2. 读取关键信号
                # current_sys_status = self.robot_controller.read_db_int(1, 242, 4)
                current_sys_status = self.robot_controller.get_system_status()
                # is_home = self.robot_controller.read_db_bit(1, 218, 0)
                is_home = self.robot_controller.get_home_status()

                # 判断任务是否完成：状态必须为1，且 (如果不强制回原点 OR 确实在原点)
                is_task_done = (current_sys_status == 1) and ((not need_home_check) or is_home)

                if is_task_done:
                    if idle_stable_start == 0:
                        idle_stable_start = time.time()

                    # 4. 信号防抖 3秒
                    if time.time() - idle_stable_start > 3.0:
                        # 提示语区分一下
                        if not need_home_check:
                            self.logger.log(f"任务确认完成 (状态空闲，跳过回原点检查)", "SUCCESS")
                        else:
                            self.logger.log(f"任务确认完成 (状态空闲且已回原点)", "SUCCESS")
                        break
                else:
                    # ... (防抖重置代码保持不变) ...
                    idle_stable_start = 0

                time.sleep(0.5)

            # ===============================================
            # 新增: 任务完成后清理 M10.x 信号 (防止误触发)
            # ===============================================
            if task.get('auto_device'):
                try:
                    if self.robot_controller.connect():
                        d = self.robot_controller.read_m_bytes(10, 1)
                        v = bytearray(d)
                        # 复位 M10.2, M10.3, M10.4
                        v[0] &= ~(1 << 2)
                        v[0] &= ~(1 << 3)
                        v[0] &= ~(1 << 4)
                        self.robot_controller.write_m_bytes(10, v)
                except:
                    pass

            # ===============================================
            # 修改后的自动收尾逻辑
            # ===============================================
            if task['tid'] == 5 and task['auto_device'] == 'oven_complex':
                self.current_step_info = "机器人已回原点，执行自动关闭..."
                self.logger.log(">>> 机器人已安全离开，执行自动关闭程序 <<<", "INFO")

                try:
                    self.logger.log(f"自动关闭: 炉盖{task['dev_id']}", "INFO")
                    self.oven_controller.control_lid(task['dev_id'], OvenLidActionCode.close)

                    if task['door_id'] > 0:
                        self.logger.log(f"自动关闭: 玻璃门{task['door_id']}", "INFO")
                        self.door_controller.send_command(task['door_id'], 'close')
                    self.logger.log("自动收尾完成", "SUCCESS")
                except Exception as e:
                    self.logger.log(f"自动关闭失败: {e}", "ERROR")

from devices.robot_core import robot_controller
from devices.door_core import door_controller
from devices.centrifuge_core import centrifuge_controller
from devices.oven_core import oven_controller
thermal_flow_mgr = ThermalFlowManager(robot_controller, door_controller, centrifuge_controller, oven_controller)