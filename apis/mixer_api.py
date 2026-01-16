from fastapi import APIRouter
from datetime import datetime, timedelta
from logger import sys_logger as logger


router = APIRouter(prefix="/api/mixer", tags=["配料"])

@router.get("/status", tags=["配料"])
def get_mixer_status():
    status_dict = {}
    return {"source": "硬件实时反馈", "mixers": status_dict}