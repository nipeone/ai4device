"""
实验总流程编排器：显式状态机 + 子流程调度，无全局状态。

职责：
- 维护当前实验阶段（phase）与上下文（experiment_id、step_info、thermal_params 等）
- 在后台线程中按阶段执行：配料 -> 熔封确认 -> 热处理 -> XRD确认 -> XRD测试
- 提供 start / get_status / confirm_seal / confirm_thermal_load / confirm_xrd_ready 供 API 层调用

说明：未引入 Celery。若后续需要任务持久化、多 Worker 或分布式队列，可在此层将
_run_experiment 拆为多个 Celery task，由本状态机驱动 task 链。
"""
import random
import threading
import time
import uuid
from typing import Optional, Any, Dict

from logger import sys_logger as logger
from schemas.oven import CurvePoint
from schemas.experiment import (
    ExperimentPhase,
    ExperimentStatusResponse,
    PHASE_LABELS,
    XRDResultData,
)

from flows.mix_flow import mix_flow_mgr
from flows.thermal_flow import thermal_flow_mgr
from flows.xrd_flow import xrd_flow_mgr
from services.oven import oven_service

try:
    import config
    _MOCK_DEVICES = getattr(config, "MOCK_DEVICES", False)
    _MOCK_STEP_DELAY = getattr(config, "MOCK_STEP_DELAY", 1.0)
except Exception:
    _MOCK_DEVICES = False
    _MOCK_STEP_DELAY = 1.0

CONFIRM_TIMEOUT = 300  # 各阶段等待确认超时（秒）
# Mock 时每个子流程（配料/热处理/XRD）模拟执行时长范围（秒），便于感知流程是否都执行过
MOCK_STEP_DURATION_MIN = 20
MOCK_STEP_DURATION_MAX = 30


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
        # 实验成功完成时的 XRD 结果（2theta、intensity），由 get_latest_data 提供
        self._last_result: Optional[Dict[str, Any]] = None

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

    def _get_step_info_from_flows(self) -> str:
        """从当前活跃子流程取步骤信息"""
        if self._phase == ExperimentPhase.MIXING and mix_flow_mgr.running:
            return getattr(mix_flow_mgr, "current_step_info", "") or "配料中"
        if self._phase == ExperimentPhase.THERMAL_RUNNING and thermal_flow_mgr.running:
            return getattr(thermal_flow_mgr, "current_step_info", "") or "热处理中"
        if self._phase == ExperimentPhase.XRD_RUNNING and xrd_flow_mgr.running:
            return getattr(xrd_flow_mgr, "current_step_info", "") or "XRD测试中"
        return self._step_info

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

    def _run_experiment(self, mixer_model: Any) -> None:
        """在后台线程中按状态机执行各阶段（配料 -> 熔封确认 -> 热处理 -> XRD确认 -> XRD测试）"""
        mock = _MOCK_DEVICES
        try:
            # ---------- 1. 配料 ----------
            if self._stop_requested:
                self._set_phase(ExperimentPhase.ERROR, error_message="用户停止实验")
                return
            self._set_phase(ExperimentPhase.MIXING, "配料流程启动" + (" [Mock]" if mock else ""))
            logger.log("实验流程：开始配料" + (" [Mock 模式，模拟执行 30～60 秒]" if mock else ""), "INFO")
            if mock:
                self._mock_sleep_with_stop_check(MOCK_STEP_DURATION_MIN, MOCK_STEP_DURATION_MAX)
                mix_result = {"status": True, "message": "mock 配料完成"}
            else:
                mix_result = mix_flow_mgr.run(mixer_model)
            if self._stop_requested:
                self._set_phase(ExperimentPhase.ERROR, error_message="用户停止实验")
                return
            if not mix_result.get("status"):
                self._set_phase(
                    ExperimentPhase.ERROR,
                    error_message=mix_result.get("message", "配料失败"),
                )
                return
            self._set_phase(ExperimentPhase.WAITING_SEAL_CONFIRM, "配料已完成，等待熔封确认")
            logger.log("等待熔封完成，请调用 POST /api/experiment/flux/confirm_seal", "WARN")

            self._seal_confirm.clear()
            if not self._wait_confirm_or_stop(self._seal_confirm, self._confirm_timeout):
                if self._stop_requested:
                    self._set_phase(ExperimentPhase.ERROR, error_message="用户停止实验")
                else:
                    self._set_phase(ExperimentPhase.ERROR, error_message="等待熔封确认超时")
                return
            logger.log("熔封已确认", "INFO")

            # ---------- 2. 等待加热炉上料确认 ----------
            if self._stop_requested:
                self._set_phase(ExperimentPhase.ERROR, error_message="用户停止实验")
                return
            self._set_phase(
                ExperimentPhase.WAITING_THERMAL_LOAD,
                "请将样品放入加热炉后调用 confirm_thermal_load",
            )
            self._thermal_load_confirm.clear()
            if not self._wait_confirm_or_stop(self._thermal_load_confirm, self._confirm_timeout):
                if self._stop_requested:
                    self._set_phase(ExperimentPhase.ERROR, error_message="用户停止实验")
                else:
                    self._set_phase(ExperimentPhase.ERROR, error_message="等待加热炉上料确认超时")
                return
            logger.log("加热炉上料已确认，开始热处理", "INFO")

            # ---------- 3. 热处理 ----------
            if self._stop_requested:
                self._set_phase(ExperimentPhase.ERROR, error_message="用户停止实验")
                return
            params = self._thermal_params or {}
            oven_id = int(params.get("oven_id", 1))
            qty = int(params.get("qty", 1))
            curve_points = self._resolve_thermal_curve_points()
            self._set_phase(ExperimentPhase.THERMAL_RUNNING, "热处理执行中" + (" [Mock]" if mock else ""))
            if mock:
                logger.log("Mock 热处理：模拟执行 30～60 秒", "INFO")
                self._mock_sleep_with_stop_check(MOCK_STEP_DURATION_MIN, MOCK_STEP_DURATION_MAX)
                thermal_result = {"status": True, "message": "mock 热处理完成"}
            else:
                thermal_result = thermal_flow_mgr.run(oven_id, qty, curve_points)
            if not thermal_result.get("status"):
                self._set_phase(
                    ExperimentPhase.ERROR,
                    error_message=thermal_result.get("message", "热处理失败"),
                )
                return
            self._set_phase(ExperimentPhase.WAITING_XRD_READY, "热处理已完成，等待XRD上样")
            logger.log(
                "请将样品放入XRD试验台后调用 POST /api/experiment/flux/confirm_xrd_ready",
                "WARN",
            )

            if self._stop_requested:
                self._set_phase(ExperimentPhase.ERROR, error_message="用户停止实验")
                return
            self._xrd_ready_confirm.clear()
            if not self._wait_confirm_or_stop(self._xrd_ready_confirm, self._confirm_timeout):
                if self._stop_requested:
                    self._set_phase(ExperimentPhase.ERROR, error_message="用户停止实验")
                else:
                    self._set_phase(ExperimentPhase.ERROR, error_message="等待XRD上样确认超时")
                return
            logger.log("XRD上样已确认，开始XRD测试", "INFO")

            # ---------- 4. XRD 测试 ----------
            if self._stop_requested:
                self._set_phase(ExperimentPhase.ERROR, error_message="用户停止实验")
                return
            self._set_phase(ExperimentPhase.XRD_RUNNING, "XRD测试执行中" + (" [Mock]" if mock else ""))
            if mock:
                logger.log("Mock XRD 测试：模拟执行 30～60 秒", "INFO")
                self._mock_sleep_with_stop_check(MOCK_STEP_DURATION_MIN, MOCK_STEP_DURATION_MAX)
                xrd_result = {"status": True, "message": "mock XRD 完成"}
            else:
                xrd_result = xrd_flow_mgr.run(
                    single=True,
                    sample_id="XY000",
                    start_theta=5.0,
                    end_theta=120.0,
                    increment=0.01,
                    exp_time=0.1,
                )
            if not (isinstance(xrd_result, dict) and xrd_result.get("status")):
                msg = (
                    str(xrd_result)
                    if not isinstance(xrd_result, dict)
                    else xrd_result.get("message", "XRD测试失败")
                )
                self._set_phase(ExperimentPhase.ERROR, error_message=msg)
                return
            # 实验成功完成：从 XRD 流程获取最新数据（2theta、intensity）并保存
            if mock:
                with self._lock:
                    self._last_result = {
                        "sample_id": "mock",
                        "theta2": [],
                        "intensity": [],
                        "timestamp": None,
                    }
            else:
                try:
                    latest = xrd_flow_mgr.get_latest_data()
                    if isinstance(latest, dict) and latest.get("status") and latest.get("data"):
                        with self._lock:
                            self._last_result = latest.get("data")
                    else:
                        with self._lock:
                            self._last_result = None
                except Exception as e:
                    logger.log(f"保存XRD结果时忽略异常: {e}", "WARN")
                    with self._lock:
                        self._last_result = None
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
        mixer_model: Any,
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
            self._thermal_params = thermal_params.copy() if thermal_params else None
            self._error_message = None
            self._step_info = ""
            self._stop_requested = False
            self._last_result = None

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
            last_result = self._last_result
        step_info = self._get_step_info_from_flows()

        is_paused = phase in (
            ExperimentPhase.WAITING_SEAL_CONFIRM,
            ExperimentPhase.WAITING_THERMAL_LOAD,
            ExperimentPhase.WAITING_XRD_READY,
        )
        pending_action = PHASE_LABELS.get(phase, phase.value) if is_paused else ""
        sub_flow = (
            "mix"
            if phase == ExperimentPhase.MIXING
            else "thermal"
            if phase == ExperimentPhase.THERMAL_RUNNING
            else "xrd"
            if phase == ExperimentPhase.XRD_RUNNING
            else None
        )
        try:
            result = XRDResultData(**last_result) if isinstance(last_result, dict) and last_result else None
        except Exception:
            result = None

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
            result=result,
        )

    def confirm_seal(self) -> None:
        """确认熔封完成，状态机从 WAITING_SEAL_CONFIRM 进入下一阶段（由 _run_experiment 推进）"""
        self._seal_confirm.set()
        logger.log("熔封确认已接收", "INFO")

    def confirm_thermal_load(
        self,
        oven_id: int = 1,
        qty: int = 1,
        curve_name: Optional[str] = None,
        curve_points: Optional[list] = None,
    ) -> None:
        """确认样品已放入加热炉，可选传入热处理参数；与 start 时的 thermal_params 合并，保留已有 curve_points（若未传 curve_name/curve_points）"""
        with self._lock:
            prev = self._thermal_params or {}
            self._thermal_params = {
                "oven_id": oven_id,
                "qty": qty,
                "curve_name": curve_name or prev.get("curve_name"),
                "curve_points": curve_points if curve_points is not None else prev.get("curve_points"),
            }
        self._thermal_load_confirm.set()
        logger.log("加热炉上料确认已接收", "INFO")

    def confirm_xrd_ready(self) -> None:
        """确认样品已放入 XRD 试验台"""
        self._xrd_ready_confirm.set()
        logger.log("XRD上样确认已接收", "INFO")

    def stop(self) -> bool:
        """
        请求停止当前实验。若正在运行或处于等待确认阶段，将置位停止标志并唤醒等待，
        后台线程会在下一轮检查时退出并将 phase 置为 ERROR（error_message="用户停止实验"）。
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
        self._seal_confirm.set()
        self._thermal_load_confirm.set()
        self._xrd_ready_confirm.set()
        thermal_flow_mgr.stop()
        xrd_flow_mgr.stop()
        logger.log("已请求停止实验", "WARN")
        return True


# 单例，供 API 层注入使用（无全局分散状态）
experiment_orchestrator = ExperimentOrchestrator(confirm_timeout=CONFIRM_TIMEOUT)
