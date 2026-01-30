from fastapi import APIRouter
from datetime import datetime, timedelta
from logger import sys_logger as logger

from devices.xrd_core import xrd_controller

router = APIRouter(prefix="/api/xrd", tags=["xrd衍射仪"])


@router.get("/status", tags=["xrd衍射仪"])
def get_xrd_status():
    return xrd_controller.get_sample_status()

@router.post("/realtime", tags=["xrd衍射仪"])
def get_realtime_data():
    '''上样请求'''
    return xrd_controller.get_current_acquire_data()
