from pydantic import BaseModel, Field
from typing import Optional, List, Any, Dict

class GetTokenRequest(BaseModel):
    username: str
    password: str

class GetTokenResponse(BaseModel):
    access_token: str
    token_type: str

class CustomConfig(BaseModel):
    """配料自定义单位配置"""
    unit: str
    unitOptions: List[str] = ["mg", "g"]

# 工艺JSON配置模型
class ProcessJson(BaseModel):
    """布局项的工艺参数配置"""
    resource_type: str
    substance: str  # 物质名称（如氯化亚铜，"Sb"/"Bi"）
    chemical_id: int  # 化学品ID
    SSSI: str  # 化学物质登记号（如"2-00-25-9"）
    add_weight: float = 0.0  # 添加重量
    offset: float = 0.0 # 偏移量
    custom: CustomConfig  # 嵌套的自定义单位配置

# 布局列表项模型
class LayoutListItem(BaseModel):
    """布局列表中的单个配置项"""
    layout_code: str
    src_layout_code: str
    resource_type: str
    tray_QR_code: str
    status: int
    QR_code: str
    unit_type: str  # 单元类型（如exp_add_powder表示添加粉末实验）
    unit_column: int  # 单元列号
    unit_row: int  # 单元行号
    unit_id: str  # 单元唯一标识
    process_json: ProcessJson  # 嵌套的工艺参数

# 任务设置模型
class TaskSetup(BaseModel):
    """任务基础设置"""
    subtype: Optional[Any] = None  # 子类型（JSON中为null，用Optional+Any兼容任意类型）
    powder_100_30: bool  # 100-30目粉末标识
    powder_30_100: bool  # 30-100目粉末标识
    added_slots: str  # 新增槽位

# 主任务模型（继承BaseModel）
class AddTaskRequest(BaseModel):
    """配料设备任务主模型"""
    task_setup: TaskSetup  # 嵌套的任务设置
    task_id: int    # 任务ID
    task_name: str  # 任务名称
    type: int       # 任务类型
    is_audit_log: int  # 是否记录审计日志（1=是，0=否）
    layout_list: List[LayoutListItem]  # 布局列表（多个布局项）
    added_slots: str = ""
    task_template_id_list: List[Any] = []  # 模板ID列表（空数组）

class AddTaskResponse(BaseModel):
    code: int
    msg: str
    result: Optional[Any]
    data: Optional[Any]
    task_id: int
    substance_shortage_list: Dict[str, Any] = {}

class GetTaskInfoRequest(BaseModel):
    task_id: int

class GetTaskInfoResponse(BaseModel):
    task_id: int
    task_name: str
    unit_save_json: str
    status: int
    creator: str
    task_begin_time: Optional[Any]
    task_end_time: Optional[Any]
    created_at: int
    updated_at: int
    is_audit_log: int
    task_template_id_list: List[Any] = []  # 模板ID列表（空数组）
    task_setup: TaskSetup
    unit_list: List[LayoutListItem]

class BatchStartTaskRequest(BaseModel):
    task_ids: List[int]

class OpTaskRequest(BaseModel):
    task_id: int
    skip_curr_taskunit: int = 0
    run_by_single_tube: int = 0
    quick_cap: int = 1
    use_tip_type: str = ""
    pack_policy: Optional[Any] = None