import threading
from fastapi import APIRouter, File, UploadFile
from logger import sys_logger as logger

# 导入全局实例
from flows.thermal_flow import thermal_flow_mgr
from flows.mix_flow import mix_flow_mgr
from flows.xrd_flow import xrd_flow_mgr
from services.mixer import mixer_service

router = APIRouter(prefix="/api/experiment", tags=["实验"])

# 熔封人工确认事件（配料完成后等待前端调用确认接口再继续热处理）
_seal_confirm_event = threading.Event()
_seal_confirm_event.set()  # 初始为已确认，避免无熔封流程时卡住
SEAL_CONFIRM_TIMEOUT = 300  # 等待熔封确认超时秒数

@router.post("/flux", tags=["实验"])
async def start_experiment(file: UploadFile = File(...)):
    """
    开始试验的总入口
    1. 配料，上传Excel文件，解析配料数据
    2. 熔封
    3. 热处理，包括加热炉、离心机工序
    5. xrd测试
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
        _seal_confirm_event.clear()
        logger.log("等待人工确认熔封完成，请调用 POST /api/experiment/flux/confirm_seal 确认", "WARN")
        if not _seal_confirm_event.wait(timeout=SEAL_CONFIRM_TIMEOUT):
            return {"status": "error", "message": "等待熔封确认超时"}
        logger.log("熔封已确认，继续热处理流程", "INFO")

        #########################################################
        # 3. 热处理 # 包括加热炉、离心机工序
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


@router.post("/flux/confirm_seal", tags=["实验"])
def confirm_flux_seal():
    """人工确认熔封完成。在实验总入口执行到熔封步骤后调用此接口，流程将继续执行热处理。"""
    _seal_confirm_event.set()
    logger.log("人工确认熔封完成", "INFO")
    return {"msg": "熔封确认已接收，流程继续"}