from fastapi import APIRouter, File, UploadFile
from logger import sys_logger as logger

# 导入全局实例
from flows.thermal_flow import thermal_flow_mgr
from flows.mix_flow import mix_flow_mgr
from flows.xrd_flow import xrd_flow_mgr
from services.mixer import mixer_service

router = APIRouter(prefix="/api/experiment", tags=["实验"])

@router.post("/flux", tags=["实验"])
async def start_experiment(file: UploadFile = File(...)):
    """
    开始试验的总入口
    1. 配料，上传Excel文件，解析配料数据
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

        #########################################################
        # 1. 配料 #
        #########################################################
        mixer_model = await mixer_service.parse_mixer_tasks_from_excel(contents)
        logger.log(f"Excel文件解析成功，任务名称: {mixer_model.task_name}", "INFO")

        mix_flow_mgr.run(mixer_model)

        #########################################################
        # 2. 熔封 #
        #########################################################

        # TODO API为完成，人工确认熔封完成

        #########################################################
        # 3. 热处理 # 包括高温炉、离心机工序
        #########################################################

        thermal_flow_mgr.run()

        #########################################################
        # 4. xrd衍射仪 #
        #########################################################
        xrd_flow_mgr.run()

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