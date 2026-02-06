from fastapi import APIRouter
from logger import sys_logger as logger

from devices.mixer_core import mixer_controller

router = APIRouter(prefix="/api/mixer", tags=["配料"])

@router.get("/status", tags=["配料"])
def get_mixer_status():
    """获取配料设备状态（连接状态、当前任务、消息）"""
    status = mixer_controller.get_status()
    status_value = status.name if hasattr(status, "name") else str(status)
    status_dict = {
        "1": {
            "connection": status_value,
            "message": mixer_controller.get_message(),
            "current_task_id": getattr(mixer_controller, "current_task_id", None),
        }
    }
    return {"source": "硬件实时反馈", "mixers": status_dict}