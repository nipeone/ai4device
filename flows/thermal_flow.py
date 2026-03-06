import struct
from typing import Optional
import time
import json
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, List
from snap7.type import Area
from enum import Enum

from logger import sys_logger as logger
from devices.robot_core import RobotController, RobotHomeStatus, RobotSystemStatus
from devices.door_core import DoorController
from devices.centrifuge_core import CentrifugeController
from devices.oven_core import OvenController, OvenLidActionCode, OvenActionCode
from schemas.door import DoorActionCode, DoorStatus
from schemas.oven import OvenStatus, CurvePoint
from schemas.centrifuge import CentrifugeDoorStatus, CentrifugeStatus

class TaskType(Enum):
    '''任务类型
    - SHELF_TAKE 货架取：1
    - SHELF_DROP 货架放：2
    - CENT_DROP  离心机放：3
    - CENT_TAKE  离心机取：4
    - OVEN_DROP  炉子放：5
    - OVEN_TAKE  炉子取：6
    '''
    SHELF_TAKE = 1 # 货架取
    SHELF_DROP = 2 # 货架放
    CENT_DROP = 3 # 离心机放
    CENT_TAKE = 4 # 离心机取
    OVEN_DROP = 5 # 炉子放
    OVEN_TAKE = 6 # 炉子取

class ShelfType(Enum):
    '''货架类型
    - SHELF_1 熔封机旁货架，名为货架1，PLC内部站位号为1
    - SHELF_2 离心机旁货架，名为货架2，PLC内部站位号为3
    '''
    SHELF_1 = 1
    SHELF_2 = 3

TASKS = {
    TaskType.SHELF_TAKE: "货架取",
    TaskType.SHELF_DROP: "货架放",
    TaskType.CENT_DROP: "离心机放",
    TaskType.CENT_TAKE: "离心机取",
    TaskType.OVEN_DROP: "炉子放",
    TaskType.OVEN_TAKE: "炉子取",
}

class ThermalFlowManager:
    """加热炉、离心机热处理工序工作流管理器"""
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

        # self.thread = threading.Thread(target=self._worker, daemon=True)
        # self.thread.start()

    def get_door_by_oven(self, oven_id: int) -> int:
        ''' 根据炉子ID获取玻璃门ID
            oven_id: 炉子ID
            return: 玻璃门ID
        '''
        if oven_id not in self.OVEN_TO_DOOR:
            self._log_step(f"炉子ID {oven_id} 没有对应的玻璃门ID", "ERROR")
            return 0
        return self.OVEN_TO_DOOR.get(oven_id, 0)

    def user_confirm(self):
        """前端调用的确认方法"""
        self.logger.log(">>> 人工已确认门盖状态，流程继续 <<<", "SUCCESS")
        self.confirm_event.set()

    def stop(self):
        self.running = False

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

    # def load(self, shelf_id, oven_id, qty):
    #     """上料流程（货架 -> 炉子）
    #     执行后系统将自动打开对应炉盖与门，并暂停等待人工确认。

    #     :param shelf_id: 货架ID
    #     :param oven_id: 炉子ID
    #     :param qty: 数量
    #     """
    #     self.task_queue = []
    #     # === 步骤 1: 货架取 ===
    #     self.task_queue.append({
    #         'tid': 1, 'st': shelf_id, 'qty': qty,
    #         'auto_device': None, 'dev_id': 0, 'door_id': 0,
    #         'desc': '1.货架取',
    #         'check_home': False,  # <--- 新增这行：设为False表示不等待回原点
    #         'need_confirm': False  # <--- 新增标记
    #     })

    #     door_id = self.get_door_by_oven(oven_id)
    #     # 任务5: 炉子放 (需要自动收尾)
    #     self.task_queue.append({
    #         'tid': 5, 'st': oven_id, 'qty': qty,
    #         'auto_device': 'oven_complex', 'dev_id': oven_id, 'door_id': door_id,
    #         'desc': f'2.炉子放(炉{oven_id}/门{door_id})',
    #         'check_home': True,
    #         'need_confirm': True
    #     })
    #     self.running = True
    #     self.logger.log(f"流程A启动: 货架{shelf_id} -> 炉子{oven_id}", "INFO")

    # def fire(self):
    #     """启动加热炉"""
    #     self._log_step("热处理完成，结束流程", "SUCCESS")

    # def unload(self, oven_id, slot_id, shelf_id):
    #     """出料流程（炉子 -> 离心机 -> 货架）。
    #     流程包含三次暂停，需配合确认接口使用。
        
    #     :param oven_id: 炉子ID
    #     :param slot_id: 槽位号
    #     :param shelf_id: 货架号
    #     """
    #     self.task_queue = []
    #     door_id = self.get_door_by_oven(oven_id)
    #     # === 步骤 1: 炉子取 ===
    #     self.task_queue.append({
    #         'tid': 6, 'st': oven_id, 'qty': slot_id,
    #         'auto_device': 'oven_complex', 'dev_id': oven_id, 'door_id': door_id,
    #         'desc': f'1.炉子取(炉{oven_id}/门{door_id})',
    #         'check_home': False,
    #         'need_confirm': True  # <---【第1次确认点】
    #     })
    #     # === 步骤 2: 离心机放  ===
    #     self.task_queue.append({
    #         'tid': 3, 'st': 3, 'qty': 3,
    #         'auto_device': 'cent',  # 触发自动开离心机门
    #         'dev_id': 0,
    #         'door_id': 0,
    #         'desc': '2.离心机放',
    #         'check_home': False,
    #         'need_confirm': True  # <---【第2次确认点】
    #     })
    #     # === 步骤 3: 离心机取 ===
    #     self.task_queue.append({
    #         'tid': 4, 'st': 4, 'qty': 4,
    #         'auto_device': 'cent',  # 再次触发开门(防止中途关过)
    #         'dev_id': 0,
    #         'door_id': 0,
    #         'desc': '3.离心机取',
    #         'check_home': False,
    #         'need_confirm': True  # <---【第3次确认点】

    #     })
    #     # === 步骤 4: 货架放 (无确认，直接放) ===
    #     self.task_queue.append({
    #         'tid': 2, 'st': shelf_id, 'qty': shelf_id,
    #         'auto_device': None,
    #         'dev_id': 0,
    #         'door_id': 0,
    #         'desc': '4.货架放',
    #         'check_home': True,
    #         'need_confirm': False
    #     })
    #     self.running = True
    #     self.logger.log(f"流程B启动: 炉子{oven_id} -> 货架{shelf_id}", "INFO")

    # def _worker(self):
    #     """后台线程"""

    #     while True:
    #         time.sleep(1)

    #         if not self.running or not self.task_queue:
    #             self.current_step_info = "流程结束或未启动"
    #             if self.running:
    #                 self.logger.log("所有任务流程已结束", "SUCCESS")
    #                 self.running = False
    #             continue

    #         # 初始检查，避免忙碌时下发
    #         if not self.robot_controller.connect():
    #             continue

    #         # 假设 DB1.242=1 表示空闲
    #         # sys_status = self.robot_controller.read_db_int(1, 242, 4)
    #         sys_status = self.robot_controller.get_system_status()
    #         if sys_status != RobotSystemStatus.IDLE:
    #             continue

    #         task = self.task_queue.pop(0)
    #         self.current_step_info = f"正在执行: {task['desc']}"
    #         self.logger.log(f"任务开始: {task['desc']}", "INFO")

    #         # ====================================================
    #         # 1. 直接下发任务并启动机器人 (模拟Utils逻辑)
    #         # ====================================================
    #         # 2. 设置任务数据
    #         if not self.robot_controller.write_task(task['tid'], task['st'], task['qty']):
    #             self.logger.log(f"严重错误: 任务数据写入失败，终止当前任务", "ERROR")
    #             # 任务失败，不应继续
    #             continue

    #         time.sleep(0.5)

    #         # 3. 启动点动 (发送启动信号)
    #         if not self.robot_controller.dispatch_task():
    #             self.logger.log(f"严重错误: 机器人启动信号发送失败，流程终止", "ERROR")
    #             continue

    #         print(f"PLC任务 {task['desc']} 已启动，等待完成及回原点...")

    #         # ===============================================
    #         # 新增步骤：必须先确认为"运行中"，防止假完成
    #         # ===============================================
    #         wait_run_start = time.time()
    #         is_started = False
    #         self.logger.log("正在等待机器人响应启动指令...", "INFO")

    #         while time.time() - wait_run_start < 10:  # 最多等10秒让它动起来
    #             if not self.robot_controller.connect():
    #                 time.sleep(1)
    #                 continue

    #             # 读取状态: 2=执行中
    #             s = self.robot_controller.get_system_status()
    #             if s == RobotSystemStatus.RUNNING:
    #                 is_started = True
    #                 self.logger.log("机器人已开始运行 (状态变更为2)", "INFO")
    #                 break
    #             time.sleep(0.5)

    #         # 【核心修改】如果10秒内机器人没动，认为任务失败，中止！
    #         if not is_started:
    #             self.logger.log("严重错误: 机器人未响应启动指令(超时10s)，任务中止", "ERROR")
    #             continue  # 跳过后续等待，直接结束当前任务（不进入假完成状态）

    #         # ====================================================
    #         # 2. 中途介入: 如果需要自动设备操作 (开门 + 确认 + 信号发送)
    #         # ====================================================
    #         if task.get('auto_device'):
    #             # 2.1 自动开启硬件
    #             try:
    #                 if task['auto_device'] == 'oven_complex':
    #                     self.logger.log(f"自动动作: 打开炉盖{task['dev_id']}及玻璃门{task['door_id']}", "INFO")
    #                     self.oven_controller.control_lid(task['dev_id'], OvenLidActionCode.open)
    #                     if task['door_id'] > 0:
    #                         self.door_controller.open_door(task['door_id'])

    #                 elif task['auto_device'] == 'cent':
    #                     self.logger.log("自动动作: 打开离心机门", "INFO")
    #                     self.centrifuge_controller.open_door()
    #             except Exception as e:
    #                 self.logger.log(f"设备自动控制失败: {e}", "ERROR")

    #             # 2.2 等待人工确认
    #             if task.get('need_confirm', False):
    #                 if not self._wait_for_confirm(f"检查炉{task['dev_id']}门盖状态", timeout=300):
    #                     continue

    #                 if not self.running: continue  # 停止后的清理

    #             # 2.3 发送PLC确认信号 (M10.x) - 模拟Utils的交互
    #             # 任务5,6 (Oven) 需要 M10.2 (Glass) 和 M10.3 (Oven)
    #             # 任务3,4 (Cent) 需要 M10.4 (Cent)
    #             try:
    #                 if self.robot_controller.connect():
    #                     v = self.robot_controller.read_m_bytes(10)

    #                     if task['auto_device'] == 'oven_complex':
    #                         # 置位 M10.2 (Bit 2) 和 M10.3 (Bit 3)
    #                         v[0] |= (1 << 2)
    #                         v[0] |= (1 << 3)
    #                         self.logger.log("已发送: 炉门/盖开启确认信号 (M10.2/M10.3)", "INFO")

    #                     elif task['auto_device'] == 'cent':
    #                         # 置位 M10.4 (Bit 4)
    #                         v[0] |= (1 << 4)
    #                         self.logger.log("已发送: 离心机门开启确认信号 (M10.4)", "INFO")

    #                     self.robot_controller.write_m_bytes(10, v)
    #             except Exception as e:
    #                 self.logger.log(f"发送PLC许可信号失败: {e}", "ERROR")

    #         # ===============================================
    #         # 修改后的安全等待逻辑
    #         # ===============================================
    #         idle_stable_start = 0
    #         self.logger.log(f"等待任务完成: {task['desc']} (等待回原点信号...)", "INFO")
    #         # === 修改点 2：获取当前任务是否强制要求回原点，默认为 True ===
    #         need_home_check = task.get('check_home', True)
    #         while True:
    #             # 1. 优先处理断线
    #             if not self.robot_controller.connected:
    #                 self.logger.log("流程暂停: PLC连接断开，正在尝试重连...", "WARN")
    #                 self.robot_controller.connect()
    #                 time.sleep(1)
    #                 idle_stable_start = 0
    #                 continue

    #             # 2. 读取关键信号
    #             # current_sys_status = self.robot_controller.read_db_int(1, 242, 4)
    #             current_sys_status = self.robot_controller.get_system_status()
    #             # is_home = self.robot_controller.read_db_bit(1, 218, 0)
    #             is_home = self.robot_controller.get_home_status()

    #             # 判断任务是否完成：状态必须为1，且 (如果不强制回原点 OR 确实在原点)
    #             is_task_done = (current_sys_status == RobotSystemStatus.IDLE) and ((not need_home_check) or is_home)

    #             if is_task_done:
    #                 if idle_stable_start == 0:
    #                     idle_stable_start = time.time()

    #                 # 4. 信号防抖 3秒
    #                 if time.time() - idle_stable_start > 3.0:
    #                     # 提示语区分一下
    #                     if not need_home_check:
    #                         self.logger.log(f"任务确认完成 (状态空闲，跳过回原点检查)", "SUCCESS")
    #                     else:
    #                         self.logger.log(f"任务确认完成 (状态空闲且已回原点)", "SUCCESS")
    #                     break
    #             else:
    #                 # ... (防抖重置代码保持不变) ...
    #                 idle_stable_start = 0

    #             time.sleep(0.5)

    #         # ===============================================
    #         # 新增: 任务完成后清理 M10.x 信号 (防止误触发)
    #         # ===============================================
    #         if task.get('auto_device'):
    #             try:
    #                 if self.robot_controller.connect():
    #                     d = self.robot_controller.read_m_bytes(10, 1)
    #                     v = bytearray(d)
    #                     # 复位 M10.2, M10.3, M10.4
    #                     v[0] &= ~(1 << 2)
    #                     v[0] &= ~(1 << 3)
    #                     v[0] &= ~(1 << 4)
    #                     self.robot_controller.write_m_bytes(10, v)
    #             except:
    #                 pass

    #         # ===============================================
    #         # 修改后的自动收尾逻辑
    #         # ===============================================
    #         if task['tid'] == 5 and task['auto_device'] == 'oven_complex':
    #             self.current_step_info = "机器人已回原点，执行自动关闭..."
    #             self.logger.log(">>> 机器人已安全离开，执行自动关闭程序 <<<", "INFO")

    #             try:
    #                 self.logger.log(f"自动关闭: 炉盖{task['dev_id']}", "INFO")
    #                 self.oven_controller.control_lid(task['dev_id'], OvenLidActionCode.close)

    #                 if task['door_id'] > 0:
    #                     self.logger.log(f"自动关闭: 玻璃门{task['door_id']}", "INFO")
    #                     self.door_controller.close_door(task['door_id'])
    #                 self.logger.log("自动收尾完成", "SUCCESS")
    #             except Exception as e:
    #                 self.logger.log(f"自动关闭失败: {e}", "ERROR")

    def _set_linked_devices_status_to_robot(self, is_oven: bool = True) -> bool:
        """设置机器人加热炉、玻璃门等关联设备状态"""
        try:
            v = self.robot_controller.read_m_bytes(10)
            if is_oven:
                v[0] |= (1 << 2)
                v[0] |= (1 << 3)
            else:
                v[0] |= (1 << 4)
            self.robot_controller.write_m_bytes(10, v)
            return True
        except Exception as e:
            self._log_step(f"发送PLC许可信号失败: {e}", "ERROR")
            return False

    def _unset_linked_devices_status_to_robot(self, is_oven: bool = True) -> bool:
        """取消设置机器人加热炉、玻璃门等关联设备状态"""
        try:
            v = self.robot_controller.read_m_bytes(10)
            if is_oven:
                v[0] &= ~(1 << 2)
                v[0] &= ~(1 << 3)
            else:
                v[0] &= ~(1 << 4)
            self.robot_controller.write_m_bytes(10, v)
            return True
        except Exception as e:
            self._log_step(f"复位PLC许可信号失败: {e}", "ERROR")
            return False

    def _wait_for_robot_started(self) -> bool:
        """等待机器人响应启动指令，最多等10秒让它动起来，必须先确认为"运行中"，防止假完成"""
        start_time = time.time()
        is_started = False
        self._log_step("正在等待机器人响应启动指令...", "INFO")
        while self.running and time.time() - start_time < 10:  # 最多等10秒让它动起来
            s = self.robot_controller.get_system_status()
            if s == RobotSystemStatus.RUNNING:
                is_started = True
                self._log_step("机器人已开始运行 (状态变更为2)", "INFO")
                break
            time.sleep(2)
        return is_started

    def _wait_for_oven_lid_operation_completed(self, oven_id: int) -> bool:
        """等待加热炉盖打开及关闭，最多等3秒"""
        self._log_step("正在等待加热炉盖打开及关闭...", "INFO")
        start_time = time.time()
        while self.running and time.time() - start_time < 3.0:  # 最多等3秒
            # TODO 获取加热炉状态，目前没有API支持
            time.sleep(1)
        return True

    def _wait_for_oven_operation_completed(self, oven_id: int, target_status: OvenStatus) -> bool:
        """等待加热炉启动及停止，最多等3秒"""
        self._log_step("正在等待加热炉启动及停止...", "INFO")
        start_time = time.time()
        is_completed = False
        while self.running and time.time() - start_time < 3.0:  # 最多等3秒
            status = self.oven_controller.get_oven_status(oven_id)
            if status == target_status:
                is_completed = True
                break
            time.sleep(2)
        return is_completed

    def _wait_for_oven_burn_completed(self, oven_id: int, points: List[CurvePoint]) -> bool:
        """等待加热炉燃烧完成，曲线中的时间为小时
        
        :param oven_id: 炉子ID
        :param points: 温度曲线
        :return: 是否完成
        """
        self._log_step("正在等待加热炉完成...", "INFO")

        # 计算燃烧时间
        burn_time = sum([p.time*60*60 for p in points[:-1] if p.time > 0]) + 60*10 # 燃烧时间 + 10分钟冗余时间
        start_time = time.time()
        while time.time() - start_time < burn_time:
            if not self.running:
                self._log_step("流程未知原因停止", "ERROR")
                return False
            status = self.oven_controller.get_oven_status(oven_id)
            if status == OvenStatus.STOPPED:
                self._log_step("加热炉未知原因停止，任务中止", "ERROR")
                return False
            time.sleep(20)
        self._log_step("加热炉燃烧完成", "SUCCESS")
        return True

    def _wait_for_door_operation_completed(self, door_id: int, status: DoorStatus) -> bool:
        """等待玻璃门打开及关闭，最多等3秒"""
        self._log_step("正在等待玻璃门打开及关闭...", "INFO")
        start_time = time.time()
        is_completed = False
        while self.running and time.time() - start_time < 3.0:  # 最多等3秒
            # TODO 获取玻璃门状态，目前没有API支持，先睡眠0.5秒
            status = self.door_controller.get_door_status(door_id)
            if status.get("status") == "success" and status.get("data") == status.value:
                is_completed = True
                break
            time.sleep(2)
        return is_completed

    def _wait_for_robot_task_completed(self, task_type: TaskType, need_home_check: bool = False) -> bool:
        """安全等待机器人任务完成，最多等5秒"""
        idle_stable_start = 0
        self._log_step(f"等待任务完成: {TASKS[task_type]} (等待回原点信号...)", "INFO")
        is_completed = False
        start_time = time.time()
        while self.running and time.time() - start_time < 5.0:  # 最多等5秒
            # 1. 优先处理断线
            if not self.robot_controller.connected:
                self._log_step("流程暂停: PLC连接断开，正在尝试重连...", "WARN")
                self.robot_controller.connect()
                time.sleep(1)
                idle_stable_start = 0
                continue

            # 2. 读取机器人状态和原点状态
            current_sys_status = self.robot_controller.get_system_status()
            home_status = self.robot_controller.get_home_status()

            # 判断任务是否完成：机器人空闲，且 (如果不强制回原点 OR 确实在原点)
            is_task_done = (current_sys_status == RobotSystemStatus.IDLE) and ((not need_home_check) or home_status == RobotHomeStatus.IN_HOME)
            if is_task_done:
                if idle_stable_start == 0:
                    idle_stable_start = time.time()

                # 4. 信号防抖 3秒
                if time.time() - idle_stable_start > 3.0:
                    if not need_home_check:
                        message = "状态空闲，跳过回原点检查"
                    else:
                        message = "状态空闲，且已回原点"
                    self._log_step(f"任务确认完成 ({message})", "SUCCESS")
                    is_completed = True
                    break
            else:
                # ... (防抖重置代码保持不变) ...
                idle_stable_start = 0

            time.sleep(2)
        return is_completed

    def _wait_for_centrifuge_completed(self, time: int):
        """等待离心机完成，最多等time分钟"""
        self._log_step(f"正在等待离心机完成...", "INFO")
        start_time = time.time()
        while time.time() - start_time < time * 60:
            if not self.running:
                self._log_step("流程未知原因停止", "ERROR")
                return False
            time.sleep(2)
        return True

    def _wait_for_centrifuge_stopped(self) -> bool:
        """等待离心机停止，最多等10秒"""
        self._log_step("正在等待离心机停止...", "INFO")
        start_time = time.time()
        is_completed = False
        while self.running and time.time() - start_time < 10.0:  # 最多等10秒
            if self.centrifuge_controller.get_centrifuge_status() == CentrifugeStatus.STOPPED:
                is_completed = True
                break
            time.sleep(0.5)
        return is_completed

    def _wait_for_centrifuge_door_operation_completed(self, status: CentrifugeDoorStatus) -> bool:
        """等待离心机门打开及关闭，最多等5秒"""
        self._log_step("正在等待离心机门打开及关闭...", "INFO")
        start_time = time.time()
        is_completed = False
        while self.running and time.time() - start_time < 5.0:  # 最多等5秒
            # 等待离心机门状态为指定状态才能往后执行
            if self.centrifuge_controller.get_door_status() == status:
                is_completed = True
                break
            time.sleep(0.5)
        return is_completed

    def _task_shelf_take(self, shelf_id: int, qty: int) -> Dict[str, Any]:
        """货架取任务，从货架1 -> 机器人自身临时货架
        - 机器人将货架1的样品放到自身临时货架，（数量最多为6）
        - PLC写入任务时，sta表示货架ID，qty表示数量

        :param shelf_id: 货架ID
        :param qty: 数量
        :return: 任务状态
        """

        # step1. 获取机器人状态，如果机器人空闲则可以上料
        sys_status = self.robot_controller.get_system_status()
        if sys_status != RobotSystemStatus.IDLE:
            self._log_step("机器人繁忙，无法上料", "ERROR")
            return {"status": False, "message": "机器人繁忙，无法上料"}

        # step2. 直接下发任务并启动机器人
        if not self.robot_controller.write_task(TaskType.SHELF_TAKE.value, shelf_id, qty):
            self._log_step("机器人任务数据写入失败，终止上料流程", "ERROR")
            return {"status": False, "message": "任务数据写入失败，终止上料流程"}
        
        time.sleep(0.5)

        # step3. 启动机器人
        if not self.robot_controller.dispatch_task():
            self._log_step("机器人任务下发失败，终止上料流程", "ERROR")
            return {"status": False, "message": "机器人任务下发失败，终止上料流程"}

        self._log_step(f"PLC任务 {TASKS[TaskType.SHELF_TAKE]} 已启动，等待完成...", "INFO")

        # step4. 等待机器人响应启动指令，最多等10秒让它动起来，必须先确认为"运行中"，防止假完成
        self._log_step(f"正在等待机器人响应启动指令...", "INFO")
        if not self._wait_for_robot_started():
            self._log_step("严重错误: 机器人未响应启动指令(超时10s)，任务中止", "ERROR")
            return {"status": False, "message": "机器人未响应启动指令(超时10s)，任务中止"}

        # step5. 等待任务完成
        if not self._wait_for_robot_task_completed(TaskType.SHELF_TAKE, need_home_check=False):
            self._log_step(f"严重错误: {TASKS[TaskType.SHELF_TAKE]}任务未完成，任务中止", "ERROR")
            return {"status": False, "message": f"{TASKS[TaskType.SHELF_TAKE]}任务未完成，任务中止"}

        return {"status": True, "message": f"{TASKS[TaskType.SHELF_TAKE]}任务完成"}

    def _task_oven_drop(self, oven_id: int, qty: int) -> Dict[str, Any]:
        """炉子放任务，6个临时小货架 -> 加热炉，
        - 机器人将自身临时货架的样品放到炉子中
        - PLC写入任务时，sta表示炉子ID，qty表示数量

        :param oven_id: 炉子ID
        :param qty: 数量
        :return: 任务状态
        """

        # step1. 获取机器人状态，如果机器人空闲则可以上料
        sys_status = self.robot_controller.get_system_status()
        if sys_status != RobotSystemStatus.IDLE:
            self._log_step("机器人繁忙，无法放入炉子", "ERROR")
            return {"status": False, "message": "机器人繁忙，无法放入炉子"}

        # step2. 直接下发任务并启动机器人
        if not self.robot_controller.write_task(TaskType.OVEN_DROP.value, oven_id, qty):
            self._log_step("机器人任务数据写入失败，终止放入炉子流程", "ERROR")
            return {"status": False, "message": "机器人任务数据写入失败，终止放入炉子流程"}
        
        time.sleep(0.5)
        
        # step3. 启动机器人
        if not self.robot_controller.dispatch_task():
            self._log_step("机器人任务下发失败，终止放入炉子流程", "ERROR")
            return {"status": False, "message": "机器人任务下发失败，终止放入炉子流程"}

        self._log_step(f"PLC任务 {TASKS[TaskType.OVEN_DROP]} 已启动，等待完成...", "INFO")
        
        # step4. 等待机器人响应启动指令，最多等10秒让它动起来，必须先确认为"运行中"，防止假完成
        self._log_step(f"正在等待机器人响应启动指令...", "INFO")
        if not self._wait_for_robot_started():
            self._log_step("严重错误: 机器人未响应启动指令(超时10s)，任务中止", "ERROR")
            return {"status": False, "message": "机器人未响应启动指令(超时10s)，任务中止"}

        # step5. 打开加热炉盖
        result = self.oven_controller.control_lid(oven_id, OvenLidActionCode.OPEN)
        if result.get("status") != "success":
            self._log_step(f"严重错误: 加热炉盖打开失败: {result.get('message')}", "ERROR")
            return {"status": False, "message": f"加热炉盖打开失败: {result.get('message')}"}
        if not self._wait_for_oven_lid_operation_completed(oven_id):
            self._log_step("严重错误: 加热炉盖打开失败，任务中止", "ERROR")
            return {"status": False, "message": "加热炉盖打开失败，任务中止"}
        
        # step6. 打开玻璃门
        result = self.door_controller.open_door(self.get_door_by_oven(oven_id))
        if result.get("status") != "success":
            self._log_step(f"严重错误: 玻璃门打开失败: {result.get('message')}", "ERROR")
            return {"status": False, "message": f"玻璃门打开失败: {result.get('message')}"}
        if not self._wait_for_door_operation_completed(self.get_door_by_oven(oven_id), DoorStatus.OPENED):
            self._log_step("严重错误: 玻璃门未打开，任务中止", "ERROR")
            return {"status": False, "message": "玻璃门未打开，任务中止"}

        # step7. 设置机器人加热炉、玻璃门等关联设备状态
        if not self._set_linked_devices_status_to_robot():
            self._log_step("严重错误: 发送PLC许可信号失败，任务中止", "ERROR")
            return {"status": False, "message": "发送PLC许可信号失败，任务中止"}
        self._log_step("已向PLC发送: 炉盖、玻璃门开启确认信号 (M10.2/M10.3)", "INFO")

        # step8. 等待机器人任务完成
        if not self._wait_for_robot_task_completed(TaskType.OVEN_DROP, need_home_check=True):
            self._log_step(f"严重错误: {TASKS[TaskType.OVEN_DROP]}任务未完成，任务中止", "ERROR")
            return {"status": False, "message": f"{TASKS[TaskType.OVEN_DROP]}任务未完成，任务中止"}

        # step9. 复位机器人加热炉、玻璃门等关联设备状态
        if not self._unset_linked_devices_status_to_robot():
            self._log_step("严重错误: 复位PLC许可信号失败，任务中止", "ERROR")
            return {"status": False, "message": "复位PLC许可信号失败，任务中止"}
        self._log_step("已向PLC发送: 炉盖、玻璃门关闭确认信号 (M10.2/M10.3)", "INFO")

        # step10. 关闭加热炉盖，并等待关闭完成，这里获取状态的代码没有实现，只能等待3秒
        result = self.oven_controller.control_lid(oven_id, OvenLidActionCode.CLOSE)
        if result.get("status") != "success":
            self._log_step(f"严重错误: 加热炉盖关闭失败: {result.get('message')}", "ERROR")
            return {"status": False, "message": f"加热炉盖关闭失败: {result.get('message')}"}
        if not self._wait_for_oven_lid_operation_completed(oven_id):
            self._log_step("严重错误: 加热炉盖关闭失败，任务中止", "ERROR")
            return {"status": False, "message": "加热炉盖关闭失败，任务中止"}

        # step11. 关闭玻璃门，并等待关闭完成，超过3秒未获取到状态则认为关闭失败
        result = self.door_controller.close_door(self.get_door_by_oven(oven_id))
        if result.get("status") != "success":
            self._log_step(f"严重错误: 玻璃门关闭失败: {result.get('message')}", "ERROR")
            return {"status": False, "message": f"玻璃门关闭失败: {result.get('message')}"}
        if not self._wait_for_door_operation_completed(self.get_door_by_oven(oven_id), DoorStatus.CLOSED):
            self._log_step("严重错误: 玻璃门未关闭，任务中止", "ERROR")
            return {"status": False, "message": "玻璃门未关闭，任务中止"}

        return {"status": True, "message": f"{TASKS[TaskType.OVEN_DROP]}任务完成"}

    def _task_oven_burn(self, oven_id: int, curve_points: List[CurvePoint]) -> Dict[str, Any]:
        """燃烧流程
        
        :param oven_id: 炉号
        :curve_points: 温度曲线
        """

        try:
            # step1. 获取加热炉状态，只有空闲状态才能点火
            oven_status = self.oven_controller.get_oven_status(oven_id)
            if oven_status != OvenStatus.STOPPED:
                self._log_step(f"严重错误: 加热炉正在运行，任务中止", "ERROR")
                return {"status": False, "message": "加热炉正在运行，任务中止"}

            # step2 设置加热炉温度曲线
            # step2.1 处理温度曲线，时间单位为小时
            processed_points: list[CurvePoint] = []
            for p in curve_points:
                if p.time == 0: continue
                if p.time < 0:
                    processed_points.append(CurvePoint(temperature=p.temperature, time=-121.0))
                    break
                else:
                    processed_points.append(CurvePoint(temperature=p.temperature, time=p.time))

            if not processed_points:
                self._log_step("严重错误: 没有有效的温度曲线数据，任务中止", "ERROR")
                return {"status": False, "message": "没有有效的温度曲线数据，任务中止"}

            # step2.2 下发加热炉温度曲线
            result = self.oven_controller.set_curve_points(oven_id, processed_points)
            if result.get("status") != "success":
                self._log_step(f"严重错误: 加热炉温度曲线设置失败: {result.get('message')}", "ERROR")
                return {"status": False, "message": f"加热炉温度曲线设置失败: {result.get('message')}"}

            # step3. 启动加热炉，启动后会自动开始燃烧
            result = self.oven_controller.control_oven(oven_id, OvenActionCode.START)
            if result.get("status") != "success":
                self._log_step(f"加热炉启动失败: {result.get('message')}", "WARNING")
                return {"status": False, "message": f"加热炉启动失败: {result.get('message')}"}
            if not self._wait_for_oven_operation_completed(oven_id, OvenStatus.RUNNING):
                self._log_step("严重错误: 加热炉启动后状态异常，任务中止", "ERROR")
                return {"status": False, "message": "加热炉启动后状态异常，任务中止"}

            # step4. 等待加热炉燃烧完成
            # 时间很漫长，需要检测进程是否正常
            if not self._wait_for_oven_burn_completed(oven_id, processed_points):
                self._log_step("严重错误: 加热炉燃烧失败，任务中止", "ERROR")
                return {"status": False, "message": "加热炉燃烧失败，任务中止"}

            self._log_step("加热炉燃烧完成", "SUCCESS")

            # step5. 停止加热炉，停止后会自动停止燃烧
            result = self.oven_controller.control_oven(oven_id, OvenActionCode.STOP)
            if result.get("status") != "success":
                self._log_step(f"加热炉停止失败: {result.get('message')}", "ERROR")
                return {"status": False, "message": f"加热炉停止失败: {result.get('message')}"}
            if not self._wait_for_oven_operation_completed(oven_id, OvenStatus.STOPPED):
                self._log_step("加热炉停止后状态异常，任务中止", "ERROR")
                return {"status": False, "message": "加热炉停止后状态异常，任务中止"}

            self._log_step("加热炉燃烧完成", "SUCCESS")
            return {"status": True, "message": "加热炉燃烧完成"}
        except Exception as e:
            self._log_step(f"严重错误: 加热炉燃烧失败: {e}", "ERROR")
            return {"status": False, "message": f"加热炉燃烧失败: {e}"}

    def _task_oven_take(self, oven_id: int, qty: int) -> Dict[str, Any]:
        """炉子取任务（加热炉 -> 机器人自带保温炉）
        - 机器人将加热炉中的样品取出放入自身保温炉
        - PLC写入任务时，sta表示炉子ID，qty表示托盘穴位

        :param oven_id: 炉子ID
        :param qty: 托盘穴位
        """

        # step1. 获取机器人状态，如果机器人空闲则可以上料
        sys_status = self.robot_controller.get_system_status()
        if sys_status != RobotSystemStatus.IDLE:
            self._log_step("机器人繁忙，无法从炉子取", "ERROR")
            return {"status": False, "message": "机器人繁忙，无法上料"}

        # step2. 直接下发任务并启动机器人
        if not self.robot_controller.write_task(TaskType.OVEN_TAKE.value, oven_id, qty):
            self._log_step("机器人任务数据写入失败，终止从炉子取样流程", "ERROR")
            return {"status": False, "message": "任务数据写入失败，终止从炉子取样流程"}
        
        time.sleep(0.5)

        # step3. 启动机器人
        if not self.robot_controller.dispatch_task():
            self._log_step("机器人任务下发失败，终止从炉子取样流程", "ERROR")
            return {"status": False, "message": "机器人任务下发失败，终止从炉子取样流程"}

        self._log_step(f"PLC任务 {TASKS[TaskType.OVEN_TAKE]} 已启动，等待完成...", "INFO")

        # step4. 等待机器人响应启动指令，最多等10秒让它动起来，必须先确认为"运行中"，防止假完成
        self._log_step(f"正在等待机器人响应启动指令...", "INFO")
        if not self._wait_for_robot_started():
            self._log_step("严重错误: 机器人未响应启动指令(超时10s)，任务中止", "ERROR")
            return {"status": False, "message": "机器人未响应启动指令(超时10s)，任务中止"}

        # step5. 打开加热炉盖
        result = self.oven_controller.control_lid(oven_id, OvenLidActionCode.OPEN)
        if result.get("status") != "success":
            self._log_step(f"严重错误: 加热炉盖打开失败: {result.get('message')}", "ERROR")
            return {"status": False, "message": f"加热炉盖打开失败: {result.get('message')}"}
        if not self._wait_for_oven_lid_operation_completed(oven_id):
            self._log_step("严重错误: 加热炉盖打开失败，任务中止", "ERROR")
            return {"status": False, "message": "加热炉盖打开失败，任务中止"}
        
        # step6. 打开玻璃门
        result = self.door_controller.open_door(self.get_door_by_oven(oven_id))
        if result.get("status") != "success":
            self._log_step(f"严重错误: 玻璃门打开失败: {result.get('message')}", "ERROR")
            return {"status": False, "message": f"玻璃门打开失败: {result.get('message')}"}
        if not self._wait_for_door_operation_completed(self.get_door_by_oven(oven_id), DoorStatus.OPENED):
            self._log_step("严重错误: 玻璃门未打开，任务中止", "ERROR")
            return {"status": False, "message": "玻璃门未打开，任务中止"}

        # step7. 告知机器人加热炉、玻璃门等关联设备状态
        if not self._set_linked_devices_status_to_robot():
            self._log_step("严重错误: 发送PLC许可信号失败，任务中止", "ERROR")
            return {"status": False, "message": "发送PLC许可信号失败，任务中止"}
        self._log_step("已向PLC发送: 炉盖、玻璃门开启确认信号 (M10.2/M10.3)", "INFO")

        # step8. 等待机器人任务完成
        if not self._wait_for_robot_task_completed(TaskType.OVEN_TAKE, need_home_check=False):
            self._log_step(f"严重错误: {TASKS[TaskType.OVEN_DROP]}任务未完成，任务中止", "ERROR")
            return {"status": False, "message": f"{TASKS[TaskType.OVEN_DROP]}任务未完成，任务中止"}

        # step9. 取消设置机器人加热炉、玻璃门等关联设备状态
        if not self._unset_linked_devices_status_to_robot():
            self._log_step("严重错误: 取消设置PLC许可信号失败，任务中止", "ERROR")
            return {"status": False, "message": "取消设置PLC许可信号失败，任务中止"}
        self._log_step("已向PLC发送: 炉盖、玻璃门关闭确认信号 (M10.2/M10.3)", "INFO")

        # step10. 关闭加热炉盖，并等待关闭完成，这里获取状态的代码没有实现，只能等待3秒
        result = self.oven_controller.control_lid(oven_id, OvenLidActionCode.CLOSE)
        if result.get("status") != "success":
            self._log_step(f"严重错误: 加热炉盖关闭失败: {result.get('message')}", "ERROR")
            return {"status": False, "message": f"加热炉盖关闭失败: {result.get('message')}"}
        if not self._wait_for_oven_lid_operation_completed(oven_id):
            self._log_step("严重错误: 加热炉盖关闭失败，任务中止", "ERROR")
            return {"status": False, "message": "加热炉盖关闭失败，任务中止"}

        # step11. 关闭玻璃门，并等待关闭完成，超过3秒未获取到状态则认为关闭失败
        result = self.door_controller.close_door(self.get_door_by_oven(oven_id))
        if result.get("status") != "success":
            self._log_step(f"严重错误: 玻璃门关闭失败: {result.get('message')}", "ERROR")
            return {"status": False, "message": f"玻璃门关闭失败: {result.get('message')}"}
        if not self._wait_for_door_operation_completed(self.get_door_by_oven(oven_id), DoorStatus.CLOSED):
            self._log_step("严重错误: 玻璃门未关闭，任务中止", "ERROR")
            return {"status": False, "message": "玻璃门未关闭，任务中止"}

        return {"status": True, "message": f"{TASKS[TaskType.OVEN_DROP]}任务完成"}

    def _task_cent_drop(self) -> Dict[str, Any]:
        """离心机放任务（保温炉 -> 离心机）
        - 机器人将保温炉的样品放到离心机
        - PLC写入任务时，sta固定为3，qty固定为3
        
        """

        # step1. 获取机器人状态，如果机器人空闲则可以上料
        sys_status = self.robot_controller.get_system_status()
        if sys_status != RobotSystemStatus.IDLE:
            self._log_step("机器人繁忙，无法放入离心机", "ERROR")
            return {"status": False, "message": "机器人繁忙，无法放入离心机"}

        # step2. 直接下发任务并启动机器人
        if not self.robot_controller.write_task(TaskType.CENT_DROP.value, 3, 3):
            self._log_step("机器人任务数据写入失败，终止放入离心机流程", "ERROR")
            return {"status": False, "message": "任务数据写入失败，终止放入离心机流程"}
        
        time.sleep(0.5)

        # step3. 启动机器人
        if not self.robot_controller.dispatch_task():
            self._log_step("机器人任务下发失败，终止放入离心机流程", "ERROR")
            return {"status": False, "message": "机器人任务下发失败，终止放入离心机流程"}

        self._log_step(f"PLC任务 {TASKS[TaskType.CENT_DROP]} 已启动，等待完成...", "INFO")

        # step4. 等待机器人响应启动指令，最多等10秒让它动起来，必须先确认为"运行中"，防止假完成
        self._log_step(f"正在等待机器人响应启动指令...", "INFO")
        if not self._wait_for_robot_started():
            self._log_step("严重错误: 机器人未响应启动指令(超时10s)，任务中止", "ERROR")
            return {"status": False, "message": "机器人未响应启动指令(超时10s)，任务中止"}

        # step5. 打开离心机门
        result = self.centrifuge_controller.open_door()
        if result.get("status") != "success":
            self._log_step(f"严重错误: 离心机门打开失败: {result.get('message')}", "ERROR")
            return {"status": False, "message": f"离心机门打开失败: {result.get('message')}"}
        if not self._wait_for_centrifuge_door_operation_completed(CentrifugeDoorStatus.OPENED):
            self._log_step("严重错误: 离心机门未打开，任务中止", "ERROR")
            return {"status": False, "message": "离心机门未打开，任务中止"}

        # step6. 设置机器人离心机等关联设备状态
        if not self._set_linked_devices_status_to_robot(False):
            self._log_step("严重错误: 发送PLC许可信号失败，任务中止", "ERROR")
            return {"status": False, "message": "发送PLC许可信号失败，任务中止"}
        self._log_step("已向PLC发送: 炉盖、玻璃门开启确认信号 (M10.2/M10.3)", "INFO")

        # step7. 等待机器人任务完成
        if not self._wait_for_robot_task_completed(TaskType.CENT_DROP, need_home_check=False):
            self._log_step(f"严重错误: {TASKS[TaskType.OVEN_DROP]}任务未完成，任务中止", "ERROR")
            return {"status": False, "message": f"{TASKS[TaskType.OVEN_DROP]}任务未完成，任务中止"}

        # step8. 取消设置机器人离心机等关联设备状态
        if not self._unset_linked_devices_status_to_robot(False):
            self._log_step("严重错误: 取消设置PLC许可信号失败，任务中止", "ERROR")
            return {"status": False, "message": "取消设置PLC许可信号失败，任务中止"}
        self._log_step("已向PLC发送: 炉盖、玻璃门关闭确认信号 (M10.2/M10.3)", "INFO")

        # step9. 关闭离心机门，并等待关闭完成，这里获取状态的代码没有实现，只能等待3秒
        result = self.centrifuge_controller.close_door()
        if result.get("status") != "success":
            self._log_step(f"严重错误: 离心机门关闭失败: {result.get('message')}", "ERROR")
            return {"status": False, "message": f"离心机门关闭失败: {result.get('message')}"}
        if not self._wait_for_centrifuge_door_operation_completed(CentrifugeDoorStatus.CLOSED):
            self._log_step("严重错误: 离心机门未关闭，任务中止", "ERROR")
            return {"status": False, "message": "离心机门未关闭，任务中止"}

        return {"status": True, "message": f"{TASKS[TaskType.CENT_DROP]}任务完成"}

    def _task_cent_take(self) -> Dict[str, Any]:
        """离心机取任务（离心机 -> 货架2）
        - 机器人将离心机中的样品取出放入货架2
        - PLC写入任务时，sta固定为4，qty固定为4

        :return: 任务状态
        """
        # step1. 获取机器人状态，如果机器人空闲则可以上料
        sys_status = self.robot_controller.get_system_status()
        if sys_status != RobotSystemStatus.IDLE:
            self._log_step("机器人繁忙，无法从离心机取样", "ERROR")
            return {"status": False, "message": "机器人繁忙，无法从离心机取样"}

        # step2. 直接下发任务并启动机器人
        if not self.robot_controller.write_task(TaskType.CENT_TAKE.value, 4, 4):
            self._log_step("机器人任务数据写入失败，终止从离心机取样流程", "ERROR")
            return {"status": False, "message": "任务数据写入失败，终止从离心机取样流程"}
        
        time.sleep(0.5)

        # step3. 启动机器人
        if not self.robot_controller.dispatch_task():
            self._log_step("机器人任务下发失败，终止从离心机取样流程", "ERROR")
            return {"status": False, "message": "机器人任务下发失败，终止从离心机取样流程"}

        self._log_step(f"PLC任务 {TASKS[TaskType.CENT_TAKE]} 已启动，等待完成...", "INFO")

        # step4. 等待机器人响应启动指令，最多等10秒让它动起来，必须先确认为"运行中"，防止假完成
        self._log_step(f"正在等待机器人响应启动指令...", "INFO")
        if not self._wait_for_robot_started():
            self._log_step("严重错误: 机器人未响应启动指令(超时10s)，任务中止", "ERROR")
            return {"status": False, "message": "机器人未响应启动指令(超时10s)，任务中止"}

        # step5. 打开离心机门
        result = self.centrifuge_controller.open_door()
        if result.get("status") != "success":
            self._log_step(f"严重错误: 离心机门打开失败: {result.get('message')}", "ERROR")
            return {"status": False, "message": f"离心机门打开失败: {result.get('message')}"}
        if not self._wait_for_centrifuge_door_operation_completed(CentrifugeDoorStatus.OPENED):
            self._log_step("严重错误: 离心机门未打开，任务中止", "ERROR")
            return {"status": False, "message": "离心机门未打开，任务中止"}

        # step6. 设置机器人离心机等关联设备状态
        if not self._set_linked_devices_status_to_robot(False):
            self._log_step("严重错误: 发送PLC许可信号失败，任务中止", "ERROR")
            return {"status": False, "message": "发送PLC许可信号失败，任务中止"}
        self._log_step("已向PLC发送: 离心机开启确认信号 (M10.4)", "INFO")

        # step7. 等待机器人任务完成
        if not self._wait_for_robot_task_completed(TaskType.CENT_TAKE, need_home_check=False):
            self._log_step(f"严重错误: {TASKS[TaskType.CENT_TAKE]}任务未完成，任务中止", "ERROR")
            return {"status": False, "message": f"{TASKS[TaskType.CENT_TAKE]}任务未完成，任务中止"}

        # step8. 取消设置机器人离心机等关联设备状态
        if not self._unset_linked_devices_status_to_robot(False):
            self._log_step("严重错误: 取消设置PLC许可信号失败，任务中止", "ERROR")
            return {"status": False, "message": "取消设置PLC许可信号失败，任务中止"}
        self._log_step("已向PLC发送: 离心机关闭确认信号 (M10.4)", "INFO")

        # step9. 关闭离心机门，并等待关闭完成，最多等5秒
        result = self.centrifuge_controller.close_door()
        if result.get("status") != "success":
            self._log_step(f"严重错误: 离心机门关闭失败: {result.get('message')}", "ERROR")
            return {"status": False, "message": f"离心机门关闭失败: {result.get('message')}"}
        if not self._wait_for_centrifuge_door_operation_completed(CentrifugeDoorStatus.CLOSED):
            self._log_step("严重错误: 离心机门未关闭，任务中止", "ERROR")
            return {"status": False, "message": "离心机门未关闭，任务中止"}

        return {"status": True, "message": f"{TASKS[TaskType.CENT_TAKE]}任务完成"}

    def _task_cent_run(self, time: int = 120, rpm: int = 500) -> Dict[str, Any]:
        """离心机运行任务"""
        try:
            # step1. 设置时间和转速
            result = self.centrifuge_controller.set_time(time)
            if not result.get("status"):
                self._log_step(f"严重错误: 离心机时间设置失败: {result.get('message')}", "ERROR")
                return {"status": False, "message": f"离心机时间设置失败: {result.get('message')}"}
            result = self.centrifuge_controller.set_speed(rpm)
            if not result.get("status"):
                self._log_step(f"严重错误: 离心机转速设置失败: {result.get('message')}", "ERROR")
                return {"status": False, "message": f"离心机转速设置失败: {result.get('message')}"}

            # step2. 启动离心机
            self._log_step(f"正在启动离心机...", "INFO")
            result = self.centrifuge_controller.start()
            if not result.get("status"):
                self._log_step(f"离心机启动失败，重试: {result.get('message')}", "WARNING")
                result = self.centrifuge_controller.start()
                if not result.get("status"):
                    self._log_step(f"离心机启动失败，重试: {result.get('message')}", "ERROR")
                    return {"status": False, "message": f"离心机启动失败: {result.get('message')}"}

            self._log_step(f"离心机运行中...", "INFO")

            # step3. 等待离心机运行完成
            if not self._wait_for_centrifuge_completed(time):
                self._log_step("严重错误: 离心机运行时间未完成，任务中止", "ERROR")

            # step4. 停止离心机，确保离心机状态已经停止
            result = self.centrifuge_controller.stop()
            if not result.get("status"):
                self._log_step(f"离心机停止失败，重试: {result.get('message')}", "WARNING")
                result = self.centrifuge_controller.stop()
                if not result.get("status"):
                    self._log_step(f"离心机停止失败，重试: {result.get('message')}", "ERROR")
            if not self._wait_for_centrifuge_stopped():
                self._log_step("严重错误: 离心机未停止，任务中止", "ERROR")
                return {"status": False, "message": "离心机未停止，任务中止"}
            
            return {"status": True, "message": f"离心机运行任务完成"}
        except Exception as e:
            self._log_step(f"严重错误: 离心机运行任务失败: {e}", "ERROR")
            return {"status": False, "message": f"离心机运行任务失败: {e}"}

    def _task_shelf_drop(self, shelf_id: int) -> Dict[str, Any]:
        """货架放任务（离心机 -> 货架2）
        - 机器人将离心机中的样品取出放入货架2
        - PLC写入任务时，sta表示货架ID，qty表示放料位置，这里sta需要和qty一致

        :param shelf_id: 货架ID
        :return: 任务状态
        """
        # step1. 获取机器人状态，如果机器人空闲则可以上料
        sys_status = self.robot_controller.get_system_status()
        if sys_status != RobotSystemStatus.IDLE:
            self._log_step("机器人繁忙，无法从离心机取样", "ERROR")
            return {"status": False, "message": "机器人繁忙，无法从离心机取样"}

        # step2. 直接下发任务并启动机器人，这里要求工位号与取放位置一致
        if not self.robot_controller.write_task(TaskType.SHELF_DROP.value, shelf_id, shelf_id):
            self._log_step("机器人任务数据写入失败，终止放入货架2任务流程", "ERROR")
            return {"status": False, "message": "任务数据写入失败，终止放入货架2任务流程"}
        
        time.sleep(0.5)

        # step3. 启动机器人
        if not self.robot_controller.dispatch_task():
            self._log_step("机器人任务下发失败，终止放入货架2任务流程", "ERROR")
            return {"status": False, "message": "机器人任务下发失败，终止放入货架2任务流程"}

        self._log_step(f"PLC任务 {TASKS[TaskType.SHELF_DROP]} 已启动，等待完成...", "INFO")

        # step4. 等待机器人响应启动指令，最多等10秒让它动起来，必须先确认为"运行中"，防止假完成
        self._log_step(f"正在等待机器人响应启动指令...", "INFO")
        if not self._wait_for_robot_started():
            self._log_step("严重错误: 机器人未响应启动指令(超时10s)，任务中止", "ERROR")
            return {"status": False, "message": "机器人未响应启动指令(超时10s)，任务中止"}

        # step5. 等待机器人任务完成
        if not self._wait_for_robot_task_completed(TaskType.SHELF_DROP, need_home_check=True):
            self._log_step(f"严重错误: {TASKS[TaskType.SHELF_DROP]}任务未完成，任务中止", "ERROR")
            return {"status": False, "message": f"{TASKS[TaskType.SHELF_DROP]}任务未完成，任务中止"}

        return {"status": True, "message": f"{TASKS[TaskType.SHELF_DROP]}任务完成"}

    def _return_with_error(self, message: str) -> dict:
        """返回错误结果"""
        self.running = False
        return {"status": False, "message": message}

    def load(self, shelf_id: int, oven_id: int, qty: int) -> Dict[str, Any]:
        """上料流程（货架1 -> 炉子）"""
        
        if not self.robot_controller.connect():
            return {"status": False, "message": "机器人连接失败"}
        if not self.door_controller.connect():
            return {"status": False, "message": "玻璃门连接失败"}
        if not self.oven_controller.connect():
            return {"status": False, "message": "加热炉连接失败"}
        if not self.centrifuge_controller.connect():
            return {"status": False, "message": "离心机连接失败"}

        ################################################################
        # === 步骤 1: 货架取 ===
        ################################################################
        result = self._task_shelf_take(shelf_id, qty)
        if not result.get("status"):
            self._log_step(f"严重错误: 货架取任务失败: {result.get('message')}", "ERROR")
            return {"status": False, "message": f"货架取任务失败: {result.get('message')}"}
        
        self._log_step(f"[货架1取]任务完成: {result.get('message')}", "SUCCESS")

        ################################################################
        # === 步骤 2: 炉子放 ===
        ################################################################
        result = self._task_oven_drop(oven_id, qty)
        if not result.get("status"):
            self._log_step(f"严重错误: 炉子放任务失败: {result.get('message')}", "ERROR")
            return {"status": False, "message": f"炉子放任务失败: {result.get('message')}"}
        
        self._log_step(f"[炉子放]任务完成: {result.get('message')}", "SUCCESS")

        return {"status": True, "message": "上料流程完成"}

    def unload(self, shelf_id: int, oven_id: int, qty: int) -> Dict[str, Any]:
        '''（炉子 -> 离心机 -> 货架2）'''
        if not self.robot_controller.connect():
            return {"status": False, "message": "机器人连接失败"}
        if not self.door_controller.connect():
            return {"status": False, "message": "玻璃门连接失败"}
        if not self.oven_controller.connect():
            return {"status": False, "message": "加热炉连接失败"}
        if not self.centrifuge_controller.connect():
            return {"status": False, "message": "离心机连接失败"}

        ################################################################
        # === 步骤 1: 炉子取 ===
        ################################################################
        result = self._task_oven_take(oven_id, qty)
        if not result.get("status"):
            self._log_step(f"严重错误: 炉子取任务失败: {result.get('message')}", "ERROR")
            return {"status": False, "message": f"炉子取任务失败: {result.get('message')}"}
        
        self._log_step(f"[炉子取]任务完成: {result.get('message')}", "SUCCESS")

        ################################################################
        # === 步骤 2: 离心机放 ===
        ################################################################
        result = self._task_cent_drop()
        if not result.get("status"):
            self._log_step(f"严重错误: 离心机放任务失败: {result.get('message')}", "ERROR")
            return {"status": False, "message": f"离心机放任务失败: {result.get('message')}"}
        
        self._log_step(f"[离心机放]任务完成: {result.get('message')}", "SUCCESS")

        ################################################################
        # === 步骤 3: 运行离心机 ===
        ################################################################
        result = self._task_cent_run(120, 500)
        if not result.get("status"):
            self._log_step(f"严重错误: 离心机运行任务失败: {result.get('message')}", "ERROR")
            return {"status": False, "message": f"离心机运行任务失败: {result.get('message')}"}
        
        self._log_step(f"[离心机运行]完成: {result.get('message')}", "SUCCESS")

        ################################################################
        # === 步骤 4: 离心机取 ===
        ################################################################

        result = self._task_cent_take()
        if not result.get("status"):
            self._log_step(f"严重错误: 离心机取任务失败: {result.get('message')}", "ERROR")
            return {"status": False, "message": f"离心机取任务失败: {result.get('message')}"}
        
        self._log_step(f"[离心机取]任务完成: {result.get('message')}", "SUCCESS")

        ################################################################
        # === 步骤 5: 货架放 ===
        ################################################################
        result = self._task_shelf_drop(shelf_id)
        if not result.get("status"):
            self._log_step(f"严重错误: 货架放任务失败: {result.get('message')}", "ERROR")
            return {"status": False, "message": f"货架放任务失败: {result.get('message')}"}
        
        self._log_step(f"[货架2放]任务完成: {result.get('message')}", "SUCCESS")

        return {"status": True, "message": "下料流程完成"}

    def run(self, oven_id: int, qty: int, curve_points: List[CurvePoint]):

        try:
            self.running = True
            #########################################################
            # 1. 上料 #
            #########################################################
            result = self.load(ShelfType.SHELF_1.value, oven_id, qty)
            if not result.get("status"):
                self._log_step(f"严重错误: 上料任务失败: {result.get('message')}", "ERROR")
                return self._return_with_error(f"上料任务失败: {result.get('message')}")

            #########################################################
            # 2. 燃烧 #
            #########################################################
            result = self._task_oven_burn(oven_id, curve_points)
            if not result.get("status"):
                self._log_step(f"严重错误: 燃烧任务失败: {result.get('message')}", "ERROR")
                return self._return_with_error(f"燃烧任务失败: {result.get('message')}")

            self._log_step(f"燃烧任务完成: {result.get('message')}", "SUCCESS")

            #########################################################
            # 3. 下料 #
            #########################################################
            result = self.unload(ShelfType.SHELF_2.value, oven_id, qty)
            if not result.get("status"):
                self._log_step(f"严重错误: 下料任务失败: {result.get('message')}", "ERROR")
                return self._return_with_error(f"下料任务失败: {result.get('message')}")

            self._log_step(f"下料任务完成: {result.get('message')}", "SUCCESS")

            return {"status": True, "message": "热处理流程完成"}
        except Exception as e:
            self._log_step(f"严重错误: 热处理流程失败: {e}", "ERROR")
            return self._return_with_error(f"热处理流程失败: {e}")
        finally:
            self.running = False

    def get_summary(self) -> dict:
        """获取热处理流程总结"""

        robot_summary = robot_controller.get_running_status()
        oven_summary = oven_controller.get_running_status()
        centrifuge_summary = centrifuge_controller.get_running_status()

        return {
            "status": True,
            "summary": {
                "robot": robot_summary,
                "oven": oven_summary,
                "centrifuge": centrifuge_summary
            }
        }

from devices.robot_core import robot_controller
from devices.door_core import door_controller
from devices.centrifuge_core import centrifuge_controller
from devices.oven_core import oven_controller
thermal_flow_mgr = ThermalFlowManager(robot_controller, door_controller, centrifuge_controller, oven_controller)