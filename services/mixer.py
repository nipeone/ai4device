import pandas as pd
import io
from typing import Any, List, Tuple
import uuid
from datetime import datetime
import re
from schemas.mixer import AddTaskRequest, TaskSetup, LayoutListItem, ProcessJson

SSSI_SUBSTANCE_MAP = {
    "0-7758-89-6": "CuCl（氯化亚铜）",
    "0-7681-65-4": "CuI（碘化亚铜）",
    "0-7699-45-8": "ZnBr2（溴化锌）",
    "0-30525-89-4": "多聚甲醛",
    "2-00-08-8": "CuCl（氯化亚铜1）",
    "2-00-09-9": "CuCl（氯化亚铜2）",
    "2-00-10-2": "CuCl（氯化亚铜3）",
    "2-00-11-3": "CuCl（氯化亚铜4）",
    "2-00-12-4": "CuCl（氯化亚铜5）",
    "2-00-13-5": "CuCl（氯化亚铜6）",
    "2-00-14-6": "CuCl（氯化亚铜7）",
    "2-00-15-7": "碳酸氢钠",
    "2-00-17-9": "Te",
    "2-00-18-0": "Co",
    "2-00-19-1": "Si",
    "2-00-20-4": "Fe",
    "2-00-21-5": "Ge",
    "2-00-22-6": "Cr",
    "2-00-23-7": "Bi",
    "2-00-25-9": "Sb",
    "2-00-26-0": "Se",
    "2-00-27-1": "Al",
    "2-00-28-2": "In",
    "2-00-29-3": "Na",
    "2-00-30-6": "NaCl",
    "2-00-31-7": "S",
    "2-00-32-8": "Sn",
    "2-00-33-9": "Zn",
    "2-00-34-0": "LiCl"
}

def get_sssi_by_substance(name: str) -> str:
    for sssi, substance in SSSI_SUBSTANCE_MAP.items():
        if name.strip() == substance.strip():
            return sssi
    return ""

# ---------------------------------------------------------------------------
# 逆向：AddTaskRequest -> 配方 Excel 行数据 / Excel 文件（与 parse_mixer_tasks_from_excel 对应）
# ---------------------------------------------------------------------------

def add_task_request_to_recipe_rows(add_task: AddTaskRequest) -> List[List[Tuple[str, float, str]]]:
    """
    将 AddTaskRequest 转为与「配方 Excel」一致的行数据（仅配料表部分）。

    - 每行对应一个配方（unit_column 一组），行内为 (物质显示名, 重量_mg) 的列表。
    - 物质显示名：若有 SSSI 则为 【SSSI】substance，否则为 substance。
    与 parse_mixer_tasks_from_excel 的解析格式互逆，便于再被 parse_mixer_tasks_from_excel 解析。
    """
    from collections import defaultdict
    grouped: dict[int, List[LayoutListItem]] = defaultdict(list)
    for item in add_task.layout_list:
        grouped[item.unit_column].append(item)
    rows: List[List[Tuple[str, float, str]]] = []
    for col in sorted(grouped.keys()):
        items = sorted(grouped[col], key=lambda x: x.unit_row)
        row: List[Tuple[str, float, str]] = []
        for it in items:
            p = it.process_json
            name = (p.substance or "").strip()
            if getattr(p, "SSSI", None) and (p.SSSI or "").strip():
                name = f"【{(p.SSSI or '').strip()}】{name}"
            weight_mg = float(p.add_weight) if p.add_weight is not None else 0.0
            unit = p.custom.unit if p.custom else "mg"
            row.append((name, weight_mg, unit))
        rows.append(row)
    return rows


def add_task_request_to_excel_bytes(add_task: AddTaskRequest) -> bytes:
    """
    将 AddTaskRequest 转为 Excel 字节流（与用户方示例 配方-0122.xlsx 一致）。

    第一行仅两列表头：【SSSI】粉末、重量（mg），其余列表头为空；
    从第二行起每行一个方案，该行依次为该方案的全部「物质、重量」对（多列），不足填空。
    """
    rows = add_task_request_to_recipe_rows(add_task)
    if not rows:
        df = pd.DataFrame(columns=["【SSSI】粉末", "重量（mg）"])
        buf = io.BytesIO()
        df.to_excel(buf, index=False, engine="openpyxl")
        return buf.getvalue()
    max_pairs = max(len(r) for r in rows)
    # 第一行仅两列表头，后续列用空字符串（Excel 第一行只显示前两列有表头）
    col_names = ["【SSSI】粉末", "重量（mg）"] + [""] * (max_pairs * 2 - 2)
    data = []
    for row in rows:
        line = []
        for i in range(max_pairs):
            if i < len(row):
                name, w, unit = row[i]
                sssi = get_sssi_by_substance(name)
                line.append(f"【{sssi}】{name}" if sssi else name)
                line.append(w)
            else:
                line.append("")
                line.append(None)
        data.append(line)
    df = pd.DataFrame(data, columns=col_names)
    buf = io.BytesIO()
    df.to_excel(buf, index=False, engine="openpyxl")
    return buf.getvalue()


class MixerService:
    """
    配料任务处理服务
    """
    async def parse_mixer_tasks_from_excel(self, excel_contents: bytes) -> AddTaskRequest:
        """
        从Excel内容解析配料任务
        :param excel_contents: Excel文件的字节内容
        :return: 解析后的AddTaskRequest对象
        """
        # 将字节内容转换为DataFrame
        df = pd.read_excel(io.BytesIO(excel_contents))
        
        # 解析Excel数据为MixerTaskModel对象
        # 这里需要根据Excel的实际结构来解析数据
        # 以下是一个示例解析逻辑，您可能需要根据实际Excel格式调整
        
        # 假设Excel中有任务基本信息
        task_name = f"JD_{datetime.now().strftime('%Y%m%d%H%M')}_{str(uuid.uuid4())[:8]}"
        task_type = 2
        is_audit_log = 1
        
        # 解析任务设置
        task_setup = TaskSetup(
            subtype=None,
            powder_100_30=False,
            powder_30_100=False,
            added_slots=""
        )
        
        # 解析布局列表
        layout_list: List[LayoutListItem] = []
        unit_id_base = int(datetime.now().timestamp()*1000)
        # row_idx 对应 JSON 中的 unit_column (第几组实验)
        for row_idx, row in df.iterrows():

            element_count = 0 # 记录当前实验组是第几个元素，用于计算 unit_row
                
            # 遍历当前行的所有列
            for col_idx in range(0, len(df.columns), 2):
                sssi_raw = str(row.iloc[col_idx]).strip()

                # 过滤空单元格
                if not sssi_raw or sssi_raw == 'nan' or sssi_raw == '':
                    continue

                weight = row.iloc[col_idx + 1]
                if pd.isna(weight): weight = 0

                # 解析 【SSSI】名称
                match = re.search(r'【(.*?)】(.*)', sssi_raw)
                sssi_code = match.group(1) if match else sssi_raw
                substance = match.group(2) if match else ""

                # --- 核心坐标逻辑变更 ---
                unit_column = row_idx      # Excel 的行，变成托盘的列
                unit_row = element_count    # 该行的第几个元素，变成托盘的行
                # -----------------------

                # 解析工艺JSON
                process_json = ProcessJson(**{
                    "resource_type": "CC10R10C",
                    "substance": substance,
                    "SSSI": sssi_code,
                    "add_weight": float(weight),
                    "offset": 0.3,
                    "custom": {"unit": "mg","unitOptions": ["mg", "g"]}
                })
            
                layout_item = LayoutListItem(**{
                    "layout_code": "",
                    "src_layout_code": "",
                    "resource_type": "CC10R10C",
                    "tray_QR_code": "",
                    "status": 0,
                    "QR_code": "",
                    "unit_type": "exp_add_powder",
                    "unit_column": unit_column,
                    "unit_row": unit_row,
                    "unit_id": f"unit-{hex(unit_id_base+row_idx)[2:]}",
                    "process_json": process_json
                })
                
                layout_list.append(layout_item)
                element_count += 1 # 准备下一个元素的行号
        
        # 创建MixerModel对象
        mixer_model = AddTaskRequest(
            task_setup=task_setup,
            task_id=0, # 新建任务
            task_name=task_name,
            is_audit_log=is_audit_log,
            type=task_type,
            layout_list=layout_list
        )
        
        return mixer_model


# 创建全局服务实例
mixer_service = MixerService()