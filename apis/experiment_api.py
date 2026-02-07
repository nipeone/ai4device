"""
实验总流程 API：支持分阶段暂停/恢复，便于人工操作与 AI Agent 调度。

流程节点：
  配料 -> [等待熔封确认] -> [等待加热炉上料确认] -> 热处理 -> [等待XRD上样确认] -> XRD测试 -> 完成

Agent 可通过 GET /api/experiment/status 获取 phase、step_info、pending_action，
在对应阶段调用 confirm 接口恢复流程。
"""
import threading
import time
import uuid
from typing import Optional, Any

from fastapi import APIRouter, File, UploadFile, HTTPException
from logger import sys_logger as logger

from flows.thermal_flow import thermal_flow_mgr
from flows.mix_flow import mix_flow_mgr
from flows.xrd_flow import xrd_flow_mgr
from services.mixer import mixer_service
from services.oven import oven_service
from schemas.oven import CurvePoint
from schemas.experiment import (
    ExperimentPhase,
    ExperimentStatusResponse,
    PHASE_LABELS,
    ThermalParamsRequest,
)

router = APIRouter(prefix="/api/experiment", tags=["实验"])

# ---------------------------------------------------------------------------
# 实验状态与同步（单例：同一时间只允许一个实验在跑）
# ---------------------------------------------------------------------------
CONFIRM_TIMEOUT = 300  # 各阶段等待确认超时（秒）

_seal_confirm = threading.Event()
_seal_confirm.set()
_thermal_load_confirm = threading.Event()
_thermal_load_confirm.set()
_xrd_ready_confirm = threading.Event()
_xrd_ready_confirm.set()

_state_lock = threading.RLock()
_experiment_id: Optional[str] = None
_phase = ExperimentPhase.IDLE
_step_info = ""
_task_name: Optional[str] = None
_error_message: Optional[str] = None
_thermal_params: Optional[dict] = None  # 由 confirm_thermal_load 写入 {oven_id, qty, curve_name}
_runner_thread: Optional[threading.Thread] = None


def _set_phase(phase: ExperimentPhase, step_info: str = "", error_message: Optional[str] = None):
    global _phase, _step_info, _error_message
    with _state_lock:
        _phase = phase
        _step_info = step_info or _step_info
        _error_message = error_message


def _get_step_info_from_flows() -> str:
    """从当前活跃子流程取步骤信息"""
    if _phase == ExperimentPhase.MIXING and mix_flow_mgr.running:
        return getattr(mix_flow_mgr, "current_step_info", "") or "配料中"
    if _phase == ExperimentPhase.THERMAL_RUNNING and thermal_flow_mgr.running:
        return getattr(thermal_flow_mgr, "current_step_info", "") or "热处理中"
    if _phase == ExperimentPhase.XRD_RUNNING and xrd_flow_mgr.running:
        return getattr(xrd_flow_mgr, "current_step_info", "") or "XRD测试中"
    return _step_info


def _resolve_thermal_curve_points() -> list:
    """根据 _thermal_params 解析曲线点，供 thermal_flow_mgr.run 使用"""
    params = _thermal_params or {}
    curve_name = params.get("curve_name")
    points = []
    if curve_name:
        points = oven_service.get_oven_curve_by_name(curve_name)
    if not points:
        curve_list = oven_service.get_oven_curve_list()
        if curve_list:
            points = oven_service.get_oven_curve_by_name(curve_list[0].curve_name)
    if not points:
        # 最小默认：避免 thermal run 因空曲线报错不明确
        points = [
            CurvePoint(temperature=100.0, time=60.0),
            CurvePoint(temperature=-121.0, time=0.0),
        ]
    return points


def _run_experiment(mixer_model: Any):
    """在后台线程中执行：配料 -> 熔封确认 -> 热处理 -> XRD确认 -> XRD测试"""
    global _phase, _experiment_id, _runner_thread
    try:
        # ---------- 1. 配料 ----------
        _set_phase(ExperimentPhase.MIXING, "配料流程启动")
        logger.log("实验流程：开始配料", "INFO")
        mix_result = mix_flow_mgr.run(mixer_model)
        if not mix_result.get("status"):
            _set_phase(ExperimentPhase.ERROR, error_message=mix_result.get("message", "配料失败"))
            return
        _set_phase(ExperimentPhase.WAITING_SEAL_CONFIRM, "配料已完成，等待熔封确认")
        logger.log("等待熔封完成，请调用 POST /api/experiment/flux/confirm_seal", "WARN")

        _seal_confirm.clear()
        if not _seal_confirm.wait(timeout=CONFIRM_TIMEOUT):
            _set_phase(ExperimentPhase.ERROR, error_message="等待熔封确认超时")
            return
        logger.log("熔封已确认", "INFO")

        # ---------- 2. 等待加热炉上料确认 ----------
        _set_phase(ExperimentPhase.WAITING_THERMAL_LOAD, "请将样品放入加热炉后调用 confirm_thermal_load")
        _thermal_load_confirm.clear()
        if not _thermal_load_confirm.wait(timeout=CONFIRM_TIMEOUT):
            _set_phase(ExperimentPhase.ERROR, error_message="等待加热炉上料确认超时")
            return
        logger.log("加热炉上料已确认，开始热处理", "INFO")

        # ---------- 3. 热处理 ----------
        params = _thermal_params or {}
        oven_id = int(params.get("oven_id", 1))
        qty = int(params.get("qty", 1))
        curve_points = _resolve_thermal_curve_points()
        _set_phase(ExperimentPhase.THERMAL_RUNNING, "热处理执行中")
        thermal_result = thermal_flow_mgr.run(oven_id, qty, curve_points)
        if not thermal_result.get("status"):
            _set_phase(ExperimentPhase.ERROR, error_message=thermal_result.get("message", "热处理失败"))
            return
        _set_phase(ExperimentPhase.WAITING_XRD_READY, "热处理已完成，等待XRD上样")
        logger.log("请将样品放入XRD试验台后调用 POST /api/experiment/flux/confirm_xrd_ready", "WARN")

        _xrd_ready_confirm.clear()
        if not _xrd_ready_confirm.wait(timeout=CONFIRM_TIMEOUT):
            _set_phase(ExperimentPhase.ERROR, error_message="等待XRD上样确认超时")
            return
        logger.log("XRD上样已确认，开始XRD测试", "INFO")

        # ---------- 4. XRD 测试 ----------
        _set_phase(ExperimentPhase.XRD_RUNNING, "XRD测试执行中")
        xrd_result = xrd_flow_mgr.run(single=True, sample_id="XY000", start_theta=5.0, end_theta=120.0, increment=0.01, exp_time=0.1)
        if not (isinstance(xrd_result, dict) and xrd_result.get("status")):
            _set_phase(ExperimentPhase.ERROR, error_message=str(xrd_result) if not isinstance(xrd_result, dict) else xrd_result.get("message", "XRD测试失败"))
            return
        _set_phase(ExperimentPhase.COMPLETED, "实验流程已全部完成")
        logger.log("实验总流程完成", "SUCCESS")
    except Exception as e:
        logger.log(f"实验流程异常: {e}", "ERROR")
        _set_phase(ExperimentPhase.ERROR, error_message=str(e))
    finally:
        with _state_lock:
            _runner_thread = None


# ---------------------------------------------------------------------------
# API：启动、状态、各阶段确认
# ---------------------------------------------------------------------------

@router.post("/flux", tags=["实验"])
async def start_experiment(file: UploadFile = File(...)):
    """
    上传 Excel 启动实验总流程（非阻塞）。
    流程会在后台执行，并在熔封/上料/XRD上样等节点暂停，等待确认接口被调用后继续。
    返回 202 与 experiment_id，可通过 GET /api/experiment/status 查询进度。
    """
    if not file.filename or not file.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="只支持上传 Excel 文件(.xlsx, .xls)")

    global _experiment_id, _phase, _task_name, _runner_thread, _thermal_params
    with _state_lock:
        if _phase not in (ExperimentPhase.IDLE, ExperimentPhase.COMPLETED, ExperimentPhase.ERROR):
            raise HTTPException(
                status_code=409,
                detail=f"当前已有实验在运行或等待确认，阶段: {_phase.value}。请先查询 GET /api/experiment/status 并完成确认或等待结束。",
            )
        contents = await file.read()
        mixer_model = await mixer_service.parse_mixer_tasks_from_excel(contents)
        _task_name = getattr(mixer_model, "task_name", None)
        _experiment_id = str(uuid.uuid4())
        _phase = ExperimentPhase.IDLE
        _thermal_params = None
        _error_message = None

    logger.log(f"实验启动，任务名称: {_task_name}，experiment_id: {_experiment_id}", "INFO")
    _runner_thread = threading.Thread(target=_run_experiment, args=(mixer_model,), daemon=True)
    _runner_thread.start()
    # 稍等一步，让线程把 phase 设为 MIXING
    time.sleep(0.2)

    return {
        "status": "started",
        "message": "实验已启动，可通过 GET /api/experiment/status 查询进度",
        "experiment_id": _experiment_id,
        "phase": _phase.value,
        "phase_label": PHASE_LABELS.get(_phase, _phase.value),
    }


@router.get("/status", response_model=ExperimentStatusResponse, tags=["实验"])
def get_experiment_status():
    """
    查询当前实验进度（供 AI Agent 或前端轮询）。
    返回阶段、是否暂停、建议的下一步操作与子流程步骤描述。
    """
    with _state_lock:
        phase = _phase
        step_info = _get_step_info_from_flows()
        experiment_id = _experiment_id or "none"
        task_name = _task_name
        error_message = _error_message

    is_paused = phase in (
        ExperimentPhase.WAITING_SEAL_CONFIRM,
        ExperimentPhase.WAITING_THERMAL_LOAD,
        ExperimentPhase.WAITING_XRD_READY,
    )
    pending_action = PHASE_LABELS.get(phase, phase.value) if is_paused else ""

    sub_flow = None
    if phase == ExperimentPhase.MIXING:
        sub_flow = "mix"
    elif phase == ExperimentPhase.THERMAL_RUNNING:
        sub_flow = "thermal"
    elif phase == ExperimentPhase.XRD_RUNNING:
        sub_flow = "xrd"

    return ExperimentStatusResponse(
        experiment_id=experiment_id,
        phase=phase,
        phase_label=PHASE_LABELS.get(phase, phase.value),
        is_paused=is_paused,
        pending_action=pending_action,
        step_info=step_info,
        sub_flow=sub_flow,
        error_message=error_message,
        task_name=task_name,
    )


@router.post("/flux/confirm_seal", tags=["实验"])
def confirm_flux_seal():
    """人工或 Agent 确认熔封已完成，流程将继续到「等待加热炉上料」阶段。"""
    _seal_confirm.set()
    logger.log("熔封确认已接收", "INFO")
    return {"msg": "熔封确认已接收，流程继续"}


@router.post("/flux/confirm_thermal_load", tags=["实验"])
def confirm_thermal_load(body: Optional[ThermalParamsRequest] = None):
    """
    确认样品已放入加热炉，并可选传入热处理参数（炉号、数量、曲线名）。
    调用后流程将开始热处理（炉子+离心机）。
    """
    global _thermal_params
    if body:
        _thermal_params = {
            "oven_id": body.oven_id,
            "qty": body.qty,
            "curve_name": body.curve_name,
        }
    _thermal_load_confirm.set()
    logger.log("加热炉上料确认已接收", "INFO")
    return {"msg": "上料确认已接收，开始热处理"}


@router.post("/flux/confirm_xrd_ready", tags=["实验"])
def confirm_xrd_ready():
    """确认样品已放入 XRD 试验台，流程将开始 XRD 测试。"""
    _xrd_ready_confirm.set()
    logger.log("XRD上样确认已接收", "INFO")
    return {"msg": "XRD上样确认已接收，开始XRD测试"}
