"""
实验总流程编排器：显式状态机 + 子流程调度，无全局状态。

职责：
- 维护当前实验阶段（phase）与上下文（experiment_id、step_info、thermal_params 等）
- 在后台线程中按阶段执行：配料 -> 熔封确认 -> 热处理 -> XRD确认 -> XRD测试
- 提供 start / get_status / confirm_seal / confirm_thermal_load / confirm_xrd_ready 供 API 层调用

说明：未引入 Celery。若后续需要任务持久化、多 Worker 或分布式队列，可在此层将
_run_experiment 拆为多个 Celery task，由本状态机驱动 task 链。
"""
import json
import os
import queue
import random
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, Any, Dict, List, Tuple

from logger import sys_logger as logger
from schemas.oven import CurvePoint
from schemas.experiment import (
    ExperimentPhase,
    ExperimentStatusResponse,
    NextAction,
    NextActionParam,
    PHASE_LABELS,
    XRDResultData
)

from flows.mix_flow import mix_flow_mgr
from flows.thermal_flow import thermal_flow_mgr
from flows.xrd_flow import xrd_flow_mgr
from services.oven import oven_service
from services.experiment_input import (
    llm_output_to_add_task_request,
    llm_output_to_curve_points_for_scheme_index,
    RecommendExperimentRecipes
)
from schemas.mixer import AddTaskRequest, MixerSummaryResponse
from services import experiment_persistence
try:
    import config
    _MOCK_DEVICES = getattr(config, "MOCK_DEVICES", False)
    _MOCK_STEP_DELAY = getattr(config, "MOCK_STEP_DELAY", 1.0)
except Exception:
    _MOCK_DEVICES = False
    _MOCK_STEP_DELAY = 1.0

CONFIRM_TIMEOUT = 60 * 60 * 24  # 各阶段等待确认超时（秒），24小时
# Mock 时每个子流程（配料/热处理/XRD）模拟执行时长范围（秒），便于感知流程是否都执行过
MOCK_STEP_DURATION_MIN = 20
MOCK_STEP_DURATION_MAX = 40


def _merge_layout_by_scheme(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    将按行展开的 layout（unit_column, unit_row, scheme_name, substance, weight）按列合并为方案列表。
    返回 [ {"scheme_name": str, "ingredients": [{"substance": str, "weight": float}, ...]}, ... ]，按 unit_column 升序。
    """
    by_col: Dict[int, List[Dict[str, Any]]] = {}
    for r in rows:
        col = int(r.get("unit_column", 0))
        if col not in by_col:
            by_col[col] = []
        by_col[col].append(r)
    scheme_list = []
    for col in sorted(by_col.keys()):
        group = sorted(by_col[col], key=lambda x: x.get("unit_row", 0))
        scheme_name = (group[0].get("scheme_name") or f"scheme{col}").strip() if group else f"scheme{col}"
        ingredients = [{"substance": r.get("substance", ""), "weight": float(r.get("weight", r.get("add_weight", 0)) or 0), "unit": r.get("unit", "mg")} for r in group]
        scheme_list.append({"scheme_name": scheme_name, "ingredients": ingredients})
    return scheme_list


def _rows_from_mixer_data(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    从真实配料设备返回的 data（可能含 layout_list、unit_list 等）提取可合并的行。
    返回 [ {unit_column, unit_row, 方案名称, 元素, 毫克}, ... ]，无法解析时返回 []。
    """
    rows: List[Dict[str, Any]] = []
    raw = data.get("layout_list") or data.get("unit_list") or []
    if not isinstance(raw, list):
        return []
    for i, item in enumerate(raw):
        if isinstance(item, dict):
            col = int(item.get("unit_column", item.get("unit_column", 0)))
            row = int(item.get("unit_row", item.get("unit_row", 0)))
            pj = item.get("process_json") or item
            substance = pj.get("substance") or ""
            add_weight = pj.get("add_weight") or 0
            rows.append({"unit_column": col, "unit_row": row, "substance": substance, "add_weight": add_weight})
        else:
            # Pydantic 模型转 dict 再取
            col = getattr(item, "unit_column", 0)
            row = getattr(item, "unit_row", 0)
            pj = getattr(item, "process_json", item)
            substance = getattr(pj, "substance", "") if pj else ""
            add_weight = getattr(pj, "add_weight", 0) if pj else 0
            rows.append({"unit_column": col, "unit_row": row, "substance": substance, "add_weight": add_weight})
    return rows


def _load_llm_output_json() -> Optional[Dict[str, Any]]:
    """加载 data/llm_output.json 用于 Mock 时生成与当前方案一致的 fake 数据；失败返回 None。"""
    for path in [
        "data/llm_output.json",
        os.path.join(os.path.dirname(__file__), "..", "data", "llm_output.json"),
    ]:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            continue
    return None


def _temperature_curve_from_llm_program(program: Dict[str, Any]) -> List[Dict[str, float]]:
    """从 LLM 温度程序（dict）生成时间-温度曲线数组 [{time, temperature}, ...]，时间单位小时，温度单位℃。"""
    if not program:
        return [{"time": 0.0, "temperature": 25.0}, {"time": 1.0, "temperature": 100.0}]
    t = 0.0
    curve = [{"time": 0.0, "temperature": 25.0}]
    # 升温到次高温
    ramp1 = float(program.get("升温到次高温时间_h") or 0)
    T1 = float(program.get("次高温段温度_摄氏") or 0)
    if ramp1 > 0:
        t += ramp1
        curve.append({"time": round(t, 2), "temperature": T1})
    hold1 = float(program.get("次高温段保温时间_h") or 0)
    if hold1 > 0:
        t += hold1
        curve.append({"time": round(t, 2), "temperature": T1})
    # 升温到最高温
    ramp2 = float(program.get("升温到最高温时间_h") or 0)
    T_high = float(program.get("最高温段保温温度_摄氏") or 0)
    if ramp2 > 0:
        t += ramp2
        curve.append({"time": round(t, 2), "temperature": T_high})
    hold2 = float(program.get("最高温段保温时间_h") or 0)
    if hold2 > 0:
        t += hold2
        curve.append({"time": round(t, 2), "temperature": T_high})
    # 主降温
    cool_h = float(program.get("降温时间_主降温_h") or 0)
    T_low = float(program.get("低温段保温温度_摄氏") or 0)
    if cool_h > 0:
        t += cool_h
        curve.append({"time": round(t, 2), "temperature": T_low})
    hold3 = float(program.get("低温段保温时间_h") or 0)
    if hold3 > 0:
        t += hold3
        curve.append({"time": round(t, 2), "temperature": T_low})
    return curve


def _fake_mix_summary(
    step_info: str = "",
    task_name: Optional[str] = None,
    mixer_data: Optional[AddTaskRequest] = None,
) -> Dict[str, Any]:
    """
    Mock 下配料子流程 get_summary 的假数据。从 AddTaskRequest 生成时按列合并为方案列表，
    每组试验方案一项：方案名称 + 配料（元素、毫克）列表。
    """
    task_name_out = task_name or "Mock配料任务"
    方案列表: List[Dict[str, Any]] = []

    if mixer_data:
        try:
            add_task = mixer_data
            task_name_out = add_task.task_name
            rows: List[Dict[str, Any]] = []
            for item in add_task.layout_list:
                unit_column = getattr(item, "unit_column", 0)
                unit_row = getattr(item, "unit_row", 0)
                pj = getattr(item, "process_json", None)
                substance = getattr(pj, "substance", "") if pj else ""
                add_weight_mg = float(getattr(pj, "add_weight", 0) or 0) if pj else 0.0
                weight = round(add_weight_mg, 2)
                rows.append({
                    "unit_column": unit_column,
                    "unit_row": unit_row,
                    "scheme_name": f"方案{unit_column}",
                    "substance": substance,
                    "weight": weight,
                })
            scheme_list = _merge_layout_by_scheme(rows)
        except Exception:
            scheme_list = []

    # 与真实 GetTaskInfoResponse + 方案列表 格式一致，便于前端统一处理
    return MixerSummaryResponse(**{
        "status": True,
        "summary": {
            "mixer": {
                "status": "success",
                "data": {
                    "task_id": 9001,
                    "task_name": task_name_out,
                    "status": 1,
                    "creator": "mock",
                    "task_begin_time": time.time(),
                    "task_end_time": None,
                    "created_at": 0,
                    "updated_at": 0,
                    "scheme_list": scheme_list,
                },
            },
        },
    }).model_dump()


def _fake_thermal_summary(
    step_info: str = "",
    temperature_curve: Optional[List[Dict[str, float]]] = None,
) -> Dict[str, Any]:
    """
    Mock 下热处理子流程 get_summary 的假数据，与 thermal_flow.get_summary() 及各 device.get_running_status() 结构一致。
    可传入 temperature_curve（由 llm_output 温度程序生成），否则使用默认曲线。
    """
    curve = temperature_curve or [
        {"time": 0.0, "temperature": 25.0},
        {"time": 11.5, "temperature": 600.0},
        {"time": 13.5, "temperature": 600.0},
        {"time": 14.5, "temperature": 870.0},
        {"time": 38.5, "temperature": 870.0},
        {"time": 188.5, "temperature": 600.0},
    ]
    return {
        "status": True,
        "summary": {
            "robot": {
                "status": "success",
                "data": {
                    "plc_connected": True,
                    "m_signals": [False, False, False, False, False, True, False],
                    "task_data": {"tid": 1, "st": 1, "qty": 1},
                    "robot": {
                        "home_status": True,
                        "fixture_status": True,
                        "system_status": 2,
                        "robot_status": True,
                        "task_status": 1,
                    },
                },
            },
            "oven": {
                "status": "success",
                "data": [
                    {
                        "设备名称": "炉1",
                        "设备地址": 1,
                        "仪表型号": "858P",
                        "在线状态": "在线",
                        "实际温度": 450.5,
                        "设定温度": 500.0,
                        "状态显示": "阶段2 剩余0.5h",
                        "结束时间": "2025-02-09 15:30",
                        "状态": "开始",
                        "运行曲线": "Mock曲线",
                    },
                ],
            },
            "centrifuge": {
                "status": "success",
                "data": {
                    "actual_rpm": 500,
                    "centrifuge_force": 120,
                    "run_time": 300,
                    "fault_code": 0,
                    "run_state": 2,
                    "door_window": 2,
                    "setted_rpm": 500,
                    "setted_time": 10,
                    "door_lid": 2,
                    "rotor_state": 2,
                    "remain_time": 180,
                },
            },
            "temperature_curve": curve,
        },
    }


def _fake_xrd_summary(step_info: str = "") -> Dict[str, Any]:
    """
    Mock 下 XRD 子流程 get_summary 的假数据，与 xrd_flow.get_summary() 及 xrd_controller.get_running_status() 结构一致。
    真实返回：{"status": True, "summary": {"xrd": status_info}}，status_info 含 name, connected, host, port, status, xray_status, power_status 等。
    """
    return {
        "status": True,
        "summary": {
            "xrd": {
                "name": "XRD衍射仪",
                "connected": True,
                "host": "192.168.1.100",
                "port": 8000,
                "status": "running",
                "xray_status": True,
                "power_status": True,
                "current_voltage": 45.0,
                "current_current": 40.0,
                "untest_station": [],
                "ready_station": ["1"],
            },
        },
    }


class ExperimentOrchestrator:
    """
    实验总流程状态机与编排器。
    状态：IDLE -> MIXING -> WAITING_SEAL_CONFIRM -> ... -> COMPLETED / ERROR
    所有可变状态与事件均封装在实例内，便于测试与后续替换为 Celery 任务链。
    """

    def __init__(self, confirm_timeout: int = CONFIRM_TIMEOUT):
        self._confirm_timeout = confirm_timeout
        self._lock = threading.RLock()

        # 状态（仅通过 _set_phase 与 _run_experiment 更新）
        self._phase = ExperimentPhase.IDLE
        self._experiment_id: Optional[str] = None
        self._step_info = ""
        self._task_name: Optional[str] = None
        self._error_message: Optional[str] = None
        self._thermal_params: Optional[Dict[str, Any]] = None
        self._xrd_params: Optional[Dict[str, Any]] = None
        self._runner_thread: Optional[threading.Thread] = None

        # 各阶段恢复事件
        self._seal_confirm = threading.Event()
        self._seal_confirm.set()
        self._thermal_load_confirm = threading.Event()
        self._thermal_load_confirm.set()
        self._xrd_ready_confirm = threading.Event()
        self._xrd_ready_confirm.set()

        # 用户请求停止（stop() 置 True，start() 清空）
        self._stop_requested = False
        # 实验成功完成时的 XRD 结果：单试管用 _last_result，多试管用 _last_results（每项含 scheme_id 关联配方）
        self._last_results: Optional[list] = None
        # 多炉流水线中当前等待 XRD 上样确认的批次（用于 next_action.body_data），进入 WAITING_XRD_READY 时设置，确认后清空
        self._current_xrd_batch: Optional[Dict[str, Any]] = None
        # 进入 XRD_RUNNING 时设置的当前/刚完成样品（Mock 或 run 返回后 xrd_flow 已清空时，供 get_status 的 xrd_running_sample 使用）
        self._current_xrd_running: Optional[Dict[str, Any]] = None
        # confirm_xrd_ready 时生成并绑定的样品列表，每项 {sample_id, scheme_id, scheme_index}，流程用其执行 XRD 并写结果
        self._pending_xrd_sample_ids: Optional[List[Dict[str, Any]]] = None
        # 报错后可从下一阶段继续：记录恢复阶段，供 confirm_continue_after_error 使用
        self._error_resume_phase: Optional[ExperimentPhase] = None
        # start() 时保存的 mixer_model，恢复流程时需传入 _run_experiment
        self._mixer_model: Optional[Any] = None

    def _set_phase(
        self,
        phase: ExperimentPhase,
        step_info: str = "",
        error_message: Optional[str] = None,
    ) -> None:
        with self._lock:
            self._phase = phase
            if step_info:
                self._step_info = step_info
            if error_message is not None:
                self._error_message = error_message
            if phase in (ExperimentPhase.COMPLETED, ExperimentPhase.ERROR):
                self._current_xrd_running = None
        if self._experiment_id:
            try:
                experiment_persistence.update_experiment_phase(
                    self._experiment_id, phase.value, error_message
                )
            except Exception as e:
                logger.log(f"持久化实验阶段失败: {e}", "WARN")

    def _set_phase_error(
        self,
        error_message: str,
        resume_phase: Optional[ExperimentPhase] = None,
        step_info: str = "",
    ) -> None:
        """设置 ERROR 阶段并记录可恢复的下一阶段（供 confirm_continue_after_error 使用）。"""
        with self._lock:
            self._error_resume_phase = resume_phase
        self._set_phase(ExperimentPhase.ERROR, step_info=step_info or "实验异常结束", error_message=error_message)

    def _get_step_info_from_flows(self) -> str:
        """从当前活跃子流程取步骤信息"""
        if self._phase == ExperimentPhase.MIXING and mix_flow_mgr.running:
            return getattr(mix_flow_mgr, "current_step_info", "") or "配料中"
        if self._phase == ExperimentPhase.LOADING and thermal_flow_mgr.running:
            return getattr(thermal_flow_mgr, "current_step_info", "") or "上料中"
        if self._phase == ExperimentPhase.THERMAL_RUNNING and thermal_flow_mgr.running:
            return getattr(thermal_flow_mgr, "current_step_info", "") or "热处理中"
        if self._phase == ExperimentPhase.XRD_RUNNING and xrd_flow_mgr.running:
            return getattr(xrd_flow_mgr, "current_step_info", "") or "XRD测试中"
        return self._step_info

    def _get_sub_flow_summaries(self) -> Dict[str, Any]:
        """
        获取当前阶段对应的子流程输出摘要，供用户查看。
        仅输出当前阶段所属子流程的 summary：mixing 只输出 mix，thermal 只输出 thermal，xrd 只输出 xrd；
        等待确认等阶段无对应子流程时返回空。
        Mock 与真实设备返回的数据格式一致（如配料均为 summary.mixer.data 含 task_id、task_name、方案列表 等）。
        """
        phase = self._phase
        out: Dict[str, Any] = {}
        step_info = self._get_step_info_from_flows()

        if phase == ExperimentPhase.MIXING:
            try:
                raw_out = mix_flow_mgr.get_summary()
                mixer_wrap = (raw_out.get("summary") or {}).get("mixer") or {}
                if isinstance(mixer_wrap, dict) and "data" in mixer_wrap:
                    inner = mixer_wrap["data"]
                    if hasattr(inner, "model_dump"):
                        inner = inner.model_dump()
                    elif not isinstance(inner, dict):
                        inner = dict(inner) if inner else {}
                    if isinstance(inner, dict):
                        rows = _rows_from_mixer_data(inner)
                        scheme_list = _merge_layout_by_scheme(rows) if rows else []
                        out = MixerSummaryResponse(**{
                            "status": True,
                            "summary": {
                                "mixer": {
                                    "status": mixer_wrap.get("status", "success"),
                                    "data": {
                                        "task_id": inner.get("task_id", 0),
                                        "task_name": inner.get("task_name", ""),
                                        "status": int(inner.get("status", 0)),
                                        "creator": inner.get("creator", ""),
                                        "task_begin_time": inner.get("task_begin_time"),
                                        "task_end_time": inner.get("task_end_time"),
                                        "created_at": int(inner.get("created_at", 0)),
                                        "updated_at": int(inner.get("updated_at", 0)),
                                        "scheme_list": scheme_list,
                                    },
                                },
                            },
                        }).model_dump()
                    else:
                        out = raw_out
                else:
                    out = raw_out
            except Exception as e:
                out = {"status": False, "message": str(e), "summary": {}}
        elif phase == ExperimentPhase.THERMAL_RUNNING:
            try:
                oven_ids = None
                with self._lock:
                    thermal_params = self._thermal_params or {}
                assignments = thermal_params.get("oven_assignments") or []
                if isinstance(assignments, list) and len(assignments) > 0:
                    oven_ids = [int(a.get("oven_id")) for a in assignments if isinstance(a, dict) and a.get("oven_id") is not None]
                if not oven_ids and thermal_params:
                    oven_ids = [int(thermal_params.get("oven_id", 1))]
                out = thermal_flow_mgr.get_summary(oven_ids=oven_ids)
                if out.get("summary") is not None:
                    summary = out["summary"]
                    # 按炉子解析温度曲线：多炉时每个炉子对应 scheme_index 的曲线不同
                    def _points_to_list(pts):
                        return [
                            {
                                "time": getattr(p, "time", p.get("time", 0.0) if isinstance(p, dict) else 0.0),
                                "temperature": getattr(p, "temperature", p.get("temperature", 0.0) if isinstance(p, dict) else 0.0),
                            }
                            for p in pts
                        ]
                    if isinstance(assignments, list) and len(assignments) > 0 and self._raw_req is not None:
                        temperature_curves = {}
                        for a in assignments:
                            if not isinstance(a, dict):
                                continue
                            oven_id = a.get("oven_id")
                            scheme_idx = int(a.get("scheme_index", 0))
                            try:
                                curve_points = llm_output_to_curve_points_for_scheme_index(self._raw_req, scheme_idx)
                            except Exception:
                                curve_points = self._resolve_thermal_curve_points()
                            if curve_points:
                                lst = _points_to_list(curve_points)
                                if oven_id is not None:
                                    temperature_curves[str(int(oven_id))] = lst
                        if temperature_curves:
                            summary["temperature_curves"] = temperature_curves
                    else:
                        curve_points = self._resolve_thermal_curve_points()
                        if curve_points:
                            summary["temperature_curves"] = {str(int(oven_id)): _points_to_list(curve_points) for oven_id in oven_ids}
            except Exception as e:
                out = {"status": False, "message": str(e), "summary": {}}
        elif phase == ExperimentPhase.ERROR:
            with self._lock:
                err = self._error_message
            out = {"status": False, "message": err or "实验异常结束", "summary": {}}
        elif phase in (ExperimentPhase.XRD_RUNNING, ExperimentPhase.COMPLETED):
            try:
                out = xrd_flow_mgr.get_summary()
            except Exception as e:
                out = {"status": False, "message": str(e), "summary": {}}
        # IDLE / WAITING_SEAL_CONFIRM / WAITING_THERMAL_LOAD / WAITING_XRD_READY 无当前子流程，返回空
        return out

    def _resolve_thermal_curve_points(self) -> list:
        """根据当前 thermal_params 解析曲线点：优先 curve_points，其次 curve_name，最后默认"""
        params = self._thermal_params or {}
        # 启动时由 LLM 入参传入的曲线点（List[CurvePoint] 或 list of dict）
        raw_points = params.get("curve_points")
        if raw_points:
            points = []
            for p in raw_points:
                if isinstance(p, CurvePoint):
                    points.append(p)
                elif isinstance(p, dict):
                    points.append(CurvePoint(**p))
                else:
                    points.append(CurvePoint(temperature=float(getattr(p, "temperature", 0)), time=float(getattr(p, "time", 0))))
            if points:
                return points
        curve_name = params.get("curve_name")
        if curve_name:
            points = oven_service.get_oven_curve_by_name(curve_name)
            if points:
                return points
        curve_list = oven_service.get_oven_curve_list()
        if curve_list:
            points = oven_service.get_oven_curve_by_name(curve_list[0].curve_name)
            if points:
                return points
        # 默认曲线：时间单位为小时（与 thermal_flow、llm_output_to_curve_points 一致）
        return [
            CurvePoint(temperature=100.0, time=1.0),
            CurvePoint(temperature=-121.0, time=0.0),
        ]

    def _wait_confirm_or_stop(self, event: threading.Event, timeout: float) -> bool:
        """等待 event 被 set，或超时，或用户调用了 stop()。返回 True 表示确认完成，False 表示超时或已停止。"""
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self._stop_requested:
                return False
            if event.wait(timeout=1.0):
                return True
        return False

    def _mock_sleep_with_stop_check(self, min_sec: int, max_sec: int) -> None:
        """
        Mock 模式下模拟子流程执行时长（秒），期间每秒检查 _stop_requested，便于中途停止。
        """
        duration = random.randint(min_sec, max_sec)
        for _ in range(duration):
            if self._stop_requested:
                return
            time.sleep(1)

    def _run_experiment(self, mixer_model: Any, start_from_phase: Optional[ExperimentPhase] = None) -> None:
        """在后台线程中按状态机执行各阶段（配料 -> 熔封确认 -> 热处理 -> XRD确认 -> XRD测试）。
        start_from_phase 非空时从该阶段开始执行（跳过之前阶段），用于报错后继续流程。"""
        mock = _MOCK_DEVICES
        PHASE_ORDER = [
            ExperimentPhase.MIXING,
            ExperimentPhase.WAITING_SEAL_CONFIRM,
            ExperimentPhase.LOADING,
            ExperimentPhase.WAITING_THERMAL_LOAD,
            ExperimentPhase.THERMAL_RUNNING,
            ExperimentPhase.WAITING_XRD_READY,
            ExperimentPhase.XRD_RUNNING,
        ]

        def _skip(phase: ExperimentPhase) -> bool:
            """为 True 时跳过以该阶段为起点的整块逻辑（因从更晚阶段恢复）。"""
            if start_from_phase is None or phase is None:
                return False
            try:
                return PHASE_ORDER.index(start_from_phase) > PHASE_ORDER.index(phase)
            except ValueError:
                return False

        try:
            # ---------- 1. 配料 -> 熔封确认 -> 上料 ----------
            if not _skip(ExperimentPhase.MIXING):
                if self._stop_requested:
                    self._set_phase(ExperimentPhase.IDLE, error_message="用户停止实验")
                    return
                self._set_phase(ExperimentPhase.MIXING, "配料流程启动" + (" [Mock]" if mock else ""))
                logger.log("实验流程：开始配料" + (" [Mock 设备]" if mock else ""), "INFO")
                if self._stop_requested:
                    self._set_phase(ExperimentPhase.IDLE, error_message="用户停止实验")
                    return
                mix_result = mix_flow_mgr.run(mixer_model)
                if self._stop_requested:
                    self._set_phase(ExperimentPhase.IDLE, error_message="用户停止实验")
                    return
                if not mix_result.get("status"):
                    msg = mix_result.get("message", "配料失败")
                    if msg == "用户停止实验":
                        self._set_phase(ExperimentPhase.IDLE, error_message=msg)
                    else:
                        self._set_phase_error(
                            msg,
                            resume_phase=ExperimentPhase.WAITING_SEAL_CONFIRM,
                        )
                    return
                self._set_phase(ExperimentPhase.WAITING_SEAL_CONFIRM, "配料已完成，等待熔封确认")
                logger.log("等待熔封完成，请调用 POST /api/experiment/flux/confirm_seal", "WARN")
                self._seal_confirm.clear()
                if not self._wait_confirm_or_stop(self._seal_confirm, self._confirm_timeout):
                    if self._stop_requested:
                        self._set_phase(ExperimentPhase.IDLE, error_message="用户停止实验")
                    else:
                        self._set_phase_error("等待熔封确认超时", resume_phase=ExperimentPhase.WAITING_THERMAL_LOAD)
                    return
                logger.log("熔封已确认", "INFO")
                self._set_phase(ExperimentPhase.LOADING, "上料流程启动" + (" [Mock]" if mock else ""))
                time.sleep(MOCK_STEP_DURATION_MIN)

            # ---------- 2. 等待加热炉上料确认 ----------
            if not _skip(ExperimentPhase.WAITING_THERMAL_LOAD):
                if self._stop_requested:
                    self._set_phase(ExperimentPhase.IDLE, error_message="用户停止实验")
                    return
                self._set_phase(ExperimentPhase.WAITING_THERMAL_LOAD, "请将样品放入加热炉后调用 confirm_thermal_load")
                logger.log("等待加热炉上料确认，请调用 POST /api/experiment/flux/confirm_thermal_load", "WARN")
                self._thermal_load_confirm.clear()
                if not self._wait_confirm_or_stop(self._thermal_load_confirm, self._confirm_timeout):
                    if self._stop_requested:
                        self._set_phase(ExperimentPhase.IDLE, error_message="用户停止实验")
                    else:
                        self._set_phase_error("等待加热炉上料确认超时", resume_phase=ExperimentPhase.WAITING_THERMAL_LOAD)
                    return
                logger.log("加热炉上料已确认，开始热处理", "INFO")

            # ---------- 3. 热处理（恢复时 start_from_phase==WAITING_XRD_READY 则跳过整段）----------
            thermal_params = self._thermal_params or {}
            oven_assignments = thermal_params.get("oven_assignments") or []
            use_multi_oven = (
                isinstance(oven_assignments, list)
                and len(oven_assignments) > 0
                and (self._raw_req.recommend_schemes is not None or mock)
            )
            if not _skip(ExperimentPhase.THERMAL_RUNNING):
                if self._stop_requested:
                    self._set_phase(ExperimentPhase.IDLE, error_message="用户停止实验")
                    return
                self._set_phase(ExperimentPhase.THERMAL_RUNNING, "热处理执行中" + (" [Mock]" if mock else ""))
                if use_multi_oven:
                    # 流水线：炉子加热结束即入队，下游单通道（离心/XRD 各一套）按完成顺序依次做「等待XRD上样 → XRD」
                    scheme_manifest = (thermal_params.get("scheme_manifest") or []) if isinstance(thermal_params.get("scheme_manifest"), list) else []
                    if not scheme_manifest:
                        scheme_manifest = [{"scheme_index": 0, "scheme_id": "方案0", "scheme_type": ""}]
                    xrd_params = self._xrd_params or {}
                    batch_queue = queue.Queue()

                    def _run_one_thermal(assign: dict):
                        oven_id = int(assign.get("oven_id", 0))
                        scheme_idx = int(assign.get("scheme_index", 0))
                        qty = int(assign.get("qty", 1))
                        curve_points = llm_output_to_curve_points_for_scheme_index(self._raw_req, scheme_idx)
                        return oven_id, thermal_flow_mgr.run(oven_id, qty, curve_points)

                    def thermal_producer():
                        try:
                            with ThreadPoolExecutor(max_workers=len(oven_assignments)) as executor:
                                futures = {executor.submit(_run_one_thermal, a): a for a in oven_assignments}
                                for future in as_completed(futures):
                                    if self._stop_requested:
                                        thermal_flow_mgr.stop()
                                        batch_queue.put(("fail", "用户停止实验"))
                                        return
                                    try:
                                        oven_id, one = future.result()
                                        assign = futures.get(future, {})
                                        scheme_idx = int(assign.get("scheme_index", 0))
                                        qty = int(assign.get("qty", 1))
                                        if not one.get("status"):
                                            thermal_flow_mgr.stop()
                                            batch_queue.put(("fail", one.get("message", "热处理失败")))
                                            return
                                        scheme = scheme_manifest[scheme_idx] if scheme_idx < len(scheme_manifest) else {}
                                        batch_queue.put(("ok", {"oven_id": oven_id, "scheme_idx": scheme_idx, "qty": qty, "scheme": scheme}))
                                    except Exception as e:
                                        assign = futures.get(future, {})
                                        lid = assign.get("oven_id", "?")
                                        thermal_flow_mgr.stop()
                                        batch_queue.put(("fail", f"炉{lid} 热处理异常: {e}"))
                                        return
                                batch_queue.put(("done", None))
                        except Exception as e:
                            batch_queue.put(("fail", str(e)))

                    prod_thread = threading.Thread(target=thermal_producer, daemon=False)
                    prod_thread.start()
                    with self._lock:
                        self._last_results = []
                    exp_id = self._experiment_id or ""
                    multi_oven_success = True
                    while multi_oven_success:
                        item = batch_queue.get()
                        kind, payload = item[0], item[1]
                        if kind == "fail":
                            self._set_phase_error(payload, resume_phase=ExperimentPhase.WAITING_XRD_READY)
                            multi_oven_success = False
                            break
                        if kind == "done":
                            break
                        batch = payload
                        oven_id, scheme_idx, qty, scheme = batch["oven_id"], batch["scheme_idx"], batch["qty"], batch["scheme"]
                        if self._stop_requested:
                            self._set_phase(ExperimentPhase.IDLE, error_message="用户停止实验")
                            multi_oven_success = False
                            break
                        with self._lock:
                            self._current_xrd_batch = {"oven_id": oven_id, "scheme_index": scheme_idx, "scheme_id": scheme.get("scheme_id"), "qty": qty}
                        self._set_phase(ExperimentPhase.WAITING_XRD_READY, f"请将炉{oven_id}的样品放入XRD试验台后调用 confirm_xrd_ready")
                        logger.log(f"等待炉{oven_id}|{scheme.get("scheme_id")}的样品放入XRD试验台并确认", "WARN")
                        self._xrd_ready_confirm.clear()
                        if not self._wait_confirm_or_stop(self._xrd_ready_confirm, self._confirm_timeout):
                            if self._stop_requested:
                                self._set_phase(ExperimentPhase.IDLE, error_message="用户停止实验")
                            else:
                                self._set_phase_error("等待XRD上样确认超时", resume_phase=ExperimentPhase.WAITING_XRD_READY)
                            multi_oven_success = False
                            break

                        with self._lock:
                            self._current_xrd_batch = None
                            pending = self._pending_xrd_sample_ids or []
                            self._pending_xrd_sample_ids = None
                        batch_sample_ids = [p["sample_id"] for p in pending]
                        if not batch_sample_ids:
                            batch_sample_ids = [f"{scheme.get('scheme_id', '方案')}_{uuid.uuid4().hex[:8]}"]
                        if self._stop_requested:
                            self._set_phase(ExperimentPhase.IDLE, error_message="用户停止实验")
                            multi_oven_success = False
                            break
                        with self._lock:
                            self._current_xrd_running = {
                                "scheme_index": scheme_idx,
                                "scheme_id": scheme.get("scheme_id"),
                                "sample_id": batch_sample_ids[0] if batch_sample_ids else None,
                            }
                        self._set_phase(ExperimentPhase.XRD_RUNNING, f"XRD测试执行中（炉{oven_id}）")
                        # 每批使用当前 confirm_xrd_ready 合并后的 XRD 参数（用户可能每炉传不同参数）
                        cur_xrd = self._xrd_params or {}
                        st = float(cur_xrd.get("start_theta", 5.1))
                        et = float(cur_xrd.get("end_theta", 120.0))
                        inc = float(cur_xrd.get("increment", 0.01))
                        exp = float(cur_xrd.get("exp_time", 0.1))
                        # XRD 单通道单工位：多样品时在同一工位依次跑单样品流程，不调用多样品多工位模式
                        xrd_result = None
                        for i, sid in enumerate(batch_sample_ids):
                            with self._lock:
                                self._current_xrd_running = {
                                    "scheme_index": scheme_idx,
                                    "scheme_id": scheme.get("scheme_id"),
                                    "sample_id": sid,
                                }
                            one = xrd_flow_mgr.run(
                                single=True,
                                sample_id=sid,
                                start_theta=st,
                                end_theta=et,
                                increment=inc,
                                exp_time=exp,
                            )
                            if not (isinstance(one, dict) and one.get("status")):
                                xrd_result = one
                                break
                            latest = xrd_flow_mgr.get_latest_data()
                            if isinstance(latest, dict) and latest.get("status") and latest.get("data"):
                                d = latest.get("data")
                                with self._lock:
                                    self._last_results.append({
                                        "experiment_id": exp_id,
                                        "sample_id": d.get("sample_id") or sid,
                                        "scheme_id": scheme.get("scheme_id"),
                                        "scheme_index": scheme_idx,
                                        "scheme_type": scheme.get("scheme_type", ""),
                                        "theta2": d.get("theta2"),
                                        "intensity": d.get("intensity"),
                                        "timestamp": d.get("timestamp"),
                                    })
                        if xrd_result is not None:
                            msg = xrd_result.get("message", "XRD测试失败") if isinstance(xrd_result, dict) else str(xrd_result)
                            if msg == "用户停止实验":
                                self._set_phase(ExperimentPhase.IDLE, error_message=msg)
                            else:
                                self._set_phase_error(msg, resume_phase=ExperimentPhase.WAITING_XRD_READY)
                            multi_oven_success = False
                            break
                    try:
                        prod_thread.join(timeout=2.0)
                    except Exception:
                        pass
                    if not multi_oven_success:
                        return
                    with self._lock:
                        to_persist = self._last_results if self._last_results else []
                    if exp_id and to_persist:
                        try:
                            experiment_persistence.insert_xrd_results(exp_id, to_persist)
                        except Exception as e:
                            logger.log(f"持久化XRD结果失败: {e}", "WARN")
                    self._set_phase(ExperimentPhase.COMPLETED, "实验流程已全部完成")
                    logger.log("实验总流程完成", "SUCCESS")
                    return
                else:
                    oven_id = int(thermal_params.get("oven_id", 1))
                    qty = int(thermal_params.get("qty", 1))
                    curve_points = self._resolve_thermal_curve_points()
                    thermal_result = thermal_flow_mgr.run(oven_id, qty, curve_points)
                if not thermal_result.get("status"):
                    msg = thermal_result.get("message", "热处理失败")
                    if msg == "用户停止实验":
                        self._set_phase(ExperimentPhase.IDLE, error_message=msg)
                    else:
                        self._set_phase_error(
                            msg,
                            resume_phase=ExperimentPhase.WAITING_XRD_READY,
                        )
                    return
                # 单炉路径：等全部热处理完成后，再统一等待XRD上样并做一次XRD
                if not use_multi_oven:
                    self._set_phase(ExperimentPhase.WAITING_XRD_READY, "热处理已完成，等待XRD上样")
                    logger.log(
                        "请将样品放入XRD试验台后调用 POST /api/experiment/flux/confirm_xrd_ready",
                        "WARN",
                    )

                if self._stop_requested:
                    self._set_phase(ExperimentPhase.IDLE, error_message="用户停止实验")
                    return
                self._xrd_ready_confirm.clear()
                if not self._wait_confirm_or_stop(self._xrd_ready_confirm, self._confirm_timeout):
                    if self._stop_requested:
                        self._set_phase(ExperimentPhase.IDLE, error_message="用户停止实验")
                    else:
                        self._set_phase_error("等待XRD上样确认超时", resume_phase=ExperimentPhase.WAITING_XRD_READY)
                    return
                logger.log("XRD上样已确认，开始XRD测试", "INFO")

            # ---------- 4. XRD 测试（仅单炉路径；多炉已在上面流水线中按批完成；恢复时 start_from_phase==WAITING_XRD_READY 也走此处）----------
            if not use_multi_oven or start_from_phase == ExperimentPhase.WAITING_XRD_READY:
                if start_from_phase == ExperimentPhase.WAITING_XRD_READY:
                    self._set_phase(ExperimentPhase.WAITING_XRD_READY, "热处理已完成，等待XRD上样（恢复流程）")
                    logger.log("请将样品放入XRD试验台后调用 POST /api/experiment/flux/confirm_xrd_ready", "WARN")
                    self._xrd_ready_confirm.clear()
                    if not self._wait_confirm_or_stop(self._xrd_ready_confirm, self._confirm_timeout):
                        if self._stop_requested:
                            self._set_phase(ExperimentPhase.IDLE, error_message="用户停止实验")
                        else:
                            self._set_phase_error("等待XRD上样确认超时", resume_phase=ExperimentPhase.WAITING_XRD_READY)
                        return
                    logger.log("XRD上样已确认，开始XRD测试", "INFO")
                if self._stop_requested:
                    self._set_phase(ExperimentPhase.IDLE, error_message="用户停止实验")
                    return
                scheme_manifest = (thermal_params.get("scheme_manifest") or []) if isinstance(thermal_params.get("scheme_manifest"), list) else []
                if not scheme_manifest:
                    scheme_manifest = [{"scheme_index": 0, "scheme_id": "方案0", "scheme_type": ""}]
                xrd_params = self._xrd_params or {}
                with self._lock:
                    pending = self._pending_xrd_sample_ids or []
                    self._pending_xrd_sample_ids = None
                sample_ids = [p["sample_id"] for p in pending]
                scheme_info_list = [(p["scheme_index"], p["scheme_id"]) for p in pending]
                if not sample_ids:
                    sample_ids = [f"方案0_{uuid.uuid4().hex[:8]}"]
                    scheme_info_list = [(0, "方案0")]
                with self._lock:
                    self._current_xrd_running = {
                        "scheme_index": 0,
                        "scheme_id": scheme_manifest[0].get("scheme_id") if scheme_manifest else None,
                        "sample_id": sample_ids[0] if sample_ids else None,
                    }
                self._set_phase(ExperimentPhase.XRD_RUNNING, "XRD测试执行中" + (" [Mock]" if mock else ""))
                start_theta = xrd_params.get("start_theta", 5.0)
                end_theta = xrd_params.get("end_theta", 120.0)
                increment = xrd_params.get("increment", 0.01)
                exp_time = xrd_params.get("exp_time", 0.1)
                # XRD 单通道单工位：多样品时在同一工位依次跑单样品流程，不调用多样品多工位模式
                exp_id = self._experiment_id or ""
                with self._lock:
                    self._last_results = []
                xrd_failed = None
                for i, sample_id in enumerate(sample_ids):
                    scheme_idx, scheme_id = scheme_info_list[i] if i < len(scheme_info_list) else (i, None)
                    m = scheme_manifest[scheme_idx] if scheme_idx < len(scheme_manifest) else {}
                    with self._lock:
                        self._current_xrd_running = {
                            "scheme_index": scheme_idx,
                            "scheme_id": scheme_id or m.get("scheme_id"),
                            "sample_id": sample_id,
                        }
                    one = xrd_flow_mgr.run(
                        single=True,
                        sample_id=sample_id,
                        start_theta=start_theta,
                        end_theta=end_theta,
                        increment=increment,
                        exp_time=exp_time,
                    )
                    if not (isinstance(one, dict) and one.get("status")):
                        xrd_failed = one
                        break
                    latest = xrd_flow_mgr.get_latest_data()
                    if isinstance(latest, dict) and latest.get("status") and latest.get("data"):
                        d = latest.get("data")
                        with self._lock:
                            self._last_results.append({
                                "experiment_id": exp_id,
                                "sample_id": d.get("sample_id") or sample_id,
                                "scheme_id": scheme_id or m.get("scheme_id"),
                                "scheme_index": scheme_idx,
                                "scheme_type": m.get("scheme_type", ""),
                                "theta2": d.get("theta2"),
                                "intensity": d.get("intensity"),
                                "timestamp": d.get("timestamp"),
                            })
                if xrd_failed is not None:
                    msg = str(xrd_failed) if not isinstance(xrd_failed, dict) else xrd_failed.get("message", "XRD测试失败")
                    if msg == "用户停止实验":
                        self._set_phase(ExperimentPhase.IDLE, error_message=msg)
                    else:
                        self._set_phase_error(msg, resume_phase=ExperimentPhase.WAITING_XRD_READY)
                    return
                with self._lock:
                    to_persist = (
                        self._last_results if self._last_results else []
                    )
                if exp_id and to_persist:
                    try:
                        experiment_persistence.insert_xrd_results(exp_id, to_persist)
                    except Exception as e:
                        logger.log(f"持久化XRD结果失败: {e}", "WARN")
                self._set_phase(ExperimentPhase.COMPLETED, "实验流程已全部完成")
                logger.log("实验总流程完成", "SUCCESS")
        except Exception as e:
            logger.log(f"实验流程异常: {e}", "ERROR")
            self._set_phase(ExperimentPhase.ERROR, error_message=str(e))
        finally:
            with self._lock:
                self._runner_thread = None

    # ------------------------- 对外 API（供 experiment_api 调用）-------------------------

    def start(
        self,
        raw_req: RecommendExperimentRecipes,
        mixer_model: AddTaskRequest,
        thermal_params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        启动一次新实验（非阻塞）。若当前已有实验在运行或等待确认，抛出 ValueError。
        thermal_params 可选：oven_id, qty, curve_name 或 curve_points（List[CurvePoint]），
        用于热处理阶段；若在 start 时传入 curve_points，则无需在 confirm_thermal_load 再传曲线。
        返回包含 experiment_id、phase、phase_label 的字典。
        """
        with self._lock:
            if self._phase not in (
                ExperimentPhase.IDLE,
                ExperimentPhase.COMPLETED,
                ExperimentPhase.ERROR,
            ):
                raise ValueError(
                    f"当前已有实验在运行或等待确认，阶段: {self._phase.value}。"
                    "请先查询状态并完成确认或等待结束。"
                )
            self._experiment_id = str(uuid.uuid4())
            self._task_name = getattr(mixer_model, "task_name", None)
            self._phase = ExperimentPhase.IDLE
            # 原始请求（供后续总结使用，原始请求中包含各个方案的名称，而解析后的mixer_model不包含方案名称）
            self._raw_req = raw_req
            # 配料数据
            self._mixer_model = mixer_model
            # 工艺数据
            self._thermal_params = thermal_params.copy() if thermal_params else None
            self._error_message = None
            self._step_info = ""
            self._stop_requested = False
            self._last_results = None
            self._current_xrd_batch = None
            self._current_xrd_running = None
            self._pending_xrd_sample_ids = None

        try:
            manifest = (self._thermal_params or {}).get("scheme_manifest") if isinstance((self._thermal_params or {}).get("scheme_manifest"), list) else None
            experiment_persistence.insert_experiment(
                self._experiment_id,
                task_name=self._task_name,
                scheme_manifest=manifest,
                thermal_params=self._thermal_params,
            )
        except Exception as e:
            logger.log(f"持久化实验记录失败: {e}", "WARN")

        logger.log(
            f"实验启动，任务名称: {self._task_name}，experiment_id: {self._experiment_id}",
            "INFO",
        )
        self._runner_thread = threading.Thread(
            target=self._run_experiment,
            args=(mixer_model,),
            daemon=True,
        )
        self._runner_thread.start()
        time.sleep(0.2)

        with self._lock:
            phase = self._phase
        return {
            "status": "started",
            "message": "实验已启动，可通过 GET /api/experiment/status 查询进度",
            "experiment_id": self._experiment_id,
            "phase": phase.value,
            "phase_label": PHASE_LABELS.get(phase, phase.value),
        }

    def get_status(self) -> ExperimentStatusResponse:
        """返回当前实验状态（供 Agent 或前端轮询）；phase=completed 时包含 result（2theta、intensity）。"""
        with self._lock:
            phase = self._phase
            experiment_id = self._experiment_id or "none"
            task_name = self._task_name
            error_message = self._error_message
            last_results = self._last_results
            manifest = (self._thermal_params or {}).get("scheme_manifest") if isinstance((self._thermal_params or {}).get("scheme_manifest"), list) else []
        # scheme_ids = [m.get("scheme_id") for m in manifest if m and m.get("scheme_id")] if manifest else None
        scheme_manifest = manifest if manifest else None
        step_info = self._get_step_info_from_flows()
        sub_flow_summaries = self._get_sub_flow_summaries()

        is_paused = phase in (
            ExperimentPhase.WAITING_SEAL_CONFIRM,
            ExperimentPhase.WAITING_THERMAL_LOAD,
            ExperimentPhase.WAITING_XRD_READY,
        )
        pending_action = PHASE_LABELS.get(phase, phase.value) if is_paused else ""
        phase_label = PHASE_LABELS.get(phase, phase.value)
        next_action = None
        if is_paused:
            thermal_params = self._thermal_params or {}
            xrd_params = self._xrd_params or {}
            with self._lock:
                current_xrd_batch = self._current_xrd_batch  # 多炉时当前等待 XRD 的批次
            if phase == ExperimentPhase.WAITING_SEAL_CONFIRM:
                next_action = NextAction(
                    method="POST",
                    path="/api/experiment/confirm_seal",
                    body_data={},
                    body_schema=[],
                )
            elif phase == ExperimentPhase.WAITING_THERMAL_LOAD:
                manifest = thermal_params.get("scheme_manifest") or []
                if not isinstance(manifest, list):
                    manifest = []
                if len(manifest) > 1:
                    body_data = {
                        "oven_assignments": [
                            {"scheme_index": i, "oven_id": None}
                            for i in range(len(manifest))
                        ]
                    }
                else:
                    body_data = {"oven_id": None}
                next_action = NextAction(
                    method="POST",
                    path="/api/experiment/confirm_thermal_load",
                    body_data=body_data,
                    body_schema=[
                        NextActionParam(name="oven_id", type="int", required=True, description="炉子ID，需用户填写（单炉）或 oven_assignments[].oven_id（多炉）；每方案一管，无需填数量"),
                    ],
                )
            elif phase == ExperimentPhase.WAITING_XRD_READY:
                st = float(xrd_params.get("start_theta", 5.1))
                et = float(xrd_params.get("end_theta", 120.0))
                inc = float(xrd_params.get("increment", 0.01))
                exp = float(xrd_params.get("exp_time", 0.1))
                if current_xrd_batch:
                    body_data = {
                        "start_theta": st,
                        "end_theta": et,
                        "increment": inc,
                        "exp_time": exp,
                        "scheme_index": int(current_xrd_batch.get("scheme_index", 0)),
                    }
                else:
                    manifest = scheme_manifest or []
                    if not isinstance(manifest, list):
                        manifest = []
                    default_scheme_index = 0
                    body_data = {
                        "start_theta": st,
                        "end_theta": et,
                        "increment": inc,
                        "exp_time": exp,
                        "scheme_index": default_scheme_index,
                    }
                next_action = NextAction(
                    method="POST",
                    path="/api/experiment/confirm_xrd_ready",
                    body_data=body_data,
                    body_schema=[
                        NextActionParam(name="start_theta", type="float", required=False, description="起始角度，默认已填", default=5.1),
                        NextActionParam(name="end_theta", type="float", required=False, description="结束角度，默认已填", default=120.0),
                        NextActionParam(name="increment", type="float", required=False, description="步长，默认已填", default=0.01),
                        NextActionParam(name="exp_time", type="float", required=False, description="曝光时间，默认已填", default=0.1),
                        NextActionParam(name="scheme_index", type="int", required=False, description="本次XRD对应的方案索引（默认0）", default=0),
                    ],
                )
        elif phase == ExperimentPhase.XRD_RUNNING:
            # XRD 子流程显式暴露「待确认」状态，编排层只读 get_pending_confirm()，不解析步骤文案
            pending = getattr(xrd_flow_mgr, "get_pending_confirm", lambda: None)()
            if pending and isinstance(pending, dict) and pending.get("message"):
                next_action = NextAction(
                    method="POST",
                    path="/api/flow/xrd/confirm",
                    body_data={},
                    body_schema=[],
                )
                phase_label = "等待XRD上样：请将样品放入XRD试验台后调用 POST /api/flow/xrd/confirm"
                pending_action = "等待XRD上样：请将样品放入XRD试验台后调用 POST /api/flow/xrd/confirm"
        elif phase == ExperimentPhase.ERROR:
            with self._lock:
                resume_phase = self._error_resume_phase
            if resume_phase is not None:
                next_action = NextAction(
                    method="POST",
                    path="/api/experiment/confirm_continue_after_error",
                    body_data={"resume_phase": resume_phase.value},
                    body_schema=[
                        NextActionParam(name="resume_phase", type="string", required=False, description="从该阶段继续执行，与当前错误可恢复阶段一致", default=None),
                    ],
                )
        
        sub_flow = (
            "mix" if phase == ExperimentPhase.MIXING else "load"
            if phase == ExperimentPhase.LOADING else "thermal"
            if phase == ExperimentPhase.THERMAL_RUNNING else "xrd"
            if phase == ExperimentPhase.XRD_RUNNING else None
        )
        result = None
        try:
            result = [XRDResultData(**item) for item in last_results] if last_results else None
        except Exception:
            result = None

        xrd_running_sample = None
        if phase == ExperimentPhase.XRD_RUNNING:
            with self._lock:
                fallback = self._current_xrd_running
            cur = getattr(xrd_flow_mgr, "current_running_sample", None)
            if cur and isinstance(cur, dict) and cur.get("sample_id"):
                xrd_running_sample = {
                    "scheme_index": cur.get("scheme_index"),
                    "scheme_id": cur.get("scheme_id"),
                    "sample_id": cur.get("sample_id"),
                }
                # 单样品 run 时 xrd_flow 只设置 sample_id，不设置 scheme_index/scheme_id，若用 scheme_manifest[0] 会错配（如 scheme_id=方案_A、sample_id=方案_C_xxx）
                if xrd_running_sample["scheme_index"] is None or xrd_running_sample["scheme_id"] is None:
                    if fallback and fallback.get("sample_id") == xrd_running_sample["sample_id"]:
                        xrd_running_sample["scheme_index"] = fallback.get("scheme_index")
                        xrd_running_sample["scheme_id"] = fallback.get("scheme_id")
                    elif scheme_manifest:
                        xrd_running_sample["scheme_index"] = 0
                        xrd_running_sample["scheme_id"] = (scheme_manifest[0] or {}).get("scheme_id")
            elif fallback and fallback.get("sample_id"):
                xrd_running_sample = {
                    "scheme_index": fallback.get("scheme_index"),
                    "scheme_id": fallback.get("scheme_id"),
                    "sample_id": fallback.get("sample_id"),
                }

        return ExperimentStatusResponse(
            experiment_id=experiment_id,
            phase=phase,
            phase_label=phase_label,
            is_paused=is_paused,
            pending_action=pending_action,
            step_info=step_info,
            sub_flow=sub_flow,
            sub_flow_summaries=sub_flow_summaries if sub_flow_summaries else None,
            error_message=error_message,
            task_name=task_name,
            scheme_manifest=scheme_manifest,
            result=result,
            next_action=next_action,
            xrd_running_sample=xrd_running_sample,
        )

    def confirm_seal(self) -> None:
        """确认熔封完成，状态机从 WAITING_SEAL_CONFIRM 进入下一阶段（由 _run_experiment 推进）"""
        self._seal_confirm.set()
        logger.log("熔封确认已接收", "INFO")

    def confirm_thermal_load(
        self,
        oven_id: Optional[int] = None,
        qty: Optional[int] = None,
        curve_name: Optional[str] = None,
        curve_points: Optional[list] = None,
        oven_assignments: Optional[list] = None,
    ) -> None:
        """确认样品已放入加热炉，可选传入热处理参数；与 start 时的 thermal_params 合并。
        若传 oven_assignments（多炉分配），则按炉按 scheme_index 取曲线执行；否则沿用单炉 oven_id/qty/curve_points。"""
        with self._lock:
            prev = self._thermal_params or {}
            params = {
                "oven_id": oven_id if oven_id is not None else prev.get("oven_id", 1),
                "qty": qty if qty is not None else prev.get("qty", 1),
                "curve_name": curve_name or prev.get("curve_name"),
                "curve_points": curve_points if curve_points is not None else prev.get("curve_points"),
                "scheme_manifest": prev.get("scheme_manifest"),
            }
            if oven_assignments is not None:
                params["oven_assignments"] = [
                    {"oven_id": a.get("oven_id"), "scheme_index": a.get("scheme_index"), "qty": a.get("qty", 1)}
                    for a in oven_assignments
                    if isinstance(a, dict) and "scheme_index" in a
                ] if isinstance(oven_assignments, list) else []
            else:
                params["oven_assignments"] = prev.get("oven_assignments")
            self._thermal_params = params
        self._thermal_load_confirm.set()
        logger.log("加热炉上料确认已接收", "INFO")

    def confirm_xrd_ready(self, 
        start_theta: Optional[float] = None, 
        end_theta: Optional[float] = None, 
        increment: Optional[float] = None, 
        exp_time: Optional[float] = None,
        scheme_index: Optional[int] = None) -> None:
        """确认样品已放入 XRD 试验台。此时生成 sample_id 并与 experiment_id/scheme_id 绑定入库；可选传入 XRD 参数与 start 时合并。"""
        with self._lock:
            prev = self._xrd_params or {}
            params = {
                "start_theta": start_theta if start_theta is not None else prev.get("start_theta", 5.0),
                "end_theta": end_theta if end_theta is not None else prev.get("end_theta", 120.0),
                "increment": increment if increment is not None else prev.get("increment", 0.01),
                "exp_time": exp_time if exp_time is not None else prev.get("exp_time", 0.1),
                "scheme_index": scheme_index if scheme_index is not None else prev.get("scheme_index", 0),
            }
            self._xrd_params = params
            exp_id = self._experiment_id or ""
            batch = self._current_xrd_batch
            manifest = (self._thermal_params or {}).get("scheme_manifest") or []
            if not isinstance(manifest, list):
                manifest = []
            pending = []
            if batch:
                scheme_id = batch.get("scheme_id") or f"方案{batch.get('scheme_index', 0)}"
                scheme_index = int(batch.get("scheme_index", 0))
                sample_id = f"{scheme_id}_{uuid.uuid4().hex[:8]}"
                try:
                    experiment_persistence.insert_sample_binding(exp_id, sample_id, scheme_id=scheme_id, scheme_index=scheme_index)
                except Exception as e:
                    logger.log(f"写入样品绑定失败: {e}", "WARN")
                pending.append({"sample_id": sample_id, "scheme_id": scheme_id, "scheme_index": scheme_index})
            elif manifest:
                for i, m in enumerate(manifest):
                    scheme_id = (m or {}).get("scheme_id") or f"方案{i}"
                    sample_id = f"{scheme_id}_{uuid.uuid4().hex[:8]}"
                    try:
                        experiment_persistence.insert_sample_binding(exp_id, sample_id, scheme_id=scheme_id, scheme_index=i)
                    except Exception as e:
                        logger.log(f"写入样品绑定失败: {e}", "WARN")
                    pending.append({"sample_id": sample_id, "scheme_id": scheme_id, "scheme_index": i})
            else:
                sample_id = f"方案0_{uuid.uuid4().hex[:8]}"
                try:
                    experiment_persistence.insert_sample_binding(exp_id, sample_id, scheme_id="方案0", scheme_index=0)
                except Exception as e:
                    logger.log(f"写入样品绑定失败: {e}", "WARN")
                pending.append({"sample_id": sample_id, "scheme_id": "方案0", "scheme_index": 0})
            self._pending_xrd_sample_ids = pending
        self._xrd_ready_confirm.set()
        logger.log("XRD上样确认已接收，已生成并绑定 sample_id", "INFO")

    def confirm_continue_after_error(self, resume_phase: Optional[str] = None) -> Dict[str, Any]:
        """
        报错后从下一阶段继续执行。仅当 phase=error 且存在可恢复阶段时有效。
        resume_phase 可选，不传则使用内部记录的 _error_resume_phase。
        返回 {"status": "ok", "message": "...", "resume_phase": "..."} 或 {"status": "error", "message": "..."}。
        """
        with self._lock:
            if self._phase != ExperimentPhase.ERROR:
                return {"status": "error", "message": "当前未处于报错状态，无需恢复"}
            phase_to_resume = self._error_resume_phase
            if phase_to_resume is None and resume_phase is not None:
                try:
                    phase_to_resume = ExperimentPhase(resume_phase)
                except ValueError:
                    return {"status": "error", "message": f"无效的 resume_phase: {resume_phase}"}
            if phase_to_resume is None:
                return {"status": "error", "message": "该错误不可恢复或未记录恢复阶段"}
            if self._mixer_model is None:
                return {"status": "error", "message": "缺少实验上下文，无法恢复"}
            if self._runner_thread is not None and self._runner_thread.is_alive():
                return {"status": "error", "message": "已有流程在运行"}
            self._error_message = None
            self._error_resume_phase = None
            self._phase = phase_to_resume
            self._step_info = f"从 {phase_to_resume.value} 恢复执行"
            self._stop_requested = False
            mixer_model = self._mixer_model
        try:
            experiment_persistence.update_experiment_phase(self._experiment_id or "", phase_to_resume.value, None)
        except Exception as e:
            logger.log(f"持久化恢复阶段失败: {e}", "WARN")
        logger.log(f"用户确认从 {phase_to_resume.value} 继续执行", "INFO")
        self._runner_thread = threading.Thread(
            target=self._run_experiment,
            args=(mixer_model,),
            kwargs={"start_from_phase": phase_to_resume},
            daemon=True,
        )
        self._runner_thread.start()
        return {"status": "ok", "message": f"已从 {phase_to_resume.value} 继续执行", "resume_phase": phase_to_resume.value}

    def stop(self) -> bool:
        """
        请求停止当前实验。若正在运行或处于等待确认阶段，将置位停止标志并唤醒等待，
        并立即将 phase 置为 IDLE，使 get_status() 立刻显示「用户停止实验」；
        后台线程会在下一轮检查时退出。
        返回 True 表示已发出停止请求，False 表示当前无实验在跑。
        """
        with self._lock:
            if self._phase in (
                ExperimentPhase.IDLE,
                ExperimentPhase.COMPLETED,
                ExperimentPhase.ERROR,
            ) and not self._runner_thread:
                return False
            self._stop_requested = True
        self._set_phase(ExperimentPhase.IDLE, error_message="用户停止实验")
        self._seal_confirm.set()
        self._thermal_load_confirm.set()
        self._xrd_ready_confirm.set()
        mix_flow_mgr.stop()
        thermal_flow_mgr.stop()
        xrd_flow_mgr.stop()
        logger.log("已请求停止实验", "WARN")
        return True


# 单例，供 API 层注入使用（无全局分散状态）
experiment_orchestrator = ExperimentOrchestrator(confirm_timeout=CONFIRM_TIMEOUT)
