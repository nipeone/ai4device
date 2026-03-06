"""
实验总流程状态与请求/响应模型
供 AI Agent 或前端查询进度、执行确认与恢复
"""
from enum import Enum
from typing import Optional, Any, Dict, List
from pydantic import BaseModel, Field, field_validator


class ExperimentPhase(str, Enum):
    """实验总流程阶段（与可中断/恢复节点对应）"""
    IDLE = "idle"                                   # 空闲，可启动实验
    MIXING = "mixing"                               # 配料中
    WAITING_SEAL_CONFIRM = "waiting_seal_confirm"   # 等待熔封完成确认
    LOADING = "loading"                             # 上料进行中
    WAITING_THERMAL_LOAD = "waiting_thermal_load"   # 等待加热炉上料确认
    THERMAL_RUNNING = "thermal_running"             # 热处理（加热炉+离心机）执行中
    WAITING_XRD_READY = "waiting_xrd_ready"         # 等待人工将样品放入XRD试验台后确认
    XRD_RUNNING = "xrd_running"                     # XRD测试执行中
    COMPLETED = "completed"                         # 实验已完成
    ERROR = "error"                                 # 实验异常结束


# 阶段说明（供 Agent 理解当前状态与下一步动作）
PHASE_LABELS: Dict[str, str] = {
    ExperimentPhase.IDLE: "空闲，可启动实验",
    ExperimentPhase.MIXING: "配料进行中",
    ExperimentPhase.WAITING_SEAL_CONFIRM: "等待熔封完成：请完成熔封后调用 POST /api/experiment/flux/confirm_seal",
    ExperimentPhase.LOADING: "上料进行中",
    ExperimentPhase.WAITING_THERMAL_LOAD: "等待上料完成：请将样品放入加热炉后调用 POST /api/experiment/flux/confirm_thermal_load",
    ExperimentPhase.THERMAL_RUNNING: "热处理进行中（加热炉与离心机）",
    ExperimentPhase.WAITING_XRD_READY: "等待XRD上样：请将样品放入XRD试验台后调用 POST /api/experiment/flux/confirm_xrd_ready",
    ExperimentPhase.XRD_RUNNING: "XRD测试进行中",
    ExperimentPhase.COMPLETED: "实验已完成",
    ExperimentPhase.ERROR: "实验异常结束",
}


class XRDResultData(BaseModel):
    """实验完成时 XRD 返回的数据（2theta 与 intensity），可带配方关联供大模型按配方总结"""
    experiment_id: Optional[str] = Field(default=None, description="实验ID，便于与 experiment_id/scheme_id/sample_id 关联查询")
    sample_id: Optional[str] = Field(default=None, description="样品/试管ID（XRD 设备侧）")
    scheme_id: Optional[str] = Field(default=None, description="关联的方案ID，如 方案_A，供大模型按配方总结")
    scheme_index: Optional[int] = Field(default=None, description="关联的方案索引（0 起）")
    scheme_type: Optional[str] = Field(default=None, description="关联的方案类型")
    theta2: Optional[Any] = Field(default=None, description="2θ 角度列表（度）")
    intensity: Optional[Any] = Field(default=None, description="强度列表")
    timestamp: Optional[Any] = Field(default=None, description="时间戳")


class ExperimentStatusResponse(BaseModel):
    """实验进度状态（Agent 轮询或单次查询）"""
    experiment_id: str = Field(..., description="实验ID")
    phase: ExperimentPhase = Field(..., description="当前阶段")
    phase_label: str = Field(..., description="阶段说明，供Agent理解")
    is_paused: bool = Field(..., description="是否处于暂停/等待人工节点")
    pending_action: str = Field(default="", description="建议的下一步操作说明")
    step_info: str = Field(default="", description="当前子流程步骤描述（如热处理/XRD内部步骤）")
    sub_flow: Optional[str] = Field(default=None, description="当前活跃子流程: mix | thermal | xrd")
    sub_flow_summaries: Optional[Dict[str, Any]] = Field(
        default=None,
        description="当前阶段对应子流程的输出摘要：mixing 时仅含 mix，thermal_running 时仅含 thermal，xrd_running/completed/error 时仅含 xrd；等待确认阶段为空",
    )
    error_message: Optional[str] = Field(default=None, description="若 phase=error 时的错误信息")
    task_name: Optional[str] = Field(default=None, description="配料任务名称（如有）")
    scheme_ids: Optional[List[str]] = Field(
        default=None,
        description="本实验包含的方案ID列表（如 方案_A、方案_B），与推荐实验方案列表顺序一致",
    )
    scheme_manifest: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="本实验的试管/方案清单，每项含 scheme_index、scheme_id、scheme_type，只读",
    )
    result: Optional[List[XRDResultData]] = Field(
        default=None,
        description="实验完成时的XRD结果（单试管或多试管），仅 phase=completed 时有值，每项含 experiment_id/scheme_id/sample_id 便于关联；单试管时可为空",
    )


class StartExperimentResponse(BaseModel):
    """启动实验接口统一返回结构（成功与冲突时字段一致）"""
    status: str = Field(..., description="started | error")
    message: str = Field(..., description="说明信息")
    experiment_id: str = Field(..., description="当前实验ID（冲突时为正在运行的实验ID）")
    phase: str = Field(..., description="当前阶段枚举值")
    phase_label: str = Field(..., description="阶段说明")


class OvenAssignment(BaseModel):
    """单炉分配：指定某炉放入某方案对应的试管及数量，曲线由 scheme_index 从 LLM 方案列表解析"""
    oven_id: int = Field(..., description="炉子ID")
    scheme_index: int = Field(..., description="方案索引（0 起），对应推荐实验方案列表顺序")
    qty: int = Field(..., description="放入该炉的试管数量")


class ThermalParamsRequest(BaseModel):
    """热处理启动参数（在确认“样品已放入加热炉”时可选传入；不传则沿用启动时的 oven_id/qty）"""
    oven_id: Optional[int] = Field(default=None, description="炉子ID，单炉时使用；多炉时用 oven_assignments")
    qty: Optional[int] = Field(default=None, description="试管数量，单炉时使用")
    curve_name: Optional[str] = Field(default=None, description="已保存的曲线名称，不传则尝试使用默认曲线")
    curve_points: Optional[List[Any]] = Field(default=None, description="曲线点列表（单炉时），多炉时由 oven_assignments 按 scheme_index 解析")
    oven_assignments: Optional[List[OvenAssignment]] = Field(
        default=None,
        description="多炉分配：每项指定 oven_id、scheme_index、qty；每种炉只能设一条曲线，不同方案进不同炉",
    )

class SampleAssignment(BaseModel):
    """样品数量分配：指定某方案放入某炉的试管数量"""
    scheme_index: int = Field(..., description="方案索引（0 起），对应推荐实验方案列表顺序")
    qty: int = Field(1, description="样品制备的数量")

class XRDParamsRequest(BaseModel):
    """XRD上样参数（在确认“样品已放入XRD试验台”时可选传入；不传则沿用默认值）"""
    start_theta: Optional[float] = Field(default=5.0, description="起始角度")
    end_theta: Optional[float] = Field(default=120.0, description="结束角度")
    increment: Optional[float] = Field(default=0.01, description="步长")
    exp_time: Optional[float] = Field(default=0.1, description="曝光时间")
    sample_assignments: Optional[List[SampleAssignment]] = Field(default=None, description="各个方案样品制备数量，默认为1")

    @field_validator('start_theta')
    def validate_start_theta(cls, v):
        if v <= 5.0:
            raise ValueError("起始角度需要>5.0")
        return v
    @field_validator('end_theta')
    def validate_end_theta(cls, v):
        if v > 120.0 or v < 5.5:
            raise ValueError("结束角度需要>=5.5且<=120.0")
        return v
    @field_validator('increment')
    def validate_increment(cls, v):
        if v < 0.005:
            raise ValueError("角度增量需要>=0.005")
        return v
    @field_validator('exp_time')
    def validate_exp_time(cls, v):
        if v < 0.1 or v > 5.0:
            raise ValueError("曝光时间需要>=0.1s且<=5.0s")
        return v