from fastapi import APIRouter
from logger import sys_logger as logger

# 导入全局实例
from devices.door_core import door_ctrl

router = APIRouter(prefix="/api/door", tags=["玻璃门"])

# ==========================================
# 3. 玻璃门模块
# ==========================================
@router.get("/status", tags=["玻璃门"])
def get_door_status():
    status_dict = {}
    for i in range(1, 7): status_dict[i] = door_ctrl.get_door_status(i)
    return {"source": "硬件实时反馈", "doors": status_dict}


@router.post("/{id}/{action}", tags=["玻璃门"])
def control_door(id: int, action: str):
    logger.log(f"玻璃门手动操作: ID={id}, Action={action}", "INFO")
    res = door_ctrl.send_command(id, action)
    res["current_real_status"] = door_ctrl.get_door_status(id)
    return res