from fastapi import APIRouter, File, UploadFile
from logger import sys_logger as logger

# 导入全局实例
from flows.flow_manager import flow_mgr
from devices.mixer_core import mixer_controller
from devices.xrd_core import xrd_controller
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

        # 创建任务
        mixer_controller.add_task(mixer_model.task_name, mixer_model.layout_list, mixer_model.task_id, is_audit_log=mixer_model.is_audit_log)
        # 启动任务
        mixer_controller.start()

        #########################################################
        # 2. 熔封 #
        #########################################################


        #########################################################
        # 3. 上料 #
        #########################################################
        # TODO 怎么获取货架、炉子、数量？
        shelf_id = 1; oven_id = 1; qty = 1; 
        flow_mgr.load(shelf_id, oven_id, qty)

        flow_mgr.user_confirm()

        #########################################################
        # 4. 下料 #
        #########################################################
        # TODO 怎么获取炉子、槽位、货架号？
        oven_id = 1; slot_id = 1; shelf_id = 1; 
        flow_mgr.unload(oven_id, slot_id, shelf_id)

        #########################################################
        # 5. xrd衍射仪 #
        #########################################################
        xrd_controller.start()

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