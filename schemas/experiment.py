"""
实验总流程状态与请求/响应模型
供 AI Agent 或前端查询进度、执行确认与恢复
"""
from enum import Enum
from typing import Optional, Any, Dict
from pydantic import BaseModel, Field


class ExperimentPhase(str, Enum):
    """实验总流程阶段（与可中断/恢复节点对应）"""
    IDLE = "idle"
    MIXING = "mixing"                          # 配料中
    WAITING_SEAL_CONFIRM = "waiting_seal_confirm"   # 等待熔封完成确认
    WAITING_THERMAL_LOAD = "waiting_thermal_load"   # 等待人工将样品放入加热炉后确认
    THERMAL_RUNNING = "thermal_running"        # 热处理（加热炉+离心机）执行中
    WAITING_XRD_READY = "waiting_xrd_ready"    # 等待人工将样品放入XRD试验台后确认
    XRD_RUNNING = "xrd_running"               # XRD测试执行中
    COMPLETED = "completed"
    ERROR = "error"


# 阶段说明（供 Agent 理解当前状态与下一步动作）
PHASE_LABELS: Dict[str, str] = {
    ExperimentPhase.IDLE: "空闲，可启动实验",
    ExperimentPhase.MIXING: "配料进行中",
    ExperimentPhase.WAITING_SEAL_CONFIRM: "等待熔封完成：请完成熔封后调用 POST /api/experiment/flux/confirm_seal",
    ExperimentPhase.WAITING_THERMAL_LOAD: "等待上料：请将样品放入加热炉后调用 POST /api/experiment/flux/confirm_thermal_load",
    ExperimentPhase.THERMAL_RUNNING: "热处理进行中（加热炉与离心机）",
    ExperimentPhase.WAITING_XRD_READY: "等待XRD上样：请将样品放入XRD试验台后调用 POST /api/experiment/flux/confirm_xrd_ready",
    ExperimentPhase.XRD_RUNNING: "XRD测试进行中",
    ExperimentPhase.COMPLETED: "实验已完成",
    ExperimentPhase.ERROR: "实验异常结束",
}


class XRDResultData(BaseModel):
    """实验完成时 XRD 返回的最新数据（2theta 与 intensity）"""
    sample_id: Optional[str] = Field(default=None, description="样品ID")
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
    error_message: Optional[str] = Field(default=None, description="若 phase=error 时的错误信息")
    task_name: Optional[str] = Field(default=None, description="配料任务名称（如有）")
    result: Optional[XRDResultData] = Field(default=None, description="实验完成时的XRD结果（2theta、intensity），仅 phase=completed 时有值")


class ThermalParamsRequest(BaseModel):
    """热处理启动参数（在确认“样品已放入加热炉”时可选传入）"""
    oven_id: int = Field(default=1, description="炉子ID")
    qty: int = Field(default=1, description="数量")
    curve_name: Optional[str] = Field(default=None, description="已保存的曲线名称，不传则尝试使用默认曲线")
