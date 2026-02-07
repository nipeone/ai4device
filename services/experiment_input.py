"""
从大模型规范输出（实验输入）提取配料任务与加热炉温度曲线。
根据 配料总总量 与 原料摩尔比_标准化 计算各原料 add_weight（添加重量）。
"""
import re
from datetime import datetime
from typing import List, Tuple
import uuid

from schemas.llm_output import StartExperimentRequest, TemperatureProgram, ProcessRecipe
from schemas.mixer import AddTaskRequest, TaskSetup, LayoutListItem, ProcessJson, GetChemicalsResponse, ChemicalData, ChemicalListItem
from schemas.oven import CurvePoint
from devices.mixer_core import mixer_controller


def _parse_ratio_string(ratio_str: str) -> List[float]:
    """
    解析 原料摩尔比_标准化 字符串为相对比例列表。
    支持格式示例："RE:Mn:Si = 0.5-1.5:1:1"、"1:1:1"、"0.5-1.5:1.0:1.0"。
    区间取中点，如 0.5-1.5 -> 1.0。
    """
    if not (ratio_str and ratio_str.strip()):
        return []
    s = ratio_str.strip()
    if "=" in s:
        s = s.split("=", 1)[1].strip()
    parts = re.split(r"\s*:\s*", s)
    out: List[float] = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        if "-" in p and not p.startswith("-"):
            # 区间，取中点
            try:
                low, high = p.split("-", 1)
                low, high = float(low.strip()), float(high.strip())
                out.append((low + high) / 2.0)
            except (ValueError, TypeError):
                out.append(1.0)
        else:
            try:
                out.append(float(p))
            except (ValueError, TypeError):
                out.append(1.0)
    return out


def _ratios_to_weights(
    n_ingredients: int,
    ratios: List[float],
    total_weight: float,
) -> List[float]:
    """
    将比例列表按原料数量展开并归一化为总质量 total_weight（克）。
    - 若 len(ratios) == n_ingredients：直接按比例分配。
    - 若 len(ratios) < n_ingredients：将第一个比例均分给前 (n_ingredients - len(ratios) + 1) 个原料，其余一一对应。
    - 若 len(ratios) > n_ingredients：取前 n_ingredients 个比例。
    - 若无比例：均分 total_weight。
    """
    if total_weight <= 0:
        return [0.0] * n_ingredients
    if not ratios:
        w = total_weight / n_ingredients if n_ingredients else 0.0
        return [w] * n_ingredients
    n_r = len(ratios)
    if n_r >= n_ingredients:
        r = ratios[:n_ingredients]
    elif n_r < n_ingredients:
        # 第一个比例拆给前 k 个原料，k = n_ingredients - n_r + 1
        k = n_ingredients - n_r + 1
        r = [ratios[0] / k] * k + list(ratios[1:])
    else:
        r = ratios
    total_r = sum(r)
    if total_r <= 0:
        w = total_weight / n_ingredients if n_ingredients else 0.0
        return [w] * n_ingredients
    return [total_weight * (ri / total_r) for ri in r]


def llm_output_to_task_name(req: StartExperimentRequest) -> str:
    """从 LLM 输出生成配料任务名称"""
    if req.配方ID:
        return f"{req.配方ID}_{datetime.now().strftime('%Y%m%d%H%M')}_{str(uuid.uuid4())[:8]}"
    if req.实验目的:
        short = (req.实验目的[:20] + "..") if len(req.实验目的 or "") > 20 else (req.实验目的 or "")
        return f"{short}_{datetime.now().strftime('%Y%m%d%H%M')}"
    return f"exp_{datetime.now().strftime('%Y%m%d%H%M')}_{str(uuid.uuid4())[:8]}"


def llm_output_to_add_task_request(req: StartExperimentRequest, check_chemical: bool = False) -> AddTaskRequest:
    """
    从大模型规范输出提取原料，生成 AddTaskRequest（配料任务）。
    原料为逗号分隔的物质名（如 "Y, Er, Mn, Si"），每个物质一个 LayoutListItem；
    各原料 add_weight 由 配料总总量（默认 5g）与 原料摩尔比_标准化 按比例计算得出。
    """
    task_name = llm_output_to_task_name(req)
    recipe: ProcessRecipe = req.工艺配方
    layout_list: List[LayoutListItem] = []

    total_weight = recipe.配料总总量 if recipe.配料总总量 and recipe.配料总总量 > 0 else 5.0

    chemical_list: List[ChemicalListItem] = []
    if check_chemical:
        chemicals = mixer_controller.get_chemicals()
        if chemicals["status"] != "success":
            raise ValueError(f"获取化学品信息失败: {chemicals['message']}")
        chemical_list = chemicals["data"].data.chemical_list

    # 检查化学品是否存在
    def check_chemical_exists(chemical_name: str) -> Tuple[bool, int, str]:
        for chemical in chemical_list:
            if chemical.name == chemical_name:
                return True, chemical.fid, chemical.sssi
        return False, 0, ""

    ingredients_str = (recipe.原料 or "").strip()
    if ingredients_str:
        substances = [s.strip() for s in ingredients_str.split(",") if s.strip()]
        ratios = _parse_ratio_string(recipe.原料摩尔比_标准化 or "")
        weights = _ratios_to_weights(len(substances), ratios, total_weight)

        for idx, substance in enumerate(substances):
            if check_chemical:
                exists, chemical_id, sssi = check_chemical_exists(substance)
                if not exists:
                    # add_chemical_response = mixer_controller.add_chemical(substance)
                    # if add_chemical_response["status"] != "success":
                    #     raise ValueError(f"添加化学品 {substance} 失败: {add_chemical_response["message"]}")
                    raise ValueError(f"化学品 {substance} 不存在，请先添加化学品")
            add_weight = weights[idx] if idx < len(weights) else 0.0
            process_json = ProcessJson(
                resource_type="CC10R10C",
                substance=substance,
                add_weight=round(add_weight, 4),
                offset=0.0,
            )
            if check_chemical:
                process_json.chemical_id = chemical_id
                process_json.SSSI = sssi
            layout_item = LayoutListItem(
                layout_code="",
                src_layout_code="",
                resource_type="CC10R10C",
                tray_QR_code="",
                status=0,
                QR_code="",
                unit_type="exp_add_powder",
                unit_column=0,
                unit_row=0,
                unit_id=f"unit-{str(uuid.uuid4())[:8]}",
                process_json=process_json,
            )
            layout_list.append(layout_item)

    if not layout_list:
        layout_list.append(
            LayoutListItem(
                unit_id="placeholder",
                process_json=ProcessJson(substance=ingredients_str or "未指定", add_weight=0.0),
            )
        )

    return AddTaskRequest(
        task_name=task_name,
        layout_list=layout_list
    )


def llm_output_to_curve_points(req: StartExperimentRequest) -> List[CurvePoint]:
    """
    从大模型规范输出的温度程序生成加热炉曲线 List[CurvePoint]。
    时间单位：小时（与现有炉控一致）；温度单位：摄氏度。
    曲线段：升温到最高温 -> 最高温保温 -> 主降温；最后一点用 time=-121 表示结束（与 thermal_flow 约定一致）。
    """
    tp: TemperatureProgram = req.温度程序
    ramp_h = tp.升温到最高温时间_h or 0.0
    T_high = tp.最高温段保温温度_摄氏 or 0.0
    hold_h = tp.最高温段保温时间_h or 0.0
    cool_rate = tp.降温速率_主降温_摄氏度每小时 or 0.0
    cool_h = tp.降温时间_主降温_h or 0.0

    ramp_min = ramp_h
    hold_min = hold_h
    cool_min = cool_h
    T_drop = cool_rate * cool_h
    T_end = max(0.0, T_high - T_drop)

    points: List[CurvePoint] = []

    # 升温结束点 (ramp_min, T_high)
    if ramp_min > 0 and T_high > 0:
        points.append(CurvePoint(temperature=T_high, time=ramp_min))

    # 保温结束点 (ramp_min + hold_min, T_high)
    if hold_min > 0:
        points.append(CurvePoint(temperature=T_high, time=ramp_min + hold_min))

    # 主降温结束点 (ramp_min + hold_min + cool_min, T_end)
    if cool_min > 0:
        points.append(
            CurvePoint(
                temperature=T_end,
                time=ramp_min + hold_min + cool_min,
            )
        )

    if not points:
        points = [
            CurvePoint(temperature=100.0, time=1.0),
            CurvePoint(temperature=-121.0, time=0.0),
        ]
    else:
        # 结束标记：time=-121（thermal_flow 约定）
        points.append(CurvePoint(temperature=-121.0, time=0.0))

    return points


def llm_output_to_experiment_input(
    req: StartExperimentRequest,
    oven_id: int = 1,
    qty: int = 1,
) -> Tuple[AddTaskRequest, List[CurvePoint], int, int]:
    """
    从 StartExperimentRequest 一次性解析出配料任务、温度曲线与炉子参数。
    返回 (AddTaskRequest, curve_points, oven_id, qty)。
    """
    add_task = llm_output_to_add_task_request(req)
    curve_points = llm_output_to_curve_points(req)
    return add_task, curve_points, oven_id, qty
