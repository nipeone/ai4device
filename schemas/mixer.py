from pydantic import BaseModel, Field
from typing import Optional, List, Any, Dict
from enum import Enum

class TaskStatus(Enum):
    UNSTARTED = 0  # 未开始
    RUNNING = 1 # 运行中
    COMPLETED = 2 # 已完成
    PAUSED = 3  # 暂停
    STOPPED = 5  # 已终止
    PAUSING = 6  # 暂停中
    STOPPING = 7  # 终止中
    WAITING = 9  # 等待中
    HOLDING = 10  # 阻塞

class GetTokenRequest(BaseModel):
    username: str
    password: str

class GetTokenResponse(BaseModel):
    access_token: str
    token_type: str

class CustomConfig(BaseModel):
    """配料自定义单位配置"""
    unit: str = "mg"
    unitOptions: List[str] = ["mg", "g"]

# 工艺JSON配置模型
class ProcessJson(BaseModel):
    """布局项的工艺参数配置"""
    resource_type: str = "CC10R10C"
    substance: str = "Sb" # 物质名称（如氯化亚铜，"Sb"/"Bi"）
    chemical_id: Optional[int] = None # 化学品ID
    SSSI: Optional[str] = None # 化学物质登记号（如"2-00-25-9"）
    add_weight: float = 0.0  # 添加重量
    offset: Optional[float] = 0.3 # 偏移量
    custom: CustomConfig = Field(default_factory=CustomConfig) # 嵌套的自定义单位配置

# 布局列表项模型
class LayoutListItem(BaseModel):
    """布局列表中的单个配置项"""
    layout_code: str = ""
    src_layout_code: str = ""
    resource_type: str = "CC10R10C"
    tray_QR_code: str = ""
    status: int = 0
    QR_code: str = ""
    unit_type: str = "exp_add_powder" # 单元类型（如exp_add_powder表示添加粉末实验）
    unit_column: int = 0  # 单元列号
    unit_row: int = 0  # 单元行号
    unit_id: str = ""  # 单元唯一标识
    process_json: ProcessJson = Field(default_factory=ProcessJson)  # 嵌套的工艺参数

# 任务设置模型
class TaskSetup(BaseModel):
    """任务基础设置"""
    subtype: Optional[Any] = None  # 子类型（JSON中为null，用Optional+Any兼容任意类型）
    powder_100_30: bool = False  # 100-30目粉末标识
    powder_30_100: bool = False  # 30-100目粉末标识
    added_slots: str = ""  # 新增槽位

class GetSetupResponse(BaseModel):
    required_tray_code: bool = False
    required_medium_code: bool = False
    method_audit_log: bool = True
    task_audit_log: bool = True
    addition_timeout: int = 360
    accuracy: float = 0.5
    substance_shortage_nums: int = 5
    created_at: str
    updated_at: str
    weight_node: int = 45
    accuracy_30mL: float = 0.3
    accuracy_100mL: float = 0.3
    small_substance_shortage_nums: int = 100
    big_substance_shortage_nums: int = 500

# 主任务模型（继承BaseModel）
class AddTaskRequest(BaseModel):
    """配料设备任务主模型"""
    task_setup: TaskSetup = Field(default_factory=TaskSetup) # 嵌套的任务设置
    task_id: int = Field(default=0, description="任务ID, 如果是新增任务，task_id填0")
    task_name: str = Field(..., description="任务名称")
    type: int = Field(default=2, description="任务类型, 2:配料任务")
    is_audit_log: int = Field(default=1, description="是否记录审计日志, 1:是, 0:否")
    layout_list: List[LayoutListItem] = Field(..., description="任务单元列表")
    added_slots: str = Field(default="", description="新增槽位, 如果为空表示不新增槽位")
    task_template_id_list: List[Any] = Field(default=[], description="模板ID列表, 如果有填表示是通过模板配置的实验")

class AddTaskResponse(BaseModel):
    code: int = 200
    msg: str = "success"
    result: Optional[Any] = None
    data: Optional[Any] = None
    task_id: int
    substance_shortage_list: Dict[str, Any] = {}

class GetTaskInfoRequest(BaseModel):
    task_id: int
    roll: int = 0

class GetResourceInfoRequest(BaseModel):
    roll: int

class GetChemicalsRequest(BaseModel):
    sort: str = "desc"
    offset: int = 0
    limit: int = 20
    query_key: Optional[str] = None

class ChemicalListItem(BaseModel):
    fid: int
    name: str
    sssi: str
    cas: Optional[str] = None
    element: Optional[str] = None
    state: Optional[str] = None
    concentration_str: Optional[str] = None
    chemical_properties: Optional[str] = None
    edit_operation: Optional[str] = None
    delete_operation: Optional[str] = None
    preparation_method: Optional[str] = None

class ChemicalData(BaseModel):
    chemical_sums: int = 0
    chemical_list: List[ChemicalListItem] = []

class GetChemicalsResponse(BaseModel):
    code: int
    msg: str
    result: Optional[ChemicalData]
    data: Optional[ChemicalData]

class AddChemicalRequest(BaseModel):
    name: str
    cas: Optional[str] = None
    state: Optional[str] = None
    element: Optional[str] = None
    concentration_str: Optional[str] = None
    density_str: Optional[str] = None
    pipetting_compensation: Optional[Dict[str, Any]] = None
    chemical_properties: Optional[str] = None
    molecular_formula: Optional[str] = None
    molecular_weight: Optional[float] = None
    preparation_method: Optional[str] = None

class AddChemicalResponseResult(BaseModel):
    chemical_id: int

class AddChemicalResponse(BaseModel):
    code: int
    msg: str
    result: Optional[AddChemicalResponseResult]

class ResourceListItem(BaseModel):
    fid: int = Field(default=0, description="资源ID")
    layout_code: str = Field(default="IPF1-1:-1", description="资源位置编码")
    working_code: str = Field(default="", description="操作时资源位置编码")
    resource_type: str = Field(..., description="资源类型")
    substance: str = Field(default="", description="物质名称")
    chemical_id: Optional[int] = Field(default=None, description="化学品ID")
    material_batch_number: Optional[Any] = Field(default=None, description="物料批次号")
    initial_volume: float = Field(default=0.0, description="初始体积")
    initial_weight: float = Field(default=0.0, description="初始重量")
    cur_volume: float = Field(default=0.0, description="当前体积")
    cur_weight: float = Field(default=0.0, description="当前重量")
    available_volume: float = Field(default=0.0, description="可用体积")
    available_weight: float = Field(default=0.0, description="可用重量")
    tray_QR_code: str = Field(default="", description="托盘二维码")
    QR_code: str = Field(default="", description="试管二维码")
    unit: str = Field(default="", description="单位")
    source_layout_code: str = Field(default="IPF1-1:-1", description="原始资源位置编码")
    with_magneton: bool = Field(default=False, description="是否带有磁性")
    usage_times: int = Field(default=0, description="使用次数")
    status: int = Field(default=0, description="状态，0:资源在位置上，1:资源待移走，2:资源待放入，3:任务占用中，4:待出料")
    color: Optional[Any] = Field(default=None, description="颜色")
    created_at: int = Field(default=0, description="创建时间")
    updated_at: int = Field(default=0, description="更新时间")
    with_cap: bool = Field(default=False, description="是否带有盖子")
    used: bool = Field(default=False, description="是否被使用")

class GetResourceInfoResponse(BaseModel):
    code: int
    msg: str
    result: Optional[Any]
    data: Optional[Any]
    resource_list: Optional[List[ResourceListItem]]

class GetTaskInfoResponse(BaseModel):
    task_id: int
    task_name: str
    unit_save_json: str
    status: int
    creator: str
    task_begin_time: Optional[Any]
    task_end_time: Optional[Any]
    created_at: float
    updated_at: float
    is_audit_log: int = 1
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

class IngredientItem(BaseModel):
    substance: str
    weight: float
    unit: str = "mg"

class SchemeItem(BaseModel):
    scheme_name: str
    ingredients: List[IngredientItem]

class MixerSummaryData(BaseModel):
    task_id: int
    task_name: str
    status: int
    creator: str
    task_begin_time: Optional[Any]
    task_end_time: Optional[Any]
    created_at: int
    updated_at: int
    scheme_list: List[SchemeItem]

class MixerSummaryItem(BaseModel):
    status: str
    data: MixerSummaryData

class MixerSummary(BaseModel):
    mixer: MixerSummaryItem

class MixerSummaryResponse(BaseModel):
    status: bool
    summary: MixerSummary

class BatchStartTaskRequest(BaseModel):
    task_ids: List[int]

class BatchCheckTaskRequest(BatchStartTaskRequest):
    pass

class BatchCheckTaskResponse(BaseModel):
    code: int
    msg: Optional[str] = None
    prompt_msg: Optional[Dict[str, Any]] = None