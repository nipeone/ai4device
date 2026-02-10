"""
从大模型规范输出（实验输入）提取配料任务与加热炉温度曲线。

输入结构（与 data/llm_output.json 一致）：
- 目标材料：化学式等
- 推荐实验方案列表：[ { 方案ID, 工艺参数: { 原料信息, 原料标准化, 温度程序 }, ... }, ... ]
- 方案索引：选用第几个方案（默认 0）

根据 配料总总量（默认 5g）与 原料标准化 计算各原料 add_weight。
大模型输出为摩尔比，需转换为质量比后下发给配料设备。
"""
import re
from datetime import datetime
from typing import List, Tuple, Optional
import uuid

from schemas.llm_output import (
    StartExperimentRequest,
    RecommendExperimentScheme,
    TemperatureProgram,
    ProcessRecipe,
)
from schemas.mixer import AddTaskRequest, LayoutListItem, ProcessJson, ChemicalListItem
from schemas.oven import CurvePoint
from devices.mixer_core import mixer_controller


# 元素符号 -> 摩尔质量 (g/mol)，用于摩尔比 -> 质量比转换（标准原子量，常见值）
ATOMIC_MASS: dict = {
    "H": 1.008, "He": 4.003, "Li": 6.94, "Be": 9.012, "B": 10.81, "C": 12.011,
    "N": 14.007, "O": 15.999, "F": 19.00, "Ne": 20.18, "Na": 22.99, "Mg": 24.31,
    "Al": 26.98, "Si": 28.09, "P": 30.97, "S": 32.06, "Cl": 35.45, "Ar": 39.95,
    "K": 39.10, "Ca": 40.08, "Sc": 44.96, "Ti": 47.87, "V": 50.94, "Cr": 52.00,
    "Mn": 54.94, "Fe": 55.85, "Co": 58.93, "Ni": 58.69, "Cu": 63.55, "Zn": 65.38,
    "Ga": 69.72, "Ge": 72.63, "As": 74.92, "Se": 78.97, "Br": 79.90, "Kr": 83.80,
    "Rb": 85.47, "Sr": 87.62, "Y": 88.91, "Zr": 91.22, "Nb": 92.91, "Mo": 95.95,
    "Tc": 98.0, "Ru": 101.1, "Rh": 102.9, "Pd": 106.4, "Ag": 107.9, "Cd": 112.4,
    "In": 114.8, "Sn": 118.71, "Sb": 121.76, "Te": 127.60, "I": 126.90, "Xe": 131.29,
    "Cs": 132.91, "Ba": 137.33, "La": 138.91, "Ce": 140.12, "Pr": 140.91, "Nd": 144.24,
    "Pm": 145.0, "Sm": 150.36, "Eu": 151.96, "Gd": 157.25, "Tb": 158.93, "Dy": 162.50,
    "Ho": 164.93, "Er": 167.26, "Tm": 168.93, "Yb": 173.05, "Lu": 174.97,
    "Hf": 178.49, "Ta": 180.95, "W": 183.84, "Re": 186.21, "Os": 190.23, "Ir": 192.22,
    "Pt": 195.08, "Au": 196.97, "Hg": 200.59, "Tl": 204.38, "Pb": 207.2, "Bi": 208.98,
    "Po": 209.0, "At": 210.0, "Rn": 222.0,
}


def get_molar_mass(substance: str) -> float:
    """
    根据物质名称/化学式返回摩尔质量 (g/mol)。
    - 单元素：支持符号（如 Al, Se, In），不区分大小写首字母大写匹配。
    - 简单化学式：形如 XnYm（如 Al2O3, NaCl），按元素与下标解析后求和；未识别时返回 0。
    """
    s = (substance or "").strip()
    if not s:
        return 0.0
    # 单元素：首字母大写、其余小写
    one = s[0].upper() + (s[1:].lower() if len(s) > 1 else "")
    if one in ATOMIC_MASS:
        return float(ATOMIC_MASS[one])
    # 简单化学式：去空格后匹配 大写字母+可选小写+可选数字
    s = re.sub(r"\s+", "", s)
    pattern = re.compile(r"([A-Z][a-z]?)(\d*)")
    total = 0.0
    pos = 0
    while pos < len(s):
        m = pattern.match(s, pos)
        if not m:
            pos += 1
            continue
        elem, num = m.group(1), m.group(2) or "1"
        n = int(num) if num else 1
        total += ATOMIC_MASS.get(elem, 0.0) * n
        pos = m.end()
    return total if total > 0 else 0.0


def molar_ratios_to_mass_weights(
    substances: List[str],
    molar_ratios: List[float],
    total_weight: float,
) -> List[float]:
    """
    将摩尔比转换为各原料质量（克），并归一化到总质量 total_weight。
    质量_i = (摩尔比_i × 摩尔质量_i) / Σ(摩尔比_j × 摩尔质量_j) × total_weight。
    若某物质摩尔质量未知（0），则按原比例均分该部分质量（与 _ratios_to_weights 行为一致）。
    """
    n = len(substances)
    if n == 0 or total_weight <= 0:
        return []
    if not molar_ratios or len(molar_ratios) < n:
        # 缺省按均分
        return [total_weight / n] * n

    ratios = molar_ratios[:n]
    masses = []
    unknown_idx: List[int] = []
    known_sum = 0.0

    for i in range(n):
        M = get_molar_mass(substances[i])
        if M <= 0:
            unknown_idx.append(i)
            masses.append(0.0)
        else:
            m = ratios[i] * M
            masses.append(m)
            known_sum += m

    if unknown_idx:
        # 有未知摩尔质量：已知部分按比例归一化，未知部分均分剩余质量
        if known_sum > 0:
            scale = total_weight / known_sum
            for i in range(n):
                if i not in unknown_idx:
                    masses[i] *= scale
            remaining = total_weight - sum(masses)
            per_unknown = remaining / len(unknown_idx) if unknown_idx else 0.0
            for i in unknown_idx:
                masses[i] = per_unknown
        else:
            return _ratios_to_weights(n, ratios, total_weight)
    else:
        total_m = sum(masses)
        if total_m > 0:
            scale = total_weight / total_m
            masses = [m * scale for m in masses]

    return masses


def get_selected_scheme(req: StartExperimentRequest) -> RecommendExperimentScheme:
    """
    从请求中取当前选中的实验方案（按 方案索引）。
    若列表为空或索引越界，抛出 ValueError。
    """
    schemes = req.推荐实验方案列表 or []
    if not schemes:
        raise ValueError("推荐实验方案列表为空，无法启动实验")
    idx = req.方案索引 if req.方案索引 is not None else 0
    if idx < 0 or idx >= len(schemes):
        raise ValueError(f"方案索引 {idx} 越界，当前共有 {len(schemes)} 个方案")
    return schemes[idx]


def _parse_ratio_string(ratio_str: str) -> List[float]:
    """
    解析 原料标准化 字符串为相对比例列表。
    支持格式示例："Al:In:Se=1:1:3"、"1:1:1"、"0.5-1.5:1.0:1.0"。
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


def _parse_ingredients_from_info(原料信息: str) -> List[str]:
    """
    从 原料信息 解析出物质名列表。
    示例："Al, In, Se (按化学计量比 1:1:3)" -> ["Al", "In", "Se"]
    """
    if not (原料信息 and 原料信息.strip()):
        return []
    # 去掉括号及括号后内容，再按逗号分割
    s = 原料信息.strip()
    if "(" in s:
        s = s.split("(")[0].strip()
    return [x.strip() for x in s.split(",") if x.strip()]


def _ratios_to_weights(
    n_ingredients: int,
    ratios: List[float],
    total_weight: float,
) -> List[float]:
    """
    将比例列表按原料数量展开并归一化为总质量 total_weight（克）。
    """
    if total_weight <= 0:
        return [0.0] * n_ingredients
    if not ratios:
        w = total_weight / n_ingredients if n_ingredients else 0.0
        return [w] * n_ingredients
    n_r = len(ratios)
    if n_r >= n_ingredients:
        r = ratios[:n_ingredients]
    else:
        k = n_ingredients - n_r + 1
        r = [ratios[0] / k] * k + list(ratios[1:])
    total_r = sum(r)
    if total_r <= 0:
        w = total_weight / n_ingredients if n_ingredients else 0.0
        return [w] * n_ingredients
    return [total_weight * (ri / total_r) for ri in r]


# 默认配料总总量（克），新结构无该字段时使用
DEFAULT_TOTAL_WEIGHT = 5.0


def llm_output_to_task_name(req: StartExperimentRequest) -> str:
    """从 LLM 输出生成配料任务名称：目标材料化学式_方案ID_时间戳"""
    scheme = get_selected_scheme(req)
    formula = ""
    if req.目标材料 and getattr(req.目标材料, "化学式", None):
        formula = (req.目标材料.化学式 or "").strip()
    scheme_id = (scheme.方案ID or "").strip() or "方案0"
    ts = datetime.now().strftime("%Y%m%d%H%M")
    uid = str(uuid.uuid4())[:8]
    if formula:
        return f"{formula}_{scheme_id}_{ts}_{uid}"
    return f"{scheme_id}_{ts}_{uid}"


def llm_output_to_add_task_request(
    req: StartExperimentRequest,
    check_chemical: bool = False,
    total_weight: float = DEFAULT_TOTAL_WEIGHT,
) -> AddTaskRequest:
    """
    从大模型规范输出提取原料，生成 AddTaskRequest。
    使用选中方案的 工艺参数.原料信息、工艺参数.原料标准化；
    配料总总量 使用 total_weight（默认 5g），按比例计算各原料 add_weight。
    """
    scheme = get_selected_scheme(req)
    recipe: Optional[ProcessRecipe] = scheme.工艺参数
    if not recipe:
        raise ValueError("选中方案的工艺参数为空，无法生成配料任务")

    task_name = llm_output_to_task_name(req)
    layout_list: List[LayoutListItem] = []

    ingredients_str = (recipe.原料信息 or "").strip()
    ratio_str = (recipe.原料标准化 or "").strip()
    substances = _parse_ingredients_from_info(ingredients_str)
    molar_ratios = _parse_ratio_string(ratio_str)
    # 大模型输出为摩尔比，转换为质量比后下发给配料设备
    weights = molar_ratios_to_mass_weights(substances, molar_ratios, total_weight)

    chemical_list: List[ChemicalListItem] = []
    if check_chemical:
        chemicals = mixer_controller.get_chemicals()
        if chemicals.get("status") != "success":
            raise ValueError(f"获取化学品信息失败: {chemicals.get('message', '')}")
        data = chemicals.get("data")
        if data and getattr(data, "data", None) and getattr(data.data, "chemical_list", None):
            chemical_list = data.data.chemical_list

    def check_chemical_exists(chemical_name: str) -> Tuple[bool, int, str]:
        for chemical in chemical_list:
            if getattr(chemical, "name", None) == chemical_name:
                return True, getattr(chemical, "fid", 0), getattr(chemical, "sssi", "")
        return False, 0, ""

    for idx, substance in enumerate(substances):
        if check_chemical:
            exists, chemical_id, sssi = check_chemical_exists(substance)
            if not exists:
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
        layout_item = LayoutListItem(
            unit_id="placeholder",
            process_json=ProcessJson(substance=ingredients_str or "未指定", add_weight=0.0),
        )
        layout_list.append(layout_item)

    return AddTaskRequest(
        task_name=task_name,
        layout_list=layout_list,
    )


def llm_output_to_curve_points(req: StartExperimentRequest) -> List[CurvePoint]:
    """
    从选中方案的 工艺参数.温度程序 生成加热炉曲线 List[CurvePoint]。
    时间单位：小时；温度单位：摄氏度。
    曲线段：升温到最高温 -> 最高温保温 -> 主降温；最后一点 time=-121 表示结束。
    """
    scheme = get_selected_scheme(req)
    recipe = scheme.工艺参数
    if not recipe or not recipe.温度程序:
        return [
            CurvePoint(temperature=100.0, time=1.0),
            CurvePoint(temperature=-121.0, time=0.0),
        ]

    tp: TemperatureProgram = recipe.温度程序
    ramp_h = tp.升温到最高温时间_h or 0.0
    T_high = tp.最高温段保温温度_摄氏 or 0.0
    hold_h = tp.最高温段保温时间_h or 0.0
    cool_rate = getattr(tp, "降温速率_主降温_摄氏度每小时", None) or 0.0
    cool_h = tp.降温时间_主降温_h or 0.0

    ramp_min = ramp_h
    hold_min = hold_h
    cool_min = cool_h
    T_drop = cool_rate * cool_h
    T_end = max(0.0, T_high - T_drop)

    points: List[CurvePoint] = []

    if ramp_min > 0 and T_high > 0:
        points.append(CurvePoint(temperature=T_high, time=ramp_min))
    if hold_min > 0:
        points.append(CurvePoint(temperature=T_high, time=ramp_min + hold_min))
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
        points.append(CurvePoint(temperature=-121.0, time=0.0))

    return points


def llm_output_to_experiment_input(
    req: StartExperimentRequest,
    oven_id: int = 1,
    qty: int = 1,
    total_weight: float = DEFAULT_TOTAL_WEIGHT,
) -> Tuple[AddTaskRequest, List[CurvePoint], int, int]:
    """
    从 StartExperimentRequest 解析出配料任务、温度曲线与炉子参数。
    返回 (AddTaskRequest, curve_points, oven_id, qty)。
    """
    add_task = llm_output_to_add_task_request(req, total_weight=total_weight)
    curve_points = llm_output_to_curve_points(req)
    return add_task, curve_points, oven_id, qty
