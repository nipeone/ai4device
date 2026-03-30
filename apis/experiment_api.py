"""
实验总流程 API：委托给 flows.experiment_flow 中的状态机编排器，无全局状态。
实验后 XRD 补充测试：POST /api/experiment/{experiment_id}/xrd-supplement，与 experiment_id/sample_id 关联存储。

启动实验：
- POST /flux：入参为大模型规范输出（JSON，见 schemas/llm_output.py），
  从中提取原料 -> AddTaskRequest、温度程序 -> List[CurvePoint]，并可选炉号/数量。
- POST /flux/from_excel：兼容旧版，上传 Excel 解析为配料任务（无温度曲线，曲线由 confirm_thermal_load 或默认提供）。

大模型输出 -> 配方表（与 配方-0122.xlsx 结构一致，不启动实验）：
- POST /recipe-from-llm：入参同 /flux，返回 JSON（rows 为每行配方的 name/weight_mg 列表）。
- POST /recipe-from-llm/excel：入参同 /flux，返回 Excel 文件下载。

大模型输出 -> 温度曲线（不启动实验）：
- POST /temperature-from-llm：入参同 /flux，返回 JSON（取第一个方案的 工艺参数.温度程序 转成的 curve_points 及原始温度程序字段）。

流程节点：
  配料、熔封 -> [等待熔封确认] -> 上料 -> [等待加热炉上料确认] -> 热处理 -> [等待XRD上样确认] -> XRD测试 -> 完成
"""
import io
import json
import uuid
from datetime import datetime
from typing import Optional
from urllib.parse import quote

from fastapi import APIRouter, File, UploadFile, Request
from fastapi.responses import StreamingResponse

from fastapi import Query

from flows.experiment_flow import experiment_orchestrator
from flows.xrd_flow import xrd_flow_mgr
from services.mixer import mixer_service
from services import experiment_persistence
from services.mixer import add_task_request_to_recipe_rows, add_task_request_to_excel_bytes
from services.experiment_input import (
    llm_output_to_add_task_request,
    llm_output_to_curve_points,
    llm_output_to_curve_points_for_scheme_index,
    get_scheme_manifest,
    get_selected_scheme,
    get_schemes,
)
from schemas.experiment import ThermalParamsRequest, XRDParamsRequest, XRDSupplementRequest, StartExperimentRequest
from schemas.llm_output import RecommendExperimentRecipes

from logger import sys_logger as logger

router = APIRouter(prefix="/api/experiment", tags=["实验"])


def _wrap_success(message: str, data=None, code: int = 200):
    """统一成功响应：{"code": 200, "status": "success", "message": "...", "data": {...}}"""
    return {"code": code, "status": "success", "message": message, "data": data}


def _wrap_error(message: str, code: int = 400, data=None):
    """统一错误响应：{"code": 4xx/5xx, "status": "error", "message": "...", "data": {...}}"""
    return {"code": code, "status": "error", "message": message, "data": data}


@router.post("/start", tags=["实验"])
async def start_experiment(req: StartExperimentRequest):
    """
    使用大模型规范输出启动实验（JSON 入参，与 data/llm_output.json 结构一致）。

    入参可为两种形式：
    - 直接传 JSON 对象：{"推荐实验方案列表": [...], ...}
    - 传 JSON 字符串："{ \"推荐实验方案列表\": [...] }"（内部会 json.loads 再解析为 StartExperimentRequest）

    推荐实验方案列表 顺序即试管序号：配料按该顺序出列（每列一配方），加热、离心、XRD 与同一序号对应。
    - 配料：推荐实验方案列表 全部参与，layout 每列对应一个方案；
    - 温度曲线：取第一个方案的 工艺参数.温度程序；
    - 完成时 result/results 含 scheme_id，便于大模型按配方总结。

    流程在后台执行，在熔封/上料/XRD上样等节点暂停，需调用对应 confirm 接口恢复。
    """
    try:
        if req.recommend_recipes_str:
            recommend_recipes = RecommendExperimentRecipes.model_validate(json.loads(req.recommend_recipes_str))
        elif req.recommend_recipes:
            recommend_recipes = req.recommend_recipes
        else:
            recommend_recipes = req
    except Exception as e:
        return _wrap_error(f"请求体解析失败: {e}", 422)
    try:
        scheme_manifest = get_scheme_manifest(recommend_recipes)
    except ValueError as e:
        return _wrap_error(str(e), 400)
    add_task = llm_output_to_add_task_request(recommend_recipes)
    curve_points = llm_output_to_curve_points(recommend_recipes)
    logger.info(f"add_task: {add_task}, scheme_manifest: {len(scheme_manifest)} tube(s)")
    logger.info(f"curve_points: {curve_points}")
    thermal_params = {
        "oven_id": 3,
        "qty": len(scheme_manifest),
        "curve_points": [p.model_dump() for p in curve_points],
        "scheme_manifest": scheme_manifest,
    }
    try:
        result = experiment_orchestrator.start(req.task_id, recommend_recipes, add_task, thermal_params)
        result["scheme_manifest"] = scheme_manifest
        data = {
            "experiment_id": result["experiment_id"],
            "phase": result["phase"],
            "phase_label": result["phase_label"],
            "scheme_manifest": result["scheme_manifest"],
        }
        return _wrap_success(result["message"], data)
    except ValueError as e:
        st = experiment_orchestrator.get_status()
        data = {
            "experiment_id": st.experiment_id,
            "phase": st.phase.value,
            "phase_label": st.phase_label,
            "scheme_manifest": st.scheme_manifest,
        }
        return _wrap_error(str(e), 409, data)


@router.post("/temperature-from-llm", tags=["实验"])
async def llm_output_to_temperature_format(req: StartExperimentRequest):
    """
    将大模型规范输出中的温度程序转为加热炉曲线数据（JSON），不启动实验。

    取 推荐实验方案列表 中第一个方案的 工艺参数.温度程序，生成 curve_points（温度℃、时间h），
    并返回原始温度程序字段便于核对。时间单位为小时（累积），最后一点 temperature=-121 表示结束。
    """
    try:
        if req.recommend_recipes_str:
            recommend_recipes = RecommendExperimentRecipes.model_validate(json.loads(req.recommend_recipes_str))
        elif req.recommend_recipes:
            recommend_recipes = req.recommend_recipes
        else:
            recommend_recipes = req
    except Exception as e:
        return _wrap_error(f"请求体解析失败: {e}", 422)
    try:
        schemes = get_schemes(recommend_recipes)
        for scheme_index, scheme in enumerate(schemes):
            curve_points = llm_output_to_curve_points_for_scheme_index(recommend_recipes, scheme_index)
            temperature_program = (
                scheme.process_recipe.temperature_program.model_dump(by_alias=True) if scheme.process_recipe and scheme.process_recipe.temperature_program else None
            )
        schemes_data = [
            {
                "scheme_id": (scheme.方案ID or "").strip() or "方案0",
                "curve_points": [{"temperature": p.temperature, "time": p.time} for p in llm_output_to_curve_points_for_scheme_index(recommend_recipes, scheme_index)],
                "temperature_program": scheme.process_recipe.temperature_program.model_dump(by_alias=True) if scheme.process_recipe and scheme.process_recipe.temperature_program else None,
                "description": "curve_points 为加热炉曲线点，时间单位小时；temperature=-121 表示结束",
            }
            for scheme_index, scheme in enumerate(schemes)
        ]
        return _wrap_success("success", {"schemes": schemes_data})
    except ValueError as e:
        return _wrap_error(str(e), 400)


@router.post("/recipe-from-llm", tags=["实验"])
async def llm_output_to_recipe_format(req: StartExperimentRequest):
    """
    将大模型规范输出转为与「配方 Excel」一致的数据格式（JSON），不启动实验。

    返回结构：每行一个配方，行内为 [{"name": "【SSSI】物质名或物质名", "weight_mg": 数值}, ...]，
    与 docs/配方-0122.xlsx 的表格结构对应，便于预览或再导入。
    """
    try:
        if req.recommend_recipes_str:
            recommend_recipes = RecommendExperimentRecipes.model_validate(json.loads(req.recommend_recipes_str))
        elif req.recommend_recipes:
            recommend_recipes = req.recommend_recipes
        else:
            recommend_recipes = req
    except Exception as e:
        return _wrap_error(f"请求体解析失败: {e}", 422)
    try:
        add_task = llm_output_to_add_task_request(recommend_recipes)
        rows = add_task_request_to_recipe_rows(add_task)
        # 转为可 JSON 序列化的结构
        out = [[{"name": name, "weight": round(w, 2), "unit": unit} for name, w, unit in row] for row in rows]
        data = {
            "task_name": add_task.task_name,
            "schemas": out,
            "description": "每个schema对应一个配方，与配方 Excel 行结构一致；name 含【SSSI】时与 Excel 中【SSSI】名称一致",
        }
        return _wrap_success("success", data)
    except ValueError as e:
        return _wrap_error(str(e), 400)


@router.post("/recipe-from-llm/excel", tags=["实验"])
async def llm_output_to_recipe_excel(req: StartExperimentRequest):
    """
    将大模型规范输出转为与「配方 Excel」一致的文件并下载，不启动实验。

    表格结构：每行一个配方，列为成对的「物质名」「重量(mg)」，与 配方-0122.xlsx 类似。
    """
    try:
        if req.recommend_recipes_str:
            recommend_recipes = RecommendExperimentRecipes.model_validate(json.loads(req.recommend_recipes_str))
        elif req.recommend_recipes:
            recommend_recipes = req.recommend_recipes
        else:
            recommend_recipes = req
    except Exception as e:
        return _wrap_error(f"请求体解析失败: {e}", 422)
    try:
        add_task = llm_output_to_add_task_request(recommend_recipes)
        excel_bytes = add_task_request_to_excel_bytes(add_task)
        # 文件名可能含中文，需用 RFC 5987 编码，避免 Content-Disposition 头 latin-1 报错
        raw_name = (add_task.task_name or "export").strip() or "export"
        safe_ascii = f"recipe_{datetime.now().strftime('%Y%m%d%H%M')}.xlsx"
        disp_value = f"attachment; filename=\"{safe_ascii}\"; filename*=UTF-8''{quote(f'recipe_{raw_name}.xlsx', safe='')}"
        return StreamingResponse(
            io.BytesIO(excel_bytes),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": disp_value},
        )
    except ValueError as e:
        return _wrap_error(str(e), 400)
    except Exception as e:
        return _wrap_error(f"生成配方 Excel 失败: {e}", 500)


@router.post("/from_excel", tags=["实验"])
async def start_experiment_from_excel(file: UploadFile = File(...)):
    """
    兼容旧版：上传 Excel 启动实验，仅解析配料任务；温度曲线由 confirm_thermal_load 传入曲线名或使用默认。
    """
    if not file.filename or not file.filename.lower().endswith((".xlsx", ".xls")):
        return _wrap_error("只支持上传 Excel 文件(.xlsx, .xls)", 400)

    contents = await file.read()
    mixer_model = await mixer_service.parse_mixer_tasks_from_excel(contents)

    try:
        raw_req = StartExperimentRequest(recommend_recipes=RecommendExperimentRecipes())
        result = experiment_orchestrator.start(raw_req.task_id, raw_req.recommend_recipes, mixer_model)
        data = {
            "experiment_id": result["experiment_id"],
            "phase": result["phase"],
            "phase_label": result["phase_label"],
            "scheme_manifest": result.get("scheme_manifest"),
        }
        return _wrap_success(result["message"], data)
    except ValueError as e:
        st = experiment_orchestrator.get_status()
        data = {
            "experiment_id": st.experiment_id,
            "phase": st.phase.value,
            "phase_label": st.phase_label,
            "scheme_manifest": getattr(st, "scheme_manifest", None),
        }
        return _wrap_error(str(e), 409, data)


@router.get("/status", tags=["实验"])
def get_experiment_status():
    """
    查询当前实验进度（供 AI Agent 或前端轮询）。
    返回阶段、是否暂停、建议的下一步操作与子流程步骤描述。
    sub_flow_summaries 仅包含当前阶段对应子流程的摘要：mixing 时仅 mix，thermal_running 时仅 thermal，xrd_running/completed/error 时仅 xrd；等待确认阶段为空。
    当 phase=completed 时，result 字段会包含 XRD 最新数据：theta2（2θ 角度列表）、intensity（强度列表）、sample_id、timestamp。
    """
    st = experiment_orchestrator.get_status()
    data = st.model_dump(mode="json") if hasattr(st, "model_dump") else st
    return _wrap_success("获取状态成功", data)


@router.get("/history", tags=["实验"])
def list_experiments(
    limit: int = Query(50, ge=1, le=200, description="返回条数"),
    offset: int = Query(0, ge=0, description="偏移"),
):
    """
    分页查询历史实验列表（持久化数据），按创建时间倒序。
    程序重启后仍可查询到已持久化的实验记录。
    """
    items = experiment_persistence.list_experiments(limit=limit, offset=offset)
    return _wrap_success("获取实验列表成功", {"total": len(items), "items": items})


@router.get("/record/{experiment_id}", tags=["实验"])
def get_experiment_by_id(experiment_id: str):
    """
    按 experiment_id 查询单条实验详情（持久化数据），含 scheme_manifest、thermal_params 及该实验的全部 XRD 结果。
    程序重启后仍可查询。
    """
    row = experiment_persistence.get_experiment(experiment_id)
    if not row:
        return _wrap_error(f"实验不存在: {experiment_id}", 404)
    results = experiment_persistence.get_xrd_results(experiment_id)
    return _wrap_success("获取实验详情成功", {"experiment": row, "xrd_results": results})


@router.post("/confirm_seal", tags=["实验"])
def confirm_flux_seal():
    """人工或 Agent 确认熔封已完成，流程将继续到「等待加热炉上料」阶段。"""
    experiment_orchestrator.confirm_seal()
    return _wrap_success("熔封确认已接收，流程继续", None)


@router.post("/confirm_thermal_load", tags=["实验"])
def confirm_thermal_load(req: Optional[ThermalParamsRequest] = None):
    """
    确认样品已放入加热炉，并可选传入热处理参数（炉号、数量、曲线名或曲线点、多炉分配）。
    若传 oven_assignments，则按炉按 scheme_index 取各方案温度曲线执行；否则单炉沿用 oven_id/qty/curve_points。
    """
    if req:
        oven_assignments = (
            [a.model_dump() for a in req.oven_assignments]
            if req.oven_assignments else None
        )
        experiment_orchestrator.confirm_thermal_load(
            oven_id=req.oven_id,
            qty=req.qty,
            curve_name=req.curve_name,
            curve_points=req.curve_points,
            oven_assignments=oven_assignments,
        )
    else:
        experiment_orchestrator.confirm_thermal_load()
    return _wrap_success("上料确认已接收，开始热处理", None)


@router.post("/confirm_xrd_ready", tags=["实验"])
def confirm_xrd_ready(req: Optional[XRDParamsRequest] = None):
    """确认样品已放入 XRD 试验台，流程将开始 XRD 测试。"""
    if req:
        experiment_orchestrator.confirm_xrd_ready(
            start_theta=req.start_theta,
            end_theta=req.end_theta,
            increment=req.increment,
            exp_time=req.exp_time,
            scheme_index=req.scheme_index,
        )
    else:
        experiment_orchestrator.confirm_xrd_ready()
    return _wrap_success("XRD上样确认已接收，开始XRD测试", None)


@router.post("/confirm_continue_after_error", tags=["实验"])
def confirm_continue_after_error(resume_phase: Optional[str] = None):
    """
    报错后从下一阶段继续执行。仅当 phase=error 且存在可恢复阶段时有效。
    可选 body 或 query：resume_phase（如 waiting_seal_confirm、waiting_thermal_load、waiting_xrd_ready），
    不传则使用内部记录的恢复阶段。
    """
    out = experiment_orchestrator.confirm_continue_after_error(resume_phase=resume_phase)
    if out.get("status") == "error":
        return _wrap_error(out.get("message", "恢复失败"), 400, out)
    return _wrap_success(out.get("message", "恢复成功"), {"resume_phase": out.get("resume_phase")})


@router.post("/stop", tags=["实验"])
def stop_experiment():
    """
    请求停止当前实验。若实验正在运行或处于某一「等待确认」阶段，将下发停止请求；
    后台线程会在下一轮检查时退出，phase 变为 error，error_message 为「用户停止实验」。
    返回已是否成功发出停止请求（无实验在跑时返回 false）。
    """
    ok = experiment_orchestrator.stop()
    msg = "已请求停止实验" if ok else "当前无实验在运行"
    return _wrap_success(msg, {"stopped": ok})


@router.post("/{experiment_id}/xrd-supplement", tags=["实验"])
def xrd_supplement(experiment_id: str, req: Optional[XRDSupplementRequest] = None):
    """
    实验后 XRD 补充测试：对已完成实验的燃烧后材料再做一次 XRD 测试，结果按 experiment_id、sample_id 关联存储。
    若不传 sample_id 则自动生成并写入 sample_bindings；可传 scheme_id/scheme_index 便于与方案对应。
    """
    exp = experiment_persistence.get_experiment(experiment_id)
    if not exp:
        return _wrap_error(f"实验不存在: {experiment_id}", 404)
    body = req or XRDSupplementRequest()
    sample_id = body.sample_id
    scheme_id = body.scheme_id
    scheme_index = body.scheme_index
    if not sample_id:
        sample_id = f"supplement_{scheme_id or '方案'}_{uuid.uuid4().hex[:8]}"
        try:
            experiment_persistence.insert_sample_binding(
                experiment_id, sample_id, scheme_id=scheme_id, scheme_index=scheme_index
            )
        except Exception as e:
            logger.log(f"补充测试写入 sample_binding 失败: {e}", "WARN")
    start_theta = body.start_theta if body.start_theta is not None else 5.1
    end_theta = body.end_theta if body.end_theta is not None else 120.0
    increment = body.increment if body.increment is not None else 0.01
    exp_time = body.exp_time if body.exp_time is not None else 0.1
    try:
        xrd_result = xrd_flow_mgr.run(
            single=True,
            sample_id=sample_id,
            start_theta=float(start_theta),
            end_theta=float(end_theta),
            increment=float(increment),
            exp_time=float(exp_time),
        )
    except Exception as e:
        return _wrap_error(f"XRD 执行失败: {e}", 500)
    if not xrd_result.get("status"):
        return _wrap_error(xrd_result.get("message", "XRD 测试未成功完成"), 502)
    latest = xrd_flow_mgr.get_latest_data()
    if isinstance(latest, dict) and latest.get("status") and latest.get("data"):
        d = latest.get("data", {})
        to_persist = [{
            "sample_id": sample_id,
            "scheme_id": scheme_id,
            "scheme_index": scheme_index,
            "scheme_type": "",
            "theta2": d.get("theta2"),
            "intensity": d.get("intensity"),
            "timestamp": d.get("timestamp"),
        }]
        try:
            experiment_persistence.insert_xrd_results(experiment_id, to_persist)
        except Exception as e:
            logger.log(f"补充测试 XRD 结果持久化失败: {e}", "WARN")
    return _wrap_success(
        "XRD 补充测试完成，结果已按 experiment_id/sample_id 关联存储",
        {"status": True, "sample_id": sample_id},
    )
