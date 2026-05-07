"""
XRD衍射仪试验工作流
根据XRD使用教程和API文档实现完整的试验流程
支持单样品模式和多样品模式
"""
import time
import threading
from typing import Dict, Any, List, Optional
from datetime import datetime

from devices.xrd_core import XRDController
from devices.mock_devices import get_xrd_controller
from logger import sys_logger as logger

try:
    import config
except Exception:
    config = None


class XRDFlowManager:
    """XRD衍射仪工序工作流管理器"""
    
    def __init__(self, xrd_controller: XRDController, logger=logger):
        self.xrd_controller = xrd_controller
        self.logger = logger
        self.running = False
        self._stop_requested = False  # 由 stop() 置位，run() 入口检查后清空，与 mix_flow/thermal_flow 一致
        self.current_step_info = "就绪"
        self.thread = None
        self.latest_data = None
        # 当前正在执行 XRD 的样品信息（供状态接口返回 scheme_index/scheme_id/sample_id）
        self.current_running_sample: Optional[Dict[str, Any]] = None

        # 确认信号事件（用于人工确认步骤）
        self.confirm_event = threading.Event()
        self.confirm_event.set()  # 默认设置为True
        # 当前等待确认时的提示文案（供编排层 get_status 的 next_action 使用，不依赖步骤日志字符串）
        self._pending_confirm_message: Optional[str] = None

    def get_pending_confirm(self) -> Optional[Dict[str, Any]]:
        """若当前处于「等待人工确认」则返回 {\"message\": \"...\"}，否则返回 None。供 experiment get_status 生成 next_action，避免依赖 current_step_info 文案。"""
        if not self.running or self._pending_confirm_message is None:
            return None
        if self.confirm_event.is_set():
            return None
        return {"message": self._pending_confirm_message}

    def user_confirm(self):
        """前端调用的确认方法"""
        self.logger.log(">>> 人工已确认，流程继续 <<<", "SUCCESS")
        self.confirm_event.set()

    def stop(self):
        self._stop_requested = True
        self.running = False
    
    def _log_step(self, message: str, level: str = "INFO"):
        """记录步骤日志"""
        self.current_step_info = message
        self.logger.log(f"[XRD流程] {message}", level)
    
    def _wait_for_confirm(self, message: str, timeout: Optional[float] = None):
        """等待人工确认"""
        self._pending_confirm_message = message
        self._log_step(f"等待确认: {message}", "WARN")
        self.confirm_event.clear()
        try:
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
        finally:
            self._pending_confirm_message = None

    def _wait_for_test_completion(self, check_interval: float = 5.0, total_samples: int = 1) -> bool:
        """
        等待测试完成
        
        :param check_interval: 检查间隔（秒）
        :param total_samples: 总样品数（用于多样品模式）
        :return: 是否完成
        """
        self._log_step("等待测试完成...", "INFO")
        start_time = time.time()
        max_wait_time = 60 * 60 * 24  # 最多等待24小时
        cap = getattr(config, "XRD_WAIT_CAP_SEC", 0) if config else 0
        if cap > 0:
            max_wait_time = min(max_wait_time, cap)
            self._log_step(f"等待测试完成上限 {cap} 秒", "INFO")

        while self.running:
            if time.time() - start_time > max_wait_time:
                self._log_step("等待测试完成超时", "ERROR")
                return False
            
            # 检查设备状态
            status = self.xrd_controller.get_sample_status()
            if status.get("status"):
                ready_stations = status.get("ready station", [])
                completed_samples = len(ready_stations)
                
                if completed_samples >= total_samples:
                    self._log_step("测试完成", "SUCCESS")
                    return True
                else:
                    self._log_step(f"测试进行中... (已完成: {completed_samples}/{total_samples})", "INFO")
                    # 获取实时数据
                    realtime_data = self.xrd_controller.get_current_acquire_data()
                    if realtime_data.get("status"):
                        energy = realtime_data.get("Energy")
                        intensity = realtime_data.get("Intensity")
                        # TODO 返回实时数据

            time.sleep(check_interval)
        
        return False
    
    def _wait_for_raise_voltage(self, check_interval: float = 5.0):
        '''等待升压完成'''

        self._log_step("等待升压", "INFO")
        start_time = time.time()
        max_wait_time = 60 * 60  # 最多等待1小时
        cap = getattr(config, "XRD_WAIT_CAP_SEC", 0) if config else 0
        if cap > 0:
            max_wait_time = min(max_wait_time, cap)
            self._log_step(f"等待升压上限 {cap} 秒", "INFO")

        while self.running:
            if time.time() - start_time > max_wait_time:
                self._log_step("等待升压超时", "ERROR")
                return False

            # 检查设备状态
            status = self.xrd_controller.get_sample_status()
            if status.get("status") \
                and status.get("xray status") == "ready" \
                and status.get("power status"):
                self._log_step("升压完成", "SUCCESS")
                return True
            
            time.sleep(check_interval)
        
        return False

    def _wait_for_voltage_current_stable(self, check_interval: float = 5.0, voltage: float = 40.0, current: float = 40.0):
        self._log_step("等待电压电流稳定", "INFO")
        start_time = time.time()
        max_wait_time = 60 * 60  # 最多等待1小时
        cap = getattr(config, "XRD_WAIT_CAP_SEC", 0) if config else 0
        if cap > 0:
            max_wait_time = min(max_wait_time, cap)
            self._log_step(f"等待电压电流稳定上限 {cap} 秒", "INFO")

        voltage_threshold = voltage * 0.95
        current_threshold = current * 0.95

        while self.running:
            if time.time() - start_time > max_wait_time:
                self._log_step("等待电压电流稳定超时", "ERROR")
                return False

            status = self.xrd_controller.get_sample_status()
            if status.get("status") \
                and status.get("current voltage") > voltage_threshold \
                and status.get("current current") > current_threshold:
                self._log_step(f"电压电流达到设定值：电压={status.get('current voltage')}, 电流={status.get('current current')}", "SUCCESS")
                return True
            else:
                self._log_step(f"电压电流不稳定: 电压={status.get('current voltage')}, 电流={status.get('current current')}", "WARN")

            time.sleep(check_interval)
        
        return False

    def _check_device_ready(self) -> bool:
        """检查设备是否就绪"""
        if not self.xrd_controller.is_connected:
            self._log_step("设备未连接，尝试连接...", "WARN")
            if not self.xrd_controller.connect():
                self._log_step("设备连接失败", "ERROR")
                return False
            else:
                self._log_step("设备连接成功")
        
        # 检查设备状态
        status = self.xrd_controller.get_sample_status()
        if not status.get("status"):
            self._log_step(f"设备状态异常: {status.get('message', '未知错误')}", "ERROR")
            return False
        
        return True
    
    def _prepare_device(self, check_interval: float = 5.0, voltage: float = 40.0, current: float = 40.0) -> bool:
        """
        前期准备工作
        包括：检查连接、升高压、设置检测电压电流等
        
        :param voltage: 电压值 (kV)，默认40.0
        :param current: 电流值 (mA)，默认40.0
        :return: 是否成功
        """
        self._log_step("开始前期准备工作...", "INFO")
        
        # 1. 检查设备连接
        if not self._check_device_ready():
            return False
        
        # 2. 启动自动模式
        self._log_step("启动自动模式...", "INFO")
        response = self.xrd_controller.start_auto_mode(True)
        if not response.get("status"):
            message = response.get("message")
            if message == "设备已启动自动测试运行" or "设备已启动自动测试运行" in message:
                self._log_step(f"设备已启动自动测试运行，请勿重试", "WARNING")
            else:
                self._log_step(f"启动自动模式失败: {response.get('message')}", "ERROR")
                return False

        # 3. 判断是否开启高压，如果没有开启则开启高压发生器
        self._log_step("开启高压发生器...", "INFO")
        status = self.xrd_controller.get_sample_status()
        if status.get("status") and not status.get("power status"):
            response = self.xrd_controller.set_power_on()
            if not response.get("status"):
                self._log_step(f"开启高压失败: {response.get('message')}", "ERROR")
                return False
            else:
                self._log_step(f"开启高压成功: {response}")
    
        # 4. 等待升压完成
        self._log_step("等待升压完成...", "INFO")
        if not self._wait_for_raise_voltage(check_interval):
            self._log_step("退出等待升压", "ERROR")
            return False
        
        # 5. 设置电压电流
        self._log_step(f"设置电压电流 (电压:{voltage}kV, 电流:{current}mA)...", "INFO")
        response = self.xrd_controller.set_voltage_current(voltage, current)
        if not response.get("status"):
            self._log_step(f"设置电压电流失败: {response.get('message')}", "ERROR")
            return False
        else:
            self._log_step(f"设置电压电流成功：{response}")

        # 6. 等待电压电流稳定
        self._log_step("等待电压电流稳定...", "INFO")
        if not self._wait_for_voltage_current_stable(check_interval, voltage, current):
            self._log_step("等待电压电流稳定超时", "ERROR")
            return False
        
        self._log_step("前期准备工作完成", "SUCCESS")
        return True
    
    def _shutdown_device(self) -> bool:
        """
        恢复待机模式，退出自动模式
        
        :return: 是否成功
        """
        self._log_step("恢复待机模式，退出自动模式...", "INFO")
        
        # 恢复待机模式电压电流
        self.xrd_controller.set_voltage_current(20.0, 5.0)
        # 退出自动模式
        self.xrd_controller.start_auto_mode(False)
        return True

    def _return_with_error(self, message: str) -> dict:
        """返回错误结果"""
        self.running = False
        return {"status": False, "message": message}
    
    def _return_with_success(self, message: str, data: Optional[Any] = None) -> dict:
        """返回成功结果"""
        self.running = False
        return {"status": True, "message": message, "data": data}

    def run_single_sample_test(self,
                          sample_id: str,
                          start_theta: float = 5.0,
                          end_theta: float = 120.0,
                          increment: float = 0.01,
                          exp_time: float = 0.1,
                          wait_for_completion: bool = True,
                          check_interval: float = 5.0) -> Dict[str, Any]:
        """
        单样品模式测试流程
        
        :param sample_id: 样品标识符
        :param start_theta: 起始角度（≥5°），默认10.0
        :param end_theta: 结束角度（≥5.5°，且必须大于start_theta），默认80.0
        :param increment: 角度增量（≥0.005），默认0.05
        :param exp_time: 曝光时间（0.1-5.0秒），默认0.1
        :param wait_for_completion: 是否等待测试完成，默认True
        :param check_interval: 检查测试状态的间隔（秒），默认5.0
        :return: 测试结果字典
        """
        self._log_step(f"开始单样品测试流程：样品ID={sample_id}", "INFO")
        try:
            self.running = True
            self.current_running_sample = {"sample_id": sample_id}
            ################################################################
            # 步骤0: 准备设备 #
            ################################################################
            self._log_step("步骤0: 准备设备：设置自动模式、升高压、设置电压电流、等待电压电流稳定...", "INFO")
            if not self._prepare_device(check_interval):
                return self._return_with_error("设备准备失败")

            ################################################################
            # 步骤1: 检查是否允许上样
            ################################################################
            self._log_step("步骤1: 检查是否允许上样...", "INFO")
            response = self.xrd_controller.get_sample_request()
            if not response.get("status"):
                error_msg = response.get("message", "不允许上样")
                self._log_step(f"上样请求被拒绝: {error_msg}", "ERROR")
                return self._return_with_error(error_msg)

            self._log_step(f"是否允许上样结果：{response}")
            
            ################################################################
            # 步骤2: 等待人工上样（提示用户将样品放到上样台） #
            ################################################################
            self._log_step("步骤2: 等待人工上样...", "INFO")
            if not self._wait_for_confirm("请确认将样品放入XRD试验台", timeout=1200):
                return self._return_with_error("上样确认超时或取消")
            
            ################################################################
            # 步骤3: 发送样品信息和采集参数
            ################################################################
            self._log_step("步骤3: 发送样品信息和采集参数...", "INFO")
            response = self.xrd_controller.send_sample_ready(
                                                            sample_id=sample_id,
                                                            start_theta=start_theta,
                                                            end_theta=end_theta,
                                                            increment=increment,
                                                            exp_time=exp_time
                                                        )
            if not response.get("status"):
                error_msg = response.get("message", "发送采集参数失败")
                self._log_step(f"发送采集参数失败: {error_msg}", "ERROR")
                return self._return_with_error(error_msg)

            self._log_step(f"发送采集参数成功: 起始角度={start_theta}°, 结束角度={end_theta}°, 步长={increment}°, 曝光时间={exp_time}s", "SUCCESS")
            
            ################################################################
            # 步骤4: 等待测试完成（可选） #
            ################################################################
            if wait_for_completion:
                self._log_step("步骤4: 等待测试完成...", "INFO")
                if not self._wait_for_test_completion(check_interval):
                    return self._return_with_error("测试未完成或超时")

            self._log_step("测试完成", "SUCCESS")
            
            ################################################################
            # 步骤5: 发送下样完成信号（单样品模式，工位通常是1） #
            ################################################################
            down_response = self.xrd_controller.get_sample_down(1)
            if not down_response.get("status"):
                self._log_step(f"下样失败: {down_response.get('message')}", "WARN")
            else:
                self._log_step("下样成功", "SUCCESS")
                self.latest_data = down_response
                # self._log_step(f"下样结果：{down_response}")
            
            down_response = self.xrd_controller.send_sample_down_ready()
            if not down_response.get("status"):
                self._log_step(f"发送下样完成信号失败: {down_response.get('message')}", "ERROR")
                return self._return_with_error("发送下样完成信号失败")
            else:
                self._log_step(f"发送下样完成信号成功: {down_response}")
            
            time.sleep(3)
            
            ################################################################
            # 步骤6: 恢复待机模式 #
            ################################################################
            self._shutdown_device()
            
            self._log_step(f"单样品测试流程完成：样品ID={sample_id}", "SUCCESS")
            return self._return_with_success(f"单样品测试流程完成：样品ID={sample_id}", self.latest_data)
        except Exception as e:
            return self._return_with_error(f"单样品测试流程失败: {e}")
        finally:
            self.running = False
            # 不在此处清 current_running_sample，以便 phase 仍为 xrd_running 时状态接口能返回当前/刚完成的样品；下次 run 会覆盖
    
    def run_multi_sample_test(self,
                          samples: List[Dict[str, Any]],
                          wait_for_all: bool = True,
                          check_interval: float = 5.0) -> Dict[str, Any]:
        """
        多样品模式测试流程（最多30个样品）。
        流程为顺序测试：对每个样品依次执行「等待人工上样确认 → send_sample_ready」；同一套确认接口（如 POST /api/flow/xrd/confirm）需在每次提示时调用一次，共 N 次上样确认 + N 次下样确认。
        注意：单样品 run_single_sample_test 已在现场设备验证；本多样品流程尚未在现场设备上完整验证，上线前需现场联调。

        :param samples: 样品列表，每个样品包含：
            - sample_id: 样品标识符
            - start_theta: 起始角度（≥5°）
            - end_theta: 结束角度（≥5.5°，且必须大于start_theta）
            - increment: 角度增量（≥0.005）
            - exp_time: 曝光时间（0.1-5.0秒）
            - station: 工位号（1-30，可选，如果不提供则按顺序分配）
        :param wait_for_all: 是否等待所有样品测试完成，默认True
        :param check_interval: 检查测试状态的间隔（秒），默认5.0
        :return: 测试结果字典
        """
        self._log_step(f"开始多样品测试流程：样品数量={len(samples)}", "INFO")
        
        if len(samples) > 30:
            return self._return_with_error("样品数量超过30个，最多支持30个样品")

        self.running = True
        self.current_running_sample = None
        try:
            ################################################################
            # 步骤0: 准备设备 #
            ################################################################
            self._log_step("步骤0: 准备设备：设置自动模式、升高压、设置电压电流、等待电压电流稳定...", "INFO")
            if not self._prepare_device(check_interval):
                return self._return_with_error("设备准备失败")

            results = []
            station_counter = 1
            for idx, sample in enumerate(samples, 1):
                sample_id = sample.get("sample_id", f"Sample_{idx}")
                station = sample.get("station", station_counter)
                station_counter = station + 1
                results.append({
                    "sample_id": sample_id,
                    "station": station,
                    "status": True,
                    "message": "样品等待上样",
                    "data": None
                })
            for idx, sample in enumerate(samples, 1):
                sample_id = sample.get("sample_id", f"Sample_{idx}")
                result = None
                for _result in results:
                    if _result["sample_id"] == sample_id:
                        result = _result
                        break
                station = result["station"]
                self.current_running_sample = {
                    "sample_id": sample_id,
                    "station": station,
                    "index": idx,
                    "scheme_index": sample.get("scheme_index"),
                    "scheme_id": sample.get("scheme_id"),
                }
                self._log_step(f"处理样品 {idx}/{len(samples)}: {sample_id} (工位{station})", "INFO")
                # 步骤1: 检查是否允许上样
                self._log_step(f"步骤1: 检查是否允许上样 (样品{idx})...", "INFO")
                response = self.xrd_controller.get_sample_request()
                if not response.get("status"):
                    error_msg = response.get("message", "不允许上样")
                    self._log_step(f"上样请求被拒绝: {error_msg}", "ERROR")
                    return self._return_with_error(f"上样请求被拒绝: {error_msg}")
                # 步骤2: 等待人工上样
                self._log_step(f"步骤2: 等待人工上样 (样品{idx}, 工位{station})...", "INFO")
                if not self._wait_for_confirm(f"请将样品{sample_id}放到工位{station}，然后点击确认", timeout=300):
                    result["status"] = False
                    result["message"] = "上样确认超时或取消"
                    continue
            # 步骤3: 多样品模式，所有样品的get_sample_request发送完成后，再统一发送send_sample_ready
            self._log_step(f"步骤3: 发送样品信息和采集参数...", "INFO")
            response = self.xrd_controller.send_sample_ready(
                sample_id=sample_id,
                start_theta=sample.get("start_theta", 10.0),
                end_theta=sample.get("end_theta", 80.0),
                increment=sample.get("increment", 0.05),
                exp_time=sample.get("exp_time", 0.1)
            )
            if not response.get("status"):
                error_msg = response.get("message", "发送采集参数失败")
                self._log_step(f"发送采集参数失败: {error_msg}", "ERROR")
                for result in results:
                    result["status"] = False
                    result["message"] = f"发送采集就绪信号失败: {error_msg}"
                return self._return_with_error(f"发送采集就绪信号失败: {error_msg}")
            for result in results:
                result["status"] = True
                result["message"] = f"发送采集就绪信号成功: {response}"
            # 步骤4: 等待所有测试完成（可选）
            if wait_for_all:
                self._log_step("步骤4: 等待所有样品测试完成...", "INFO")
                self._wait_for_test_completion(check_interval, total_samples=len(samples))
            # 步骤5: 获取所有样品数据并下样
            self._log_step("步骤5: 获取测试数据并下样...", "INFO")
            for idx, sample in enumerate(samples, 1):
                sample_id = sample.get("sample_id", f"Sample_{idx}")
                result = None
                for _result in results:
                    if _result["sample_id"] == sample_id:
                        result = _result
                        break
                station = result["station"]
                down_response = self.xrd_controller.get_sample_down(station)
                if down_response.get("status"):
                    result["data"] = down_response.get("sample_info")
                    result["status"] = True
                    result["message"] = f"下样成功"
                else:
                    self._log_step(f"下样失败 (工位{station}): {down_response.get('message')}", "WARN")
                self._log_step(f"下样: 样品{sample_id} (工位{station})...", "INFO")
                if not self._wait_for_confirm(f"请确认样品{sample_id}已从工位{station}取出，然后点击确认", timeout=300):
                    continue
            # 发送下样完成信号
            self.xrd_controller.send_sample_down_ready()

            rtn = {
                "status": True,
                "total_samples": len(samples),
                "results": results,
                "message": "多样品测试流程完成"
            }
            self._log_step(f"多样品测试流程完成 - 共处理 {len(samples)} 个样品", "SUCCESS")
            return rtn
        finally:
            self.running = False
            # 不在此处清 current_running_sample，以便 phase 仍为 xrd_running 时状态接口能返回；下次 run 会覆盖

    def get_realtime_data(self, sample_id: Optional[str] = None) -> Dict[str, Any]:
        """
        获取测试数据
        
        :param sample_id: 样品ID（可选，用于标识）
        :return: 测试数据字典
        """
        self._log_step("获取测试数据...", "INFO")
        
        if not self._check_device_ready():
            return {"status": False, "message": "设备未就绪"}
        
        response = self.xrd_controller.get_current_acquire_data()
        if response.get("status"):
            if "Energy" in response and "Intensity" in response:
                self._log_step("成功获取测试数据", "SUCCESS")
                return {
                    "status": True,
                    "sample_id": sample_id,
                    "energy": response.get("Energy", []),
                    "intensity": response.get("Intensity", []),
                    "timestamp": response.get("timestamp")
                }
            else:
                return {
                    "status": False,
                    "message": response.get("message", "当前无样品数据")
                }
        else:
            return {
                "status": False,
                "message": response.get("message", "获取数据失败")
            }
    
    def get_latest_data(self):
        """
        获取最新数据
        :return: 数据字典
        """
        if "sample_info" in self.latest_data:
            sample_info = self.latest_data["sample_info"]
            return {
                "status": True,
                "message": "获取数据成功",
                "data": {
                    "sample_id": sample_info["id_number"],
                    "theta2": sample_info["2theta"],
                    "intensity": sample_info["intensity"],
                    "timestamp": self.latest_data["timestamp"]
                }
            }
        elif "2theta" in self.latest_data and "intensity" in self.latest_data:
            return {
                "status": True,
                "message": "获取数据成功",
                "data": {
                    "sample_id": self.latest_data["id_number"],
                    "theta2": self.latest_data["2theta"],
                    "intensity": self.latest_data["intensity"],
                    "timestamp": self.latest_data["timestamp"]
                }
            }
        else:
            return {
                "status": False,
                "message": "获取数据失败",
                "data": None
            }

    def run(self,
            single: bool = True,
            sample_id: str = "XY000",
            start_theta: float = 5.0,
            end_theta: float = 120.0,
            increment: float = 0.01,
            exp_time: float = 0.1,
            samples: Optional[List[Dict[str, Any]]] = None,
        ) -> Dict[str, Any]:
        """
        单样品或多样品 XRD 测试。single=True 时用 sample_id/start_theta 等；single=False 时用 samples 列表（每项含 sample_id、start_theta、end_theta 等），便于与配方 scheme_id 关联。
        """
        if self._stop_requested:
            self._stop_requested = False
            return {"status": False, "message": "用户停止实验"}
        if single:
            if start_theta <= 5.0:
                raise Exception("起始角度需要>5.0")
            if end_theta > 120.0:
                raise Exception("结束角度需要<120.0")
            if end_theta < start_theta:
                raise Exception("结束角度应该大于起始角度")
            if end_theta - start_theta < 10:
                raise Exception("起始角度和结束角度之差应该≥10")
            if exp_time >= 5.0:
                raise Exception("曝光时间不能>5.0s")
            return self.run_single_sample_test(sample_id, start_theta, end_theta, increment, exp_time)
        else:
            if not samples or len(samples) == 0:
                raise Exception("多样品模式需传入 samples 列表")
            return self.run_multi_sample_test(
                samples=samples,
                wait_for_all=True,
                check_interval=5.0,
            )

    def get_summary(self) -> dict:
        """获取XRD流程总结"""
        xrd_summary = self.xrd_controller.get_running_status()
        return {
            "status": True,
            "summary": {
                "xrd": xrd_summary
            }
        }

xrd_flow_mgr = XRDFlowManager(get_xrd_controller())
