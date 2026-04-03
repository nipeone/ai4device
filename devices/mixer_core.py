import requests
import time
from typing import Dict, Any, List, Optional
from .base import RestAPIControlledDevice, DeviceStatus
import config
from utils import retry_on_failure
from schemas.mixer import (
    GetTaskInfoRequest,
    GetTaskInfoResponse,
    GetResourceInfoRequest,
    GetResourceInfoResponse,
    GetChemicalsRequest,
    GetChemicalsResponse,
    AddChemicalRequest,
    AddChemicalResponse,
    AddTaskRequest,
    AddTaskResponse,
    BatchStartTaskRequest,
    OpTaskRequest,
    GetTokenRequest,
    GetTokenResponse,
    GetSetupResponse,
    BatchCheckTaskRequest,
    BatchCheckTaskResponse
)
from logger import sys_logger as logger

class MixerController(RestAPIControlledDevice):
    """
    RestAPI控制的配料设备
    基于配料设备API文档实现所有功能
    """
    
    def __init__(self, device_id: str = "01", api_base_url: str = None, username: str = None, password: str = None):
        # 从环境变量获取配置，如果没有提供参数则使用默认值
        api_base_url = api_base_url or config.MIXER_API_BASE_URL
        username = username or config.MIXER_USERNAME
        password = password or config.MIXER_PASSWORD
        super().__init__("restapi_mixer_" + device_id, device_id, api_base_url)
        self.current_task_id = None
        self.current_task_status = None # 由get_task_info获取
        self.task_info_cache = {}
        self.username = username
        self.password = password
        self.api_headers = {
            "Content-Type": "application/json",
            "Authorization": ""
        }

    def connect(self):
        """连接配料设备（检测API是否可达），获取Token"""
        try:
            payload = GetTokenRequest(
                username=self.username,
                password=self.password
            )
            # 尝试获取任务信息来检测连接
            response = requests.post(f"{self.api_base_url}/api/Token", json=payload.model_dump(), timeout=5)
            if response.status_code == 200:
                data = GetTokenResponse(**response.json())
                self.api_token = data.access_token
                self.api_token_type = data.token_type
                self.api_headers["Authorization"] = f"{self.api_token_type} {self.api_token}"
                self.is_connected = True
                self.message = "配料设备连接成功"
                self.status = DeviceStatus.CONNECTED
                return True
            else:
                self.is_connected = False
                self.api_token = None
                self.api_token_type = None
                self.api_headers = {}
                self.message = f"获取Token失败，状态码：{response.status_code}"
                self.status = DeviceStatus.DISCONNECTED
                return False
        except requests.exceptions.RequestException as e:
            self.is_connected = False
            self.message = f"获取Token失败: {str(e)}"
            self.status = DeviceStatus.DISCONNECTED
            return False

    def disconnect(self):
        """断开配料设备连接"""
        self.is_connected = False
        self.current_task_id = None
        self.current_task_status = None
        self.task_info_cache = {}
        self.api_token = None
        self.api_token_type = None
        self.api_headers = {}
        self.message = "配料设备已断开连接"
        self.status = DeviceStatus.DISCONNECTED

    def get_setup(self) -> Dict[str, Any]:
        """
        获取设置信息（GetSetUp）
        :return: 设置信息
        """
        if not self.is_connected:
            return {"status": "error", "message": "设备未连接"}
        try:
            response = requests.post(f"{self.api_base_url}/api/GetSetUp", headers=self.api_headers)
            response.raise_for_status()
            data = GetSetupResponse(**response.json())
            return {"status": "success", "data": data}
        except requests.exceptions.RequestException as e:
            self.message = f"获取设置信息失败: {str(e)}"
            self.result = {"status": "error", "message": self.message}
            return self.result

    def get_task_info(self, task_id: Optional[int] = None) -> Dict[str, Any]:
        """
        获取单个任务详情（GetTaskInfo）
        :param task_id: 任务id，若不传，则返回第一个任务
        :return: 任务信息字典
        """
        if not self.is_connected:
            return {"status": "error", "message": "设备未连接"}

        try:
            if task_id is None:
                return {"status": "error", "message": "任务id不能为空"}
            payload = GetTaskInfoRequest(task_id=task_id)

            response = requests.post(
                f"{self.api_base_url}/api/GetTaskInfo",
                json=payload.model_dump(),
                timeout=10,
                headers=self.api_headers
            )
            response.raise_for_status()
            data = GetTaskInfoResponse(**response.json())
            
            # 缓存任务信息
            tid = data.task_id
            self.task_info_cache[tid] = data
            self.current_task_id = tid
            self.current_task_status = data.status
            
            self.message = f"获取任务信息成功: task_id={task_id}"
            self.result = {"status": "success", "data": data}
            return self.result
        except requests.exceptions.RequestException as e:
            self.message = f"获取任务信息失败: {str(e)}"
            self.result = {"status": "error", "message": self.message}
            return self.result

    def get_resource_info(self) -> Dict[str, Any]:
        """
        获取资源信息（GetResourceInfo）
        :return: 资源信息
        """
        if not self.is_connected:
            return {"status": "error", "message": "设备未连接"}

        try:
            payload = GetResourceInfoRequest(roll=0)

            response = requests.post(
                f"{self.api_base_url}/api/GetResourceInfo",
                json=payload.model_dump(),
                timeout=10,
                headers=self.api_headers
            )
            response.raise_for_status()
            data = GetResourceInfoResponse(**response.json())
            
            self.result = {"status": "success", "data": data}
            return self.result
        except requests.exceptions.RequestException as e:
            self.message = f"获取任务信息失败: {str(e)}"
            self.result = {"status": "error", "message": self.message}
            return self.result

    def get_chemicals(self, sort: str = "desc", offset: int = 0, limit: int = 20, query_key: Optional[str] = None) -> Dict[str, Any]:
        """
        获取化学品信息（GetChemicals）
        :return: 化学品信息
        """
        if not self.is_connected:
            return {"status": "error", "message": "设备未连接"}
        try:
            payload = GetChemicalsRequest(sort=sort, offset=offset, limit=limit, query_key=query_key)
            response = requests.get(
                f"{self.api_base_url}/api/v1/knowledge/getChemicalList",
                params=payload.model_dump(),
                timeout=10,
                headers=self.api_headers
            )
            response.raise_for_status()
            data = GetChemicalsResponse(**response.json())
            return {"status": "success", "data": data}
        except requests.exceptions.RequestException as e:
            self.message = f"获取化学品信息失败: {str(e)}"
            self.result = {"status": "error", "message": self.message}
            return self.result

    def add_chemical(self, chemical_name: str) -> Dict[str, Any]:
        """
        添加化学品（AddChemical）
        :param chemical_name: 化学品名称
        :return: 添加结果
        """
        if not self.is_connected:
            return {"status": "error", "message": "设备未连接"}
        try:
            payload = AddChemicalRequest(name=chemical_name)
            response = requests.post(
                f"{self.api_base_url}/api/v1/knowledge/addChemical",
                json=payload.model_dump(),
                timeout=10,
                headers=self.api_headers
            )
            response.raise_for_status()
            data = AddChemicalResponse(**response.json())
            return {"status": "success", "data": data}
        except requests.exceptions.RequestException as e:
            self.message = f"添加化学品信息失败: {str(e)}"
            self.result = {"status": "error", "message": self.message}
            return self.result

    @retry_on_failure(max_retries=3, delay=1.0, status_key="status", success_value="success")
    def add_task(self, add_task_request: AddTaskRequest) -> Dict[str, Any]:
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
            payload = add_task_request.model_dump()
            response = requests.post(
                f"{self.api_base_url}/api/AddTask",
                json=payload,
                timeout=30,
                headers=self.api_headers
            )
            response.raise_for_status()
            print("-"*20)
            print(response.json())
            if response.json().get("code") != 200:
                return {"status": "error", "message": f"创建任务失败: {response.json().get('msg')}"}
            data = AddTaskResponse(**response.json())
            
            # 更新当前任务信息
            if data.task_id:
                self.current_task_id = data.task_id
                # 获取新创建的任务详情
                self.get_task_info(self.current_task_id)
            
            self.message = f"创建任务成功: task_id = {data.task_id}"
            self.result = {"status": "success", "data": data}
            return self.result
        except requests.exceptions.RequestException as e:
            self.message = f"创建任务失败: {str(e)}"
            self.result = {"status": "error", "message": self.message}
            return self.result

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
                timeout=30,
                headers=self.api_headers
            )
            response.raise_for_status()
            data = response.json()
            
            # 更新当前任务状态
            self.current_task_id = task_id
            if "code" in data and data["code"] == 200:
                self.status = DeviceStatus.RUNNING
            
            self.message = f"启动任务成功: task_id={task_id}"
            self.result = {"status": "success", "data": data}
            return data
        except requests.exceptions.RequestException as e:
            self.message = f"启动任务失败: {str(e)}"
            self.result = {"status": "error", "message": str(e)}
            return {"status": "error", "message": str(e)}

    def batch_check_task(self, task_ids: List[int]) -> Dict[str, Any]:
        """
        批量检查任务（BatchCheckTask）
        :param task_ids: 任务id列表
        :return: 批量检查结果
        """
        if not self.is_connected:
            return {"status": "error", "message": "设备未连接"}
        
        try:
            payload = BatchCheckTaskRequest(task_ids=task_ids)
            response = requests.post(
                f"{self.api_base_url}/api/BatchCheckTask",
                json=payload.model_dump(),
                timeout=30,
                headers=self.api_headers
            )
            response.raise_for_status()
            data = BatchCheckTaskResponse(**response.json())
            return {"status": "success", "data": data}
        except requests.exceptions.RequestException as e:
            self.message = f"批量检查任务失败: {str(e)}"
            self.result = {"status": "error", "message": str(e)}
            return {"status": "error", "message": str(e)}

    @retry_on_failure(max_retries=3, delay=1.0, status_key="status", success_value="success")
    def batch_start_task(self, task_ids: List[int]) -> Dict[str, Any]:
        """
        批量启动任务（BatchStartTask）
        :param task_ids: 任务id列表
        :return: 批量启动结果
        """
        if not self.is_connected:
            return {"status": "error", "message": "设备未连接"}
        
        try:
            payload = {"task_ids": task_ids}
            response = requests.post(
                f"{self.api_base_url}/api/BatchStartTask",
                json=payload,
                timeout=30,
                headers=self.api_headers
            )
            response.raise_for_status()
            data = response.json()
            return {"status": "success", "data": data}
        except requests.exceptions.RequestException as e:
            self.message = f"批量启动任务失败: {str(e)}"
            self.result = {"status": "error", "message": str(e)}
            return {"status": "error", "message": str(e)}

    @retry_on_failure(max_retries=3, delay=1.0, status_key="status", success_value="success")
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
                timeout=30,
                headers=self.api_headers
            )
            response.raise_for_status()
            data = response.json()
            
            # 更新当前任务状态
            if task_id == self.current_task_id:
                if "code" in data and data["code"] == 200:
                    self.status = DeviceStatus.PAUSED
            
            self.message = f"暂停任务成功: task_id={task_id}"
            self.result = {"status": "success", "data": data}
            return data
        except requests.exceptions.RequestException as e:
            self.message = f"暂停任务失败: {str(e)}"
            self.result = {"status": "error", "message": str(e)}
            return {"status": "error", "message": str(e)}

    @retry_on_failure(max_retries=3, delay=1.0, status_key="status", success_value="success")
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
                timeout=30,
                headers=self.api_headers
            )
            response.raise_for_status()
            data = response.json()
            
            # 更新当前任务状态
            if task_id == self.current_task_id:
                if "code" in data and data["code"] == 200:
                    self.status = DeviceStatus.CANCELLED
                    self.current_task_id = None
                    self.current_task_status = None
            
            self.message = f"取消任务成功: task_id={task_id}"
            self.result = {"status": "success", "data": data}
            return self.result
        except requests.exceptions.RequestException as e:
            self.message = f"取消任务失败: {str(e)}"
            self.result = {"status": "error", "message": self.message}
            return self.result

    @retry_on_failure(max_retries=3, delay=1.0, status_key="status", success_value="success")
    def del_task(self, task_id: int) -> Dict[str, Any]:
        """
        删除任务（DelTask）
        :param task_id: 任务id
        :return: 删除结果
        """
        if not self.is_connected:
            return {"status": "error", "message": "设备未连接"}
        try:
            payload = {"task_id": task_id}
            response = requests.post(
                f"{self.api_base_url}/api/DeleteTask",
                json=payload,
                timeout=30,
                headers=self.api_headers
            )
            response.raise_for_status()
            data = response.json()

            if task_id == self.current_task_id:
                if "code" in data and data["code"] == 200:
                    self.status = DeviceStatus.UNKNOWN
                    self.current_task_id = None
                    self.current_task_status = None
            self.message = f"删除任务成功: task_id={task_id}"
            self.result = {"status": "success", "data": data}
            return self.result 
        except requests.exceptions.RequestException as e:
            self.message = f"删除任务失败: {str(e)}"
            self.result = {"status": "error", "message": str(e)}
            return self.result

    @retry_on_failure(max_retries=3, delay=1.0, status_key="status", success_value="success")
    def start(self):
        """启动设备（启动当前任务）"""
        if self.current_task_id:
            return self.start_task(self.current_task_id)
        else:
            self.message = "没有当前任务，无法启动"
            self.result = {"status": "error", "message": "没有当前任务"}
            return self.result

    @retry_on_failure(max_retries=3, delay=1.0, status_key="status", success_value="success")
    def stop(self):
        """停止设备（暂停当前任务）"""
        if self.current_task_id:
            return self.stop_task(self.current_task_id)
        else:
            self.message = "没有当前任务，无法暂停"
            self.result = {"status": "error", "message": "没有当前任务"}
            return self.result

    def get_running_status(self) -> dict:
        """获取设备运行状态"""
        if not self.is_connected:
            return {"status": "error", "message": "设备未连接"}

        if not self.current_task_id:
            return {"status": "error", "message": "当前任务为空"}
        return self.get_task_info(self.current_task_id)

    def get_status(self) -> dict:
        """获取设备状态"""
        return self.status

    def get_result(self) -> dict:
        """获取设备结果"""
        if self.current_task_id:
            self.result = self.get_task_info(self.current_task_id)
        return self.result if self.result else {
            "status": "idle",
            "message": "无操作结果"
        }

    def get_message(self) -> str:
        """获取设备消息"""
        return self.message if self.message else "配料设备就绪"


# 创建全局实例（保持向后兼容）
mixer_controller = MixerController()
