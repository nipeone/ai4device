from fastapi import APIRouter
from logger import sys_logger as logger

router = APIRouter(prefix="/api/system", tags=["系统"])

@router.get("/logs", tags=["系统"])
def get_system_logs():
    """获取最新日志"""
    return {"logs": logger.logs}