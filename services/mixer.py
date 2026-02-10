import pandas as pd
import io
from typing import Any, List
import uuid
from datetime import datetime
import re
from schemas.mixer import AddTaskRequest, TaskSetup, LayoutListItem, ProcessJson

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