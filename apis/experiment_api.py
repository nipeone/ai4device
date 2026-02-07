"""
实验总流程 API：委托给 flows.experiment_flow 中的状态机编排器，无全局状态。

流程节点：
  配料 -> [等待熔封确认] -> [等待加热炉上料确认] -> 热处理 -> [等待XRD上样确认] -> XRD测试 -> 完成

Agent 可通过 GET /api/experiment/status 获取 phase、step_info、pending_action，
在对应阶段调用 confirm 接口恢复流程。
"""
from typing import Optional

from fastapi import APIRouter, File, UploadFile, HTTPException

from flows.experiment_flow import experiment_orchestrator
from services.mixer import mixer_service
from schemas.experiment import ExperimentStatusResponse, ThermalParamsRequest

router = APIRouter(prefix="/api/experiment", tags=["实验"])


@router.post("/flux", tags=["实验"])
async def start_experiment(file: UploadFile = File(...)):
    """
    上传 Excel 启动实验总流程（非阻塞）。
    流程在后台由编排器执行，在熔封/上料/XRD上样等节点暂停，等待确认接口被调用后继续。
    返回 experiment_id 与当前 phase，可通过 GET /api/experiment/status 查询进度。
    """
    if not file.filename or not file.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="只支持上传 Excel 文件(.xlsx, .xls)")

    contents = await file.read()
    mixer_model = await mixer_service.parse_mixer_tasks_from_excel(contents)

    try:
        result = experiment_orchestrator.start(mixer_model)
        return result
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/status", response_model=ExperimentStatusResponse, tags=["实验"])
def get_experiment_status():
    """
    查询当前实验进度（供 AI Agent 或前端轮询）。
    返回阶段、是否暂停、建议的下一步操作与子流程步骤描述。
    """
    return experiment_orchestrator.get_status()


@router.post("/flux/confirm_seal", tags=["实验"])
def confirm_flux_seal():
    """人工或 Agent 确认熔封已完成，流程将继续到「等待加热炉上料」阶段。"""
    experiment_orchestrator.confirm_seal()
    return {"msg": "熔封确认已接收，流程继续"}


@router.post("/flux/confirm_thermal_load", tags=["实验"])
def confirm_thermal_load(body: Optional[ThermalParamsRequest] = None):
    """
    确认样品已放入加热炉，并可选传入热处理参数（炉号、数量、曲线名）。
    调用后流程将开始热处理（炉子+离心机）。
    """
    if body:
        experiment_orchestrator.confirm_thermal_load(
            oven_id=body.oven_id,
            qty=body.qty,
            curve_name=body.curve_name,
        )
    else:
        experiment_orchestrator.confirm_thermal_load()
    return {"msg": "上料确认已接收，开始热处理"}


@router.post("/flux/confirm_xrd_ready", tags=["实验"])
def confirm_xrd_ready():
    """确认样品已放入 XRD 试验台，流程将开始 XRD 测试。"""
    experiment_orchestrator.confirm_xrd_ready()
    return {"msg": "XRD上样确认已接收，开始XRD测试"}
