import pandas as pd
import io
from typing import Any, List
import uuid
from datetime import datetime
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
        for index, row in df.iterrows():
            if index == 0:  # 跳过标题行或任务基本信息行
                continue
                
            # 解析工艺JSON
            process_json = ProcessJson(**{
                "resource_type": row.get('resource_type', 'CC10R10C'),
                "substance": row.get('substance', ''),
                "chemical_id": int(row.get('chemical_id', 0)),
                "SSSI": row.get('SSSI', ''),
                "add_weight": int(row.get('add_weight', 0)),
                "offset": int(row.get('offset', 0)),
                "custom": {
                    "unit": row.get('unit', ''),
                    "unitOptions": [row.get('unit', '')]  # 示例
                }
            })
            
            layout_item = LayoutListItem(**{
                "layout_code": row.get('layout_code', ''),
                "src_layout_code": row.get('src_layout_code', ''),
                "resource_type": row.get('resource_type', 'CC10R10C'),
                "tray_QR_code": row.get('tray_QR_code', ''),
                "status": int(row.get('status', 0)),
                "QR_code": row.get('QR_code', ''),
                "unit_type": row.get('unit_type', 'exp_add_powder'),
                "unit_column": int(row.get('unit_column', 0)),
                "unit_row": int(row.get('unit_row', 0)),
                "unit_id": row.get('unit_id', ''),
                "process_json": process_json
            })
            
            layout_list.append(layout_item)
        
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