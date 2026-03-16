from fastapi import APIRouter, Body
from logger import sys_logger as logger

# 导入全局实例
from flows.thermal_flow import thermal_flow_mgr
from flows.mix_flow import mix_flow_mgr
from flows.xrd_flow import xrd_flow_mgr
from schemas.flow import StartXRDTestRequest

router = APIRouter(prefix="/api/flow", tags=["流程"])

@router.post("/thermal/confirm_continue", tags=["热处理流程"])
def confirm_flow_continue():
    """流程暂停时的确认继续接口"""
    thermal_flow_mgr.user_confirm()
    return {"code": 200, "status": "success", "message": "确认指令已发送", "data": None}


@router.post("/thermal/load", tags=["热处理流程"])
def start_input_flow(shelf_id: int = Body(...), oven_id: int = Body(...), qty: int = Body(...)):
    """启动上料流程（货架 -> 炉子）。
在 Request body 中输入 shelf_id (货架号)、oven_id (炉子号)、qty (数量)，点击 Execute 执行。执行后系统将自动打开对应炉盖与门，并暂停等待人工确认。"""
    thermal_flow_mgr.load(shelf_id, oven_id, qty)
    return {"code": 200, "status": "success", "message": "上料流程已启动，货架{shelf_id} -> 炉子{oven_id} (数量:{qty})", "data": None}


@router.post("/thermal/unload", tags=["热处理流程"])
def start_output_flow(oven_id: int = Body(...), slot_id: int = Body(...), shelf_id: int = Body(...)):
    """启动出料流程（炉子 -> 离心机 -> 货架）。
在 Request body 中输入 oven_id (炉子号)、slot_id (穴位号)、shelf_id (货架号)，点击 Execute 执行。此流程包含三次暂停，需配合确认接口使用。"""
    thermal_flow_mgr.unload(oven_id, slot_id, shelf_id)
    return {"code": 200, "status": "success", "message": "出料流程已启动，炉子{oven_id}(穴{slot_id}) -> 离心机 -> 货架{shelf_id}", "data": None}


@router.get("/thermal/status", tags=["热处理流程"])
def get_thermal_flow_status():
    """获取当前流程运行状态。
返回数据中 running 表示是否运行中，step_info 显示当前步骤。若显示"等待确认..."，请使用确认接口。"""
    data = {
        "running": thermal_flow_mgr.running,
        "step_info": thermal_flow_mgr.current_step_info,
        "remaining_tasks": len(thermal_flow_mgr.task_queue)
    }
    return {"code": 200, "status": "success", "message": "获取热处理流程状态成功", "data": data}

@router.post("/xrd/start", tags=["xrd衍射仪流程"])
def start_xrd_single_sample_test(
    request: StartXRDTestRequest
):
    """启动xrd单样品测试流程"""
    xrd_flow_mgr.run(True, request.sample_id, request.start_theta, request.end_theta, request.increment, request.exp_time)
    return {"code": 200, "status": "success", "message": "xrd单样品测试流程已启动，样品{request.sample_id}测试完成"}

@router.post("/xrd/stop", tags=["xrd衍射仪流程"])
def stop_xrd_single_sample_test():
    xrd_flow_mgr.stop()
    return {"code": 200, "status": "success", "message": "xrd已停止", "data": None}

@router.post("/xrd/confirm", tags=["xrd衍射仪流程"])
def confirm_xrd_test():
    """
    确认 XRD 流程中的当前等待步骤（人工上样/下样等）。
    单样品：上样时调用 1 次即可；多样品：每支试管上样、每支试管下样各需调用 1 次（6 支共 12 次）。
    当前等待提示见 GET /api/experiment/status 的 step_info。
    """
    xrd_flow_mgr.user_confirm()
    return {"code": 200, "status": "success", "message": "完成确认", "data": None}

@router.get("/xrd/latest", tags=["xrd衍射仪流程"])
def get_xrd_latest_data():
    """确认xrd单样品测试完成"""
    data = xrd_flow_mgr.get_latest_data()
    if data is not None:
        return {"code": 200, "status": "success", "message": "获取成功", "data": data}
    else:
        return {"code": 400, "status": "error", "message": "获取失败", "data": None}