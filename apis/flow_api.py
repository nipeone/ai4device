from fastapi import APIRouter, Body
from logger import sys_logger as logger

# 导入全局实例
from devices.flow_manager import flow_mgr

router = APIRouter(prefix="/api/flow", tags=["流程"])

# ==========================================
# 5. 流程管理器接口
# ==========================================

@router.post("/confirm_continue", tags=["流程"])
def confirm_flow_continue():
    """流程暂停时的确认继续接口"""
    flow_mgr.user_confirm()
    return {"msg": "确认指令已发送"}


@router.post("/load", tags=["流程"])
def start_input_flow(shelf_id: int = Body(...), oven_id: int = Body(...), qty: int = Body(...)):
    """启动上料流程（货架 -> 炉子）。
在 Request body 中输入 shelf_id (货架号)、oven_id (炉子号)、qty (数量)，点击 Execute 执行。执行后系统将自动打开对应炉盖与门，并暂停等待人工确认。"""
    flow_mgr.load(shelf_id, oven_id, qty)
    return {"msg": "上料流程已启动", "detail": f"货架{shelf_id} -> 炉子{oven_id} (数量:{qty})"}


@router.post("/unload", tags=["流程"])
def start_output_flow(oven_id: int = Body(...), slot_id: int = Body(...), shelf_id: int = Body(...)):
    """启动出料流程（炉子 -> 离心机 -> 货架）。
在 Request body 中输入 oven_id (炉子号)、slot_id (穴位号)、shelf_id (货架号)，点击 Execute 执行。此流程包含三次暂停，需配合确认接口使用。"""
    flow_mgr.unload(oven_id, slot_id, shelf_id)
    return {"msg": "出料流程已启动", "detail": f"炉子{oven_id}(穴{slot_id}) -> 离心机 -> 货架{shelf_id}"}


@router.get("/status", tags=["流程"])
def get_flow_status():
    """获取当前流程运行状态。
返回数据中 running 表示是否运行中，step_info 显示当前步骤。若显示"等待确认..."，请使用确认接口。"""
    return {
        "running": flow_mgr.running,
        "step_info": flow_mgr.current_step_info,
        "remaining_tasks": len(flow_mgr.task_queue)
    }