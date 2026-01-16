"""
配料设备控制模块
基于REST API控制配料设备，实现任务管理功能
"""
import requests
import time
from typing import Dict, Any, List, Optional
from .base import RestAPIControlledDevice


class MixerController(RestAPIControlledDevice):
    """
    配料设备控制器
    基于配料设备API文档实现所有功能
    """
    
    def __init__(self, device_id: str = "01", api_base_url: str = "http://127.0.0.1:4669"):
        super().__init__("restapi_mixer_" + device_id, device_id, api_base_url)
        self.current_task_id = None
        self.current_task_status = None
        self.task_info_cache = {}

    def connect(self):
        """连接配料设备（检测API是否可达）"""
        try:
            # 尝试获取任务信息来检测连接
            response = requests.get(f"{self.api_base_url}/api/GetTaskInfo", timeout=5)
            # 即使返回错误，只要能够通信就认为连接成功
            self.is_connected = True
            self.message = "配料设备连接成功"
            return True
        except requests.exceptions.RequestException as e:
            # 如果API不存在健康检查端点，尝试简单的GET请求
            try:
                # 尝试调用GetTaskInfo接口
                response = requests.post(
                    f"{self.api_base_url}/api/GetTaskInfo",
                    json={},
                    timeout=5
                )
                self.is_connected = True
                self.message = "配料设备连接成功"
                return True
            except:
                self.is_connected = False
                self.message = f"配料设备连接失败: {str(e)}"
                return False

    def disconnect(self):
        """断开配料设备连接"""
        self.is_connected = False
        self.message = "配料设备已断开连接"

    def get_task_info(self, task_id: Optional[int] = None) -> Dict[str, Any]:
        """
        获取单个任务详情（GetTaskInfo）
        :param task_id: 任务id，若不传，则返回第一个任务
        :return: 任务信息字典
        """
        if not self.is_connected:
            return {"status": "error", "message": "设备未连接"}

        try:
            payload = {}
            if task_id is not None:
                payload["task_id"] = task_id

            response = requests.post(
                f"{self.api_base_url}/api/GetTaskInfo",
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            # 缓存任务信息
            if "fid" in data or "task_id" in data:
                tid = data.get("fid") or data.get("task_id")
                if tid:
                    self.task_info_cache[tid] = data
                    self.current_task_id = tid
                    self.current_task_status = data.get("status")
            
            self.message = f"获取任务信息成功: task_id={task_id}"
            self.result = {"status": "success", "data": data}
            return data
        except requests.exceptions.RequestException as e:
            self.message = f"获取任务信息失败: {str(e)}"
            self.result = {"status": "error", "message": str(e)}
            return {"status": "error", "message": str(e)}

    def add_task(self, task_name: str, layout_list: List[Dict[str, Any]], 
                  task_id: int = 0, task_template_id_list: Optional[List[int]] = None,
                  is_audit_log: bool = False, is_copy: bool = False) -> Dict[str, Any]:
        """
        创建任务（AddTask）
        :param task_name: 任务名称
        :param layout_list: 任务单元列表
        :param task_id: 任务id，如果是新增任务，task_id填0
        :param task_template_id_list: 任务模板id列表，有填表示是通过模板配置的实验
        :param is_audit_log: 是否审计
        :param is_copy: 是否从其他任务复制
        :return: 创建结果
        """
        if not self.is_connected:
            return {"status": "error", "message": "设备未连接"}

        try:
            payload = {
                "task_id": task_id,
                "task_name": task_name,
                "layout_list": layout_list
            }
            
            if task_template_id_list is not None:
                payload["task_template_id_list"] = task_template_id_list
            if is_audit_log:
                payload["is_audit_log"] = is_audit_log
            if is_copy:
                payload["is_copy"] = is_copy

            response = requests.post(
                f"{self.api_base_url}/api/AddTask",
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            # 更新当前任务信息
            if "task_id" in data and data["task_id"]:
                self.current_task_id = data["task_id"]
                # 获取新创建的任务详情
                self.get_task_info(self.current_task_id)
            
            self.message = f"创建任务成功: task_id={data.get('task_id')}, task_name={task_name}"
            self.result = {"status": "success", "data": data}
            return data
        except requests.exceptions.RequestException as e:
            self.message = f"创建任务失败: {str(e)}"
            self.result = {"status": "error", "message": str(e)}
            return {"status": "error", "message": str(e)}

    def start_task(self, task_id: int, skip_curr_taskunit: int = 1,
                   run_by_single_tube: int = 0, quick_cap: int = 1,
                   use_tip_type: str = "") -> Dict[str, Any]:
        """
        启动任务（StartTask）
        :param task_id: 任务id
        :param skip_curr_taskunit: 跳过当前任务单元的方式
            0 原地恢复
            1 重跑当前操作，暂停或者操作异常时有效
            2 跳过当前操作，暂停或者操作异常时有效
            3 重跑当前任务单元
            4 跳过当前任务单元
        :param run_by_single_tube: 是否按单管顺序执行，1表示是
        :param quick_cap: 是否批量开关盖，0表示批量，1表示单个
        :param use_tip_type: 使用的tip类型
        :return: 启动结果
        """
        if not self.is_connected:
            return {"status": "error", "message": "设备未连接"}

        try:
            payload = {
                "task_id": task_id,
                "skip_curr_taskunit": skip_curr_taskunit,
                "run_by_single_tube": run_by_single_tube,
                "quick_cap": quick_cap
            }
            
            if use_tip_type:
                payload["use_tip_type"] = use_tip_type

            response = requests.post(
                f"{self.api_base_url}/api/StartTask",
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            # 更新当前任务状态
            self.current_task_id = task_id
            if "code" in data and data["code"] == 200:
                self.current_task_status = "running"
            
            self.message = f"启动任务成功: task_id={task_id}"
            self.result = {"status": "success", "data": data}
            return data
        except requests.exceptions.RequestException as e:
            self.message = f"启动任务失败: {str(e)}"
            self.result = {"status": "error", "message": str(e)}
            return {"status": "error", "message": str(e)}

    def stop_task(self, task_id: int) -> Dict[str, Any]:
        """
        暂停任务（StopTask）
        :param task_id: 任务id
        :return: 暂停结果
        """
        if not self.is_connected:
            return {"status": "error", "message": "设备未连接"}

        try:
            payload = {"task_id": task_id}

            response = requests.post(
                f"{self.api_base_url}/api/StopTask",
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            # 更新当前任务状态
            if task_id == self.current_task_id:
                if "code" in data and data["code"] == 200:
                    self.current_task_status = "paused"
            
            self.message = f"暂停任务成功: task_id={task_id}"
            self.result = {"status": "success", "data": data}
            return data
        except requests.exceptions.RequestException as e:
            self.message = f"暂停任务失败: {str(e)}"
            self.result = {"status": "error", "message": str(e)}
            return {"status": "error", "message": str(e)}

    def cancel_task(self, task_id: int) -> Dict[str, Any]:
        """
        取消任务（CancelTask）
        :param task_id: 任务id
        :return: 取消结果
        """
        if not self.is_connected:
            return {"status": "error", "message": "设备未连接"}

        try:
            payload = {"task_id": task_id}

            response = requests.post(
                f"{self.api_base_url}/api/CancelTask",
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            # 更新当前任务状态
            if task_id == self.current_task_id:
                if "code" in data and data["code"] == 200:
                    self.current_task_status = "cancelled"
                    self.current_task_id = None
            
            self.message = f"取消任务成功: task_id={task_id}"
            self.result = {"status": "success", "data": data}
            return data
        except requests.exceptions.RequestException as e:
            self.message = f"取消任务失败: {str(e)}"
            self.result = {"status": "error", "message": str(e)}
            return {"status": "error", "message": str(e)}

    def start(self):
        """启动设备（启动当前任务）"""
        if self.current_task_id:
            return self.start_task(self.current_task_id)
        else:
            self.message = "没有当前任务，无法启动"
            self.result = {"status": "error", "message": "没有当前任务"}
            return self.result

    def stop(self):
        """停止设备（暂停当前任务）"""
        if self.current_task_id:
            return self.stop_task(self.current_task_id)
        else:
            self.message = "没有当前任务，无法暂停"
            self.result = {"status": "error", "message": "没有当前任务"}
            return self.result

    def get_status(self) -> dict:
        """获取设备状态"""
        status_info = {
            "name": self.device_name,
            "connected": self.is_connected,
            "current_task_id": self.current_task_id,
            "current_task_status": self.current_task_status
        }
        
        # 如果有当前任务，获取详细信息
        if self.current_task_id:
            try:
                task_info = self.get_task_info(self.current_task_id)
                if "status" not in task_info.get("status", {}):
                    status_info["task_info"] = task_info
            except:
                pass
        
        return status_info

    def get_result(self) -> dict:
        """获取设备结果"""
        return self.result if self.result else {
            "status": "idle",
            "message": "无操作结果"
        }

    def get_message(self) -> str:
        """获取设备消息"""
        return self.message if self.message else "配料设备就绪"


# 创建全局实例（保持向后兼容）
mixer_controller = MixerController()
