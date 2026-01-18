from fastapi import APIRouter, File, UploadFile
from logger import sys_logger as logger

# 导入全局实例
from devices.flow_manager import flow_mgr
from devices.mixer_core import mixer_controller
from devices.centrifuge_core import centrifuge_controller
from devices.oven_core import oven_controller
from devices.door_core import door_controller
from services.mixer import mixer_service

router = APIRouter(prefix="/api/experiment", tags=["实验"])

@router.post("/experiment", tags=["实验"])
async def start_experiment(file: UploadFile = File(...)):
    """
    开始试验的总入口
    1. 上传Excel文件，解析配料数据
    2. 熔封
    3. 上料
    4. 下料
    5. xrd衍射仪
    """
    try:
        # 检查文件类型
        if not file.filename.lower().endswith(('.xlsx', '.xls')):
            return {"status": "error", "message": "只支持上传Excel文件(.xlsx, .xls)"}

        # 读取上传的Excel文件
        contents = await file.read()

        mixer_model = await mixer_service.parse_mixer_tasks_from_excel(contents)

        logger.log(f"Excel文件解析成功，任务名称: {mixer_model.task_name}", "INFO")

        return {
            "status": "success",
            "message": "Excel文件解析成功",
            "task_data": mixer_model.model_dump_json()
        }

    except Exception as e:
        logger.log(f"Excel文件解析失败: {str(e)}", "ERROR")
        return {
            "status": "error",
            "message": f"Excel文件解析失败: {str(e)}"
        }