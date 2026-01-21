"""
XRD衍射仪试验工作流
根据XRD使用教程和API文档实现完整的试验流程
支持单样品模式和多样品模式
"""
import time
import threading
from typing import Dict, Any, List, Optional
from datetime import datetime

from devices.xrd_core import XRDController, xrd_controller
from logger import sys_logger as logger


class XRDFlowManager:
    """XRD衍射仪试验流程管理器"""
    
    def __init__(self, xrd_controller: XRDController, logger=logger):
        self.xrd_controller = xrd_controller
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
        self.logger.log(f"[XRD流程] {message}", level)
    
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
        if not self.xrd_controller.is_connected:
            self._log_step("设备未连接，尝试连接...", "WARN")
            if not self.xrd_controller.connect():
                self._log_step("设备连接失败", "ERROR")
                return False
        
        # 检查设备状态
        status = self.xrd_controller.get_sample_status()
        if not status.get("status"):
            self._log_step(f"设备状态异常: {status.get('message', '未知错误')}", "ERROR")
            return False
        
        return True
    
    def prepare_device(self, voltage: float = 40.0, current: float = 30.0) -> bool:
        """
        前期准备工作
        包括：开高压发生器、设置电压电流等
        
        :param voltage: 电压值 (kV)，默认40.0
        :param current: 电流值 (mA)，默认30.0
        :return: 是否成功
        """
        self._log_step("开始前期准备工作...", "INFO")
        
        # 1. 检查设备连接
        if not self._check_device_ready():
            return False
        
        # 2. 开启高压发生器
        self._log_step("开启高压发生器...", "INFO")
        response = self.xrd_controller.set_power_on()
        if not response.get("status"):
            self._log_step(f"开启高压失败: {response.get('message')}", "ERROR")
            return False
        time.sleep(1)  # 等待高压稳定
        
        # 3. 设置电压电流
        self._log_step(f"设置电压电流 (电压:{voltage}kV, 电流:{current}mA)...", "INFO")
        response = self.xrd_controller.set_voltage_current(voltage, current)
        if not response.get("status"):
            self._log_step(f"设置电压电流失败: {response.get('message')}", "ERROR")
            return False
        time.sleep(1)  # 等待设置生效
        
        # 4. 启动自动模式
        self._log_step("启动自动模式...", "INFO")
        response = self.xrd_controller.start_auto_mode(True)
        if not response.get("status"):
            self._log_step(f"启动自动模式失败: {response.get('message')}", "ERROR")
            return False
        
        self._log_step("前期准备工作完成", "SUCCESS")
        return True
    
    def single_sample_test(self, 
                          sample_id: str,
                          start_theta: float = 10.0,
                          end_theta: float = 80.0,
                          increment: float = 0.05,
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
        self._log_step(f"开始单样品测试流程 - 样品ID: {sample_id}", "INFO")
        
        if not self._check_device_ready():
            return {"status": False, "message": "设备未就绪"}
        
        # 步骤1: 检查是否允许上样
        self._log_step("步骤1: 检查是否允许上样...", "INFO")
        response = self.xrd_controller.get_sample_request()
        if not response.get("status"):
            error_msg = response.get("message", "不允许上样")
            self._log_step(f"上样请求被拒绝: {error_msg}", "ERROR")
            return {"status": False, "message": error_msg}
        
        # 步骤2: 等待人工上样（提示用户将样品放到上样台）
        self._log_step("步骤2: 等待人工上样...", "INFO")
        if not self._wait_for_confirm("请将样品放到上样台，然后点击确认", timeout=300):
            return {"status": False, "message": "上样确认超时或取消"}
        
        # 步骤3: 发送样品信息和采集参数
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
            return {"status": False, "message": error_msg}
        
        self._log_step(f"采集参数已发送: 起始角度={start_theta}°, 结束角度={end_theta}°, 步长={increment}°, 曝光时间={exp_time}s", "SUCCESS")
        
        # 步骤4: 等待测试完成（可选）
        if wait_for_completion:
            self._log_step("步骤4: 等待测试完成...", "INFO")
            if not self._wait_for_test_completion(check_interval):
                return {"status": False, "message": "测试未完成或超时"}
        
        # 步骤5: 获取测试数据
        self._log_step("步骤5: 获取测试数据...", "INFO")
        data_response = self.xrd_controller.get_current_acquire_data()
        
        # 步骤6: 下样
        self._log_step("步骤6: 下样...", "INFO")
        if not self._wait_for_confirm("请确认样品已取出，然后点击确认", timeout=300):
            return {"status": False, "message": "下样确认超时或取消"}
        
        # 发送下样完成信号（单样品模式，工位通常是1）
        down_response = self.xrd_controller.get_sample_down(1)
        if down_response.get("status"):
            self._log_step("下样成功", "SUCCESS")
        else:
            self._log_step(f"下样失败: {down_response.get('message')}", "WARN")
        
        self.xrd_controller.send_sample_down_ready()
        
        result = {
            "status": True,
            "sample_id": sample_id,
            "test_params": {
                "start_theta": start_theta,
                "end_theta": end_theta,
                "increment": increment,
                "exp_time": exp_time
            },
            "data": data_response if data_response.get("status") else None,
            "message": "单样品测试流程完成"
        }
        
        self._log_step(f"单样品测试流程完成 - 样品ID: {sample_id}", "SUCCESS")
        return result
    
    def multi_sample_test(self,
                          samples: List[Dict[str, Any]],
                          wait_for_all: bool = True,
                          check_interval: float = 5.0) -> Dict[str, Any]:
        """
        多样品模式测试流程（最多30个样品）
        
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
        self._log_step(f"开始多样品测试流程 - 样品数量: {len(samples)}", "INFO")
        
        if len(samples) > 30:
            return {"status": False, "message": "样品数量超过30个，最多支持30个样品"}
        
        if not self._check_device_ready():
            return {"status": False, "message": "设备未就绪"}
        
        results = []
        station_counter = 1
        
        for idx, sample in enumerate(samples, 1):
            sample_id = sample.get("sample_id", f"Sample_{idx}")
            station = sample.get("station", station_counter)
            station_counter = station + 1 if station_counter == station else station_counter + 1
            
            self._log_step(f"处理样品 {idx}/{len(samples)}: {sample_id} (工位{station})", "INFO")
            
            # 步骤1: 检查是否允许上样
            self._log_step(f"步骤1: 检查是否允许上样 (样品{idx})...", "INFO")
            response = self.xrd_controller.get_sample_request()
            if not response.get("status"):
                error_msg = response.get("message", "不允许上样")
                self._log_step(f"上样请求被拒绝: {error_msg}", "ERROR")
                results.append({
                    "sample_id": sample_id,
                    "station": station,
                    "status": False,
                    "message": error_msg
                })
                continue
            
            # 步骤2: 等待人工上样
            self._log_step(f"步骤2: 等待人工上样 (样品{idx}, 工位{station})...", "INFO")
            if not self._wait_for_confirm(f"请将样品{sample_id}放到工位{station}，然后点击确认", timeout=300):
                results.append({
                    "sample_id": sample_id,
                    "station": station,
                    "status": False,
                    "message": "上样确认超时或取消"
                })
                continue
            
            # 步骤3: 发送样品信息和采集参数
            self._log_step(f"步骤3: 发送样品信息和采集参数 (样品{idx})...", "INFO")
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
                results.append({
                    "sample_id": sample_id,
                    "station": station,
                    "status": False,
                    "message": error_msg
                })
                continue
            
            results.append({
                "sample_id": sample_id,
                "station": station,
                "status": True,
                "message": "样品已上样，等待测试"
            })
        
        # 步骤4: 等待所有测试完成（可选）
        if wait_for_all:
            self._log_step("步骤4: 等待所有样品测试完成...", "INFO")
            self._wait_for_test_completion(check_interval, total_samples=len(samples))
        
        # 步骤5: 获取所有样品数据并下样
        self._log_step("步骤5: 获取测试数据并下样...", "INFO")
        for idx, sample in enumerate(samples, 1):
            sample_id = sample.get("sample_id", f"Sample_{idx}")
            station = sample.get("station", idx)
            
            # 获取数据
            data_response = self.xrd_controller.get_current_acquire_data()
            
            # 下样
            self._log_step(f"下样: 样品{sample_id} (工位{station})...", "INFO")
            if not self._wait_for_confirm(f"请确认样品{sample_id}已从工位{station}取出，然后点击确认", timeout=300):
                continue
            
            down_response = self.xrd_controller.get_sample_down(station)
            if down_response.get("status"):
                # 更新结果
                for result in results:
                    if result.get("sample_id") == sample_id:
                        result["data"] = down_response.get("sample_info")
                        result["down_status"] = True
                        break
            else:
                self._log_step(f"下样失败 (工位{station}): {down_response.get('message')}", "WARN")
        
        # 发送下样完成信号
        self.xrd_controller.send_sample_down_ready()
        
        result = {
            "status": True,
            "total_samples": len(samples),
            "results": results,
            "message": "多样品测试流程完成"
        }
        
        self._log_step(f"多样品测试流程完成 - 共处理 {len(samples)} 个样品", "SUCCESS")
        return result
    
    def _wait_for_test_completion(self, check_interval: float = 5.0, total_samples: int = 1) -> bool:
        """
        等待测试完成
        
        :param check_interval: 检查间隔（秒）
        :param total_samples: 总样品数（用于多样品模式）
        :return: 是否完成
        """
        self._log_step("等待测试完成...", "INFO")
        start_time = time.time()
        max_wait_time = 3600 * 24  # 最多等待24小时
        
        while self.running:
            if time.time() - start_time > max_wait_time:
                self._log_step("等待测试完成超时", "ERROR")
                return False
            
            # 检查设备状态
            status = self.xrd_controller.get_sample_status()
            if status.get("status") and "Station" in status:
                station_info = status["Station"]
                ready_stations = station_info.get("ready station", [])
                
                if total_samples == 1:
                    # 单样品模式：检查是否有已完成的数据
                    data_response = self.xrd_controller.get_current_acquire_data()
                    if data_response.get("status") and "Energy" in data_response:
                        self._log_step("测试完成，已获取数据", "SUCCESS")
                        return True
                else:
                    # 多样品模式：检查已完成工位数
                    if len(ready_stations) >= total_samples:
                        self._log_step(f"所有样品测试完成 (已完成工位: {ready_stations})", "SUCCESS")
                        return True
                    else:
                        self._log_step(f"测试进行中... (已完成: {len(ready_stations)}/{total_samples})", "INFO")
            
            time.sleep(check_interval)
        
        return False
    
    def get_test_data(self, sample_id: Optional[str] = None) -> Dict[str, Any]:
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
    
    def shutdown_device(self) -> bool:
        """
        关闭设备（关闭高压、停止自动模式）
        
        :return: 是否成功
        """
        self._log_step("关闭设备...", "INFO")
        
        if not self.xrd_controller.is_connected:
            return True  # 已断开，无需操作
        
        # 关闭高压
        self._log_step("关闭高压发生器...", "INFO")
        response = self.xrd_controller.set_power_off()
        if not response.get("status"):
            self._log_step(f"关闭高压失败: {response.get('message')}", "WARN")
        
        # 停止自动模式
        self._log_step("停止自动模式...", "INFO")
        response = self.xrd_controller.start_auto_mode(False)
        if not response.get("status"):
            self._log_step(f"停止自动模式失败: {response.get('message')}", "WARN")
        
        self._log_step("设备关闭完成", "SUCCESS")
        return True

xrd_flow_manager = XRDFlowManager(xrd_controller)
