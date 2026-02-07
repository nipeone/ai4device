"""
实验总流程 API：委托给 flows.experiment_flow 中的状态机编排器，无全局状态。

启动实验：
- POST /flux：入参为大模型规范输出（JSON，见 schemas/llm_output.py），
  从中提取原料 -> AddTaskRequest、温度程序 -> List[CurvePoint]，并可选炉号/数量。
- POST /flux/from_excel：兼容旧版，上传 Excel 解析为配料任务（无温度曲线，曲线由 confirm_thermal_load 或默认提供）。

流程节点：
  配料 -> [等待熔封确认] -> [等待加热炉上料确认] -> 热处理 -> [等待XRD上样确认] -> XRD测试 -> 完成
"""
from typing import Optional

from fastapi import APIRouter, File, UploadFile, HTTPException

from flows.experiment_flow import experiment_orchestrator
from services.mixer import mixer_service
from services.experiment_input import (
    llm_output_to_add_task_request,
    llm_output_to_curve_points,
)
from schemas.experiment import ExperimentStatusResponse, ThermalParamsRequest
from schemas.llm_output import StartExperimentRequest

from logger import sys_logger as logger

router = APIRouter(prefix="/api/experiment", tags=["实验"])


@router.post("/flux", tags=["实验"])
async def start_experiment(body: StartExperimentRequest):
    """
    使用大模型规范输出启动实验（JSON 入参，与 data/llm_output.json 结构一致）。

    从 body 中提取：
    - 工艺配方.原料 -> 配料任务 AddTaskRequest（每个原料对应一个 LayoutListItem）
    - 温度程序 -> 加热炉曲线 List[CurvePoint]（升温/保温/降温段，时间单位为小时）

    流程在后台执行，在熔封/上料/XRD上样等节点暂停，需调用对应 confirm 接口恢复。
    返回 experiment_id 与当前 phase，可通过 GET /api/experiment/status 查询进度。
    """
    # 配料数据
    add_task = llm_output_to_add_task_request(body)
    # 工艺曲线数据
    curve_points = llm_output_to_curve_points(body)
    logger.info(f"add_task: {add_task}")
    logger.info(f"curve_points: {curve_points}")
    thermal_params = {
        "oven_id": 3,
        "qty": 1,
        "curve_points": [p.model_dump() for p in curve_points],
    }
    try:
        result = experiment_orchestrator.start(add_task, thermal_params=thermal_params)
        return result
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/flux/from_excel", tags=["实验"])
async def start_experiment_from_excel(file: UploadFile = File(...)):
    """
    兼容旧版：上传 Excel 启动实验，仅解析配料任务；温度曲线由 confirm_thermal_load 传入曲线名或使用默认。
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
    当 phase=completed 时，result 字段会包含 XRD 最新数据：theta2（2θ 角度列表）、intensity（强度列表）、sample_id、timestamp。
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
    若启动时已通过 LLM 输出传入曲线，此处可不传曲线名，仅确认上料即可。
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


@router.post("/stop", tags=["实验"])
def stop_experiment():
    """
    请求停止当前实验。若实验正在运行或处于某一「等待确认」阶段，将下发停止请求；
    后台线程会在下一轮检查时退出，phase 变为 error，error_message 为「用户停止实验」。
    返回已是否成功发出停止请求（无实验在跑时返回 false）。
    """
    ok = experiment_orchestrator.stop()
    return {"stopped": ok, "msg": "已请求停止实验" if ok else "当前无实验在运行"}
