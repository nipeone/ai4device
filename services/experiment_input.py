"""
从大模型规范输出（实验输入）提取配料任务与加热炉温度曲线。

输入结构（与 data/llm_output.json 一致）：
- 目标材料：化学式等
- 推荐实验方案列表：[ { 方案ID, 工艺参数: { 原料信息, 原料标准化, 温度程序 }, ... }, ... ]
- 推荐实验方案列表 顺序即试管/配方序号（0,1,2,...），配料、加热、XRD 均按此序号对应

根据 配料总总量（默认 5g）与 原料标准化 计算各原料质量；下发给配料机时 add_weight 为毫克（mg）。
大模型输出为摩尔比，需转换为质量比后下发给配料设备。
"""
import re
from datetime import datetime
from typing import List, Tuple, Optional
import uuid

from schemas.llm_output import (
    RecommendExperimentRecipes,
    RecommendExperimentScheme,
    TemperatureProgram,
    ProcessRecipe,
)
from schemas.mixer import AddTaskRequest, LayoutListItem, ProcessJson, ChemicalListItem, TaskSetup
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


def get_selected_scheme(req: RecommendExperimentRecipes) -> RecommendExperimentScheme:
    """
    从请求中取第一个实验方案（用于温度曲线等单方案逻辑）。列表为空时抛出 ValueError。
    """
    schemes = req.recommend_schemes or []
    if not schemes:
        raise ValueError("推荐实验方案列表为空，无法启动实验")
    return schemes[0]

def get_schemes(req: RecommendExperimentRecipes) -> List[RecommendExperimentScheme]:
    """
    从请求中取所有实验方案（用于配料任务）。列表为空时抛出 ValueError。
    """
    schemes = req.recommend_schemes or []
    if not schemes:
        raise ValueError("推荐实验方案列表为空，无法启动实验")
    return schemes

def get_scheme_manifest(req: RecommendExperimentRecipes) -> List[dict]:
    """
    按 推荐实验方案列表 顺序生成试管配方清单，供加热/XRD 与序号对应。
    返回列表每项为 {"scheme_index": int, "scheme_id": str, "scheme_type": str}，长度 = len(推荐实验方案列表)。
    """
    schemes = req.recommend_schemes or []
    if not schemes:
        raise ValueError("推荐实验方案列表为空，无法启动实验")
    return [
        {
            "scheme_index": i,
            "scheme_id": s.scheme_id or f"方案{i}",
            "scheme_type": s.scheme_type or "",
        }
        for i, s in enumerate(schemes)
    ]


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


def _parse_ingredients_from_info(raw_material_info: str) -> List[str]:
    """
    从 raw_material_info 解析出物质名列表。
    示例："Al, In, Se (按化学计量比 1:1:3)" -> ["Al", "In", "Se"]
    """
    if not (raw_material_info and raw_material_info.strip()):
        return []
    # 去掉括号及括号后内容，再按逗号分割
    s = raw_material_info.strip()
    if "(" in s:
        s = s.split("(")[0].strip()
    return [x.strip() for x in s.split(",") if x.strip()]


def _parse_flux_ratio(flux_standardization: str) -> Optional[Tuple[str, float, float]]:
    """
    解析 flux_standardization(助熔剂标准化) 字符串，得到「助熔剂名: 助熔剂比例 : 原料总量比例」。
    示例："Na:(Al+In+Se)=2.7:1" -> ("Na", 2.7, 1.0)；助熔剂与全部原料的摩尔比 2.7:1。
    返回 (flux_name, flux_ratio, main_ratio)，无法解析时返回 None。
    """
    if not (flux_standardization and flux_standardization.strip()):
        return None
    s = flux_standardization.strip()
    if "=" not in s:
        return None
    left, right = s.split("=", 1)
    left, right = left.strip(), right.strip()
    # 右侧 "2.7:1" 或 "10.0:1"
    parts = re.split(r"\s*:\s*", right)
    if len(parts) < 2:
        return None
    try:
        flux_ratio = float(parts[0].strip())
        main_ratio = float(parts[1].strip())
    except (ValueError, TypeError):
        return None
    if main_ratio <= 0:
        return None
    # 左侧 "Na:(Al+In+Se)"，取冒号前为助熔剂名
    flux_name = left.split(":")[0].strip() if ":" in left else left.strip()
    if not flux_name:
        return None
    return (flux_name, flux_ratio, main_ratio)


def _parse_flux_from_info(flux_info: str) -> Optional[str]:
    """
    从 flux_info(助熔剂信息) 解析出助熔剂物质名（用于与 flux_standardization(助熔剂标准化) 中的名称对应或兜底）。
    示例："Na 助熔剂" -> "Na"，"NaCl-KCl 混合助熔剂" -> "NaCl-KCl"。
    """
    if not (flux_info and flux_info.strip()):
        return None
    s = flux_info.strip()
    # 去掉「助熔剂」及其后括号内容
    for sep in ["助熔剂", "助溶剂"]:
        if sep in s:
            s = s.split(sep)[0].strip()
    if "(" in s:
        s = s.split("(")[0].strip()
    s = s.strip()
    return s if s else None


def _normalize_substance_for_compare(name: str) -> str:
    """物质名规范化后用于比较（自助熔剂与原料是否同种）：去空格、首字母大写其余小写（便于 In/in 一致）。"""
    if not name:
        return ""
    s = name.strip()
    if len(s) <= 2:
        return s[0].upper() + (s[1:].lower() if len(s) > 1 else "")
    return s


def _main_and_flux_weights(
    main_substances: List[str],
    molar_ratios: List[float],
    total_weight_g: float,
    flux_name: Optional[str],
    flux_ratio: float,
    main_ratio: float,
) -> Tuple[List[float], float]:
    """
    在「原料 + 助熔剂 = total_weight_g（克）」约束下，按原料摩尔比与助熔剂:原料摩尔比分配质量。
    返回 (原料各物质质量列表, 助熔剂质量克)。无助熔剂时 flux_ratio/main_ratio 视为 0，助熔剂质量=0。
    """
    n = len(main_substances)
    if n == 0 or total_weight_g <= 0:
        return [], 0.0
    ratios = molar_ratios[:n] if molar_ratios else []
    if not ratios:
        return [total_weight_g / n] * n, 0.0

    # 原料摩尔质量与 r_i*M_i
    S_main = 0.0  # sum(r_i * M_i)
    sum_r = 0.0
    for i in range(n):
        M = get_molar_mass(main_substances[i])
        r = ratios[i] if i < len(ratios) else 1.0
        sum_r += r
        S_main += r * M if M > 0 else 0.0

    M_flux = get_molar_mass(flux_name) if flux_name else 0.0
    flux_part = 0.0
    if flux_name and M_flux > 0 and main_ratio > 0 and flux_ratio >= 0:
        flux_part = sum_r * (flux_ratio / main_ratio) * M_flux

    denom = S_main + flux_part
    if denom <= 0:
        return [total_weight_g / n] * n, 0.0

    R = total_weight_g / denom
    main_weights = []
    for i in range(n):
        M = get_molar_mass(main_substances[i])
        r = ratios[i] if i < len(ratios) else 1.0
        main_weights.append(R * r * M if M > 0 else 0.0)
    flux_mass_g = total_weight_g - sum(main_weights)
    if flux_mass_g < 0:
        flux_mass_g = 0.0
    return main_weights, flux_mass_g


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


# 默认配料总总量（克），用于按比例计算；下发给配料机时转换为 mg
DEFAULT_TOTAL_WEIGHT = 5.0
# 配料机 add_weight 单位为毫克（mg）
G_PER_MG = 1000.0


def llm_output_to_task_name(req: RecommendExperimentRecipes) -> str:
    """从 LLM 输出生成配料任务名称：目标材料化学式_方案ID_时间戳（单方案）或多方案_时间戳"""
    scheme = get_selected_scheme(req)
    formula = ""
    if req.target_material and getattr(req.target_material, "chemical_formula", None):
        formula = (req.target_material.chemical_formula or "").strip()
    scheme_id = (scheme.scheme_id or "").strip() or "方案0"
    ts = datetime.now().strftime("%Y%m%d%H%M")
    uid = str(uuid.uuid4())[:8]
    if formula:
        return f"{formula}_{scheme_id}_{ts}_{uid}"
    return f"{scheme_id}_{ts}_{uid}"


def _get_schemes_for_layout(req: RecommendExperimentRecipes) -> List[RecommendExperimentScheme]:
    """
    参与配料任务的方案列表 = 推荐实验方案列表 全部按顺序（每列一个配方，与试管序号一致）。
    """
    schemes = req.recommend_schemes or []
    if not schemes:
        raise ValueError("推荐实验方案列表为空，无法生成配料任务")
    return list(schemes)


def llm_output_to_add_task_request(
    req: RecommendExperimentRecipes,
    check_chemical: bool = False,
    total_weight: float = DEFAULT_TOTAL_WEIGHT,
) -> AddTaskRequest:
    """
    从大模型规范输出生成配料机可识别的 AddTaskRequest。

    配料机 layout_list 约定：一种配方占一列（unit_column），列内每种原料占一行（unit_row）。
    - 推荐实验方案列表 中的每个方案 → 一列（unit_column=0,1,2,...）；
    - 每个方案内的 工艺参数.原料信息、原料标准化 解析为多种物质 → 该列内 unit_row=0,1,2,...；
    - 工艺参数.助熔剂信息、助熔剂标准化 解析助熔剂与原料总量的比值（如 Na:(Al+In+Se)=2.7:1）；原料与助熔剂共同满足「原料总质量 + 助熔剂质量 = total_weight（默认 5g）」；
    - 摩尔比转为质量时内部用克（g），total_weight 为克；写入 layout 的 add_weight 转为毫克（mg）供配料机使用。

    配料列顺序、试管顺序、加热/XRD 序号均与 推荐实验方案列表 顺序一致。
    """
    schemes = _get_schemes_for_layout(req)
    formula = ""
    if req.target_material and getattr(req.target_material, "chemical_formula", None):
        formula = (req.target_material.chemical_formula or "").strip()
    ts = datetime.now().strftime("%Y%m%d%H%M")
    uid = str(uuid.uuid4())[:8]
    task_name = f"{formula}_多方案_{ts}_{uid}" if len(schemes) > 1 else llm_output_to_task_name(req)

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

    layout_list: List[LayoutListItem] = []
    unit_id_base = int(datetime.now().timestamp()*1000)
    for col_idx, scheme in enumerate(schemes):
        recipe: Optional[ProcessRecipe] = scheme.process_recipe
        if not recipe:
            raise ValueError(f"方案 col={col_idx} 的工艺参数为空")
        ingredients_str = (recipe.raw_material_info or "").strip()
        ratio_str = (recipe.raw_material_standardization or "").strip()
        substances = _parse_ingredients_from_info(ingredients_str)
        molar_ratios = _parse_ratio_string(ratio_str)

        flux_ratio_tuple = _parse_flux_ratio((recipe.flux_standardization or "").strip())
        flux_name_from_info = _parse_flux_from_info((recipe.flux_info or "").strip())
        if flux_ratio_tuple:
            flux_name, flux_ratio, main_ratio = flux_ratio_tuple
            flux_substance = flux_name or flux_name_from_info or "助熔剂"
            weights, flux_mass_g = _main_and_flux_weights(
                substances, molar_ratios, total_weight,
                flux_substance, flux_ratio, main_ratio,
            )
        else:
            flux_substance = None
            flux_mass_g = 0.0
            weights = molar_ratios_to_mass_weights(substances, molar_ratios, total_weight)

        # 自助熔剂：助熔剂与某原料为同种物质时合并为一行，不再单独追加
        flux_merge_idx: Optional[int] = None
        if flux_substance and flux_mass_g > 0:
            fn = _normalize_substance_for_compare(flux_substance)
            for i, s in enumerate(substances):
                if _normalize_substance_for_compare(s) == fn:
                    flux_merge_idx = i
                    break

        for row_idx, substance in enumerate(substances):
            if check_chemical:
                exists, chemical_id, sssi = check_chemical_exists(substance)
                if not exists:
                    raise ValueError(f"化学品 {substance} 不存在，请先添加化学品")
            add_weight_g = weights[row_idx] if row_idx < len(weights) else 0.0
            if row_idx == flux_merge_idx:
                add_weight_g += flux_mass_g
            add_weight_mg = round(add_weight_g * G_PER_MG, 2)
            process_json = ProcessJson(**{
                    # "resource_type": "CC10R10C",
                    "substance": substance,
                    # "chemical_id": chemical_id,
                    "add_weight": float(add_weight_mg),
                    "offset": 0.3,
                    "custom": {"unit": "mg","unitOptions": ["mg", "g"]}
                })
            if check_chemical:
                process_json.chemical_id = chemical_id
                # process_json.SSSI = sssi
            layout_item = LayoutListItem(
                layout_code="",
                src_layout_code="",
                resource_type="CC10R10C",
                tray_QR_code="",
                status=0,
                QR_code="",
                unit_type="exp_add_powder",
                unit_column=col_idx,
                unit_row=row_idx,
                unit_id=f"unit-{hex(unit_id_base+col_idx)[2:]}",
                process_json=process_json,
            )
            layout_list.append(layout_item)

        # 助熔剂：若未与原料合并（非自助熔剂），则追加一行
        if flux_substance is not None and flux_mass_g > 0 and flux_merge_idx is None:
                if check_chemical:
                    exists, chemical_id, sssi = check_chemical_exists(flux_substance)
                    if not exists:
                        raise ValueError(f"化学品（助熔剂）{flux_substance} 不存在，请先添加化学品")
                flux_mass_mg = round(flux_mass_g * G_PER_MG, 2)
                process_json_flux = ProcessJson(
                    # resource_type="CC10R10C",
                    substance=flux_substance,
                    add_weight=flux_mass_mg,
                    offset=0.0,
                )
                if check_chemical:
                    process_json_flux.chemical_id = chemical_id
                    # process_json_flux.SSSI = sssi
                layout_list.append(
                    LayoutListItem(
                        layout_code="",
                        src_layout_code="",
                        resource_type="CC10R10C",
                        tray_QR_code="",
                        status=0,
                        QR_code="",
                        unit_type="exp_add_powder",
                        unit_column=col_idx,
                        unit_row=len(substances),
                        unit_id=f"unit-{str(uuid.uuid4())[:8]}",
                        process_json=process_json_flux,
                    )
                )

    if not layout_list:
        raise ValueError(f"方案 scheme={task_name} 的布局信息为空")

    task_type = 2
    is_audit_log = 1
    task_setup = TaskSetup(
        subtype=None,
        powder_100_30=True,
        powder_30_100=True,
        added_slots=""
    )

    return AddTaskRequest(
        task_setup=task_setup,
        task_id=0, # 新建任务
        task_name=task_name,
        is_audit_log=is_audit_log,
        type=task_type,
        layout_list=layout_list,
    )


# 室温起点（℃），用于曲线首段“从室温升温到次高温”
ROOM_TEMP_DEFAULT = 20.0


def _temperature_program_to_curve_points(tp: Optional[TemperatureProgram]) -> List[CurvePoint]:
    """
    从单条 温度程序 生成加热炉曲线 List[CurvePoint]。
    语义：每点 (temperature, time) 表示该段温度与段持续时间（小时）。
    """
    if not tp:
        return [
            CurvePoint(temperature=ROOM_TEMP_DEFAULT, time=0.0),
            CurvePoint(temperature=ROOM_TEMP_DEFAULT, time=-121.0),
        ]
    points: List[CurvePoint] = []
    ramp1_hr = float(tp.ramp_to_sub_hight_termperature_time_h or 0.0)
    T1 = float(tp.sub_high_temperature_temperature_celsius or 0.0)
    hold1_hr = float(tp.sub_high_temperature_hold_time_h or 0.0)
    ramp2_hr = float(tp.ramp_to_high_temperature_time_h or 0.0)
    T_high = float(tp.high_temperature_hold_temperature_celsius or 0.0)
    hold2_hr = float(tp.high_temperature_hold_time_h or 0.0)
    cool_hr = float(tp.main_cooling_time_h or 0.0)
    T_low = float(tp.low_temperature_hold_temperature_celsius or 0.0)
    hold3_hr = float(tp.low_temperature_hold_time_h or 0.0)

    points.append(CurvePoint(temperature=ROOM_TEMP_DEFAULT, time=ramp1_hr if ramp1_hr > 0 else 0.0))
    if T1 > 0:
        points.append(CurvePoint(temperature=T1, time=hold1_hr))
    if T_high > 0:
        points.append(CurvePoint(temperature=T1, time=ramp2_hr))
        points.append(CurvePoint(temperature=T_high, time=hold2_hr))
    points.append(CurvePoint(temperature=T_high, time=cool_hr))
    points.append(CurvePoint(temperature=T_low, time=hold3_hr))
    points.append(CurvePoint(temperature=T_low, time=-121.0))
    points = [p for p in points if p.time != 0.0]
    return points


def llm_output_to_curve_points(req: RecommendExperimentRecipes) -> List[CurvePoint]:
    """
    从选中方案（第一个）的 process_recipe.temperature_program 生成加热炉曲线 List[CurvePoint]。
    """
    scheme = get_selected_scheme(req)
    recipe = scheme.process_recipe
    return _temperature_program_to_curve_points(recipe.temperature_program if recipe else None)


def llm_output_to_curve_points_for_scheme_index(
    req: RecommendExperimentRecipes, scheme_index: int
) -> List[CurvePoint]:
    """
    从 recommend_schemes 中指定索引方案的 process_recipe.temperature_program 生成加热炉曲线。
    用于多炉多曲线：每炉对应一方案，按 scheme_index 取该方案曲线。
    """
    schemes = req.recommend_schemes or []
    if not schemes or scheme_index < 0 or scheme_index >= len(schemes):
        return [
            CurvePoint(temperature=ROOM_TEMP_DEFAULT, time=1.0),
            CurvePoint(temperature=ROOM_TEMP_DEFAULT, time=-121.0),
        ]
    scheme = schemes[scheme_index]
    recipe = scheme.process_recipe if scheme else None
    return _temperature_program_to_curve_points(recipe.temperature_program if recipe else None)


def llm_output_to_experiment_input(
    req: RecommendExperimentRecipes,
    oven_id: int = 1,
    qty: int = 1,
    total_weight: float = DEFAULT_TOTAL_WEIGHT,
) -> Tuple[AddTaskRequest, List[CurvePoint], int, int]:
    """
    从 RecommendExperimentRecipes 解析出配料任务、温度曲线与炉子参数。
    返回 (AddTaskRequest, curve_points, oven_id, qty)。
    """
    add_task = llm_output_to_add_task_request(req, total_weight=total_weight)
    curve_points = llm_output_to_curve_points(req)
    return add_task, curve_points, oven_id, qty
