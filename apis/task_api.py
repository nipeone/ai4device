from fastapi import APIRouter, File, UploadFile
import pandas as pd
import io
from logger import sys_logger as logger
from schemas.mixer_task import MixerTaskModel
from services.mixer_task import mixer_task_service

router = APIRouter(prefix="/api/task", tags=["任务"])

@router.post("/experiment", tags=["任务"])
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

        mixer_task = await mixer_task_service.parse_mixer_tasks_from_excel(contents)

        logger.log(f"Excel文件解析成功，任务名称: {mixer_task.task_name}", "INFO")

        return {
            "status": "success",
            "message": "Excel文件解析成功",
            "task_data": mixer_task.model_dump_json()
        }

    except Exception as e:
        logger.log(f"Excel文件解析失败: {str(e)}", "ERROR")
        return {
            "status": "error",
            "message": f"Excel文件解析失败: {str(e)}"
        }