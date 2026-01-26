from asyncio.constants import ACCEPT_RETRY_DELAY
from fastapi import APIRouter
import struct

from utils import cent_format_time
from logger import sys_logger as logger
from devices.centrifuge_core import (
    centrifuge_controller,
    CENT_RUN_MAP,
    CENT_ROTOR_MAP,
    CENT_DOOR_MAP,
    CENT_FAULT_MAP,
    CENT_LID_MAP
)
from schemas.centrifuge import (
    CentrifugeStatusResponse,
    CentrifugeSpeedResponse,
    CentrifugeTimeResponse,
    CentrifugeSpeedRequest,
    CentrifugeTimeRequest,
    CentrifugeActionRequest,
    CentrifugeActionResponse,
    CentrifugeStatus
)

router = APIRouter(prefix="/api/centrifuge", tags=["离心机"])

# ==========================================
# 1. 离心机模块
# ==========================================

@router.get("/status", response_model=CentrifugeStatusResponse, tags=["离心机"])
def get_centrifuge_status() -> CentrifugeStatusResponse:
    result = centrifuge_controller.get_running_status()
    if result.get("status") != "success": 
        return CentrifugeStatusResponse(code="500", message=result.get("message", "未知错误"))
    else:
        data: dict = result.get("data")
        if not data:
            return CentrifugeStatusResponse(code="500", message="数据不完整")
        else:
            parsed_data = CentrifugeStatus(
                actual_rpm = data.get('actual_rpm'),
                remain_time = cent_format_time(data.get('remain_time')),
                run_state = CENT_RUN_MAP.get(data.get('run_state', 0)),
                rotor_state = CENT_ROTOR_MAP.get(data.get('rotor_state'), "静止"),
                fault_code = CENT_FAULT_MAP.get(data.get('fault_code'), "未知故障码"),
                door_window_state = CENT_DOOR_MAP.get(data.get('door_window'), "未知代码"),
                door_lid_state = CENT_LID_MAP.get(data.get('door_lid'), "未知代码"),
                actual_time = data.get('run_time'),
                setted_rpm = data.get('setted_rpm'),
                setted_time = data.get('setted_time'),
                centrifuge_force = data.get('centrifuge_force')
            )
        return CentrifugeStatusResponse(code="200", message="离心机运行状态获取成功", data=parsed_data)


@router.post("/{action}", response_model=CentrifugeActionResponse, tags=["离心机"])
def control_centrifuge(request: CentrifugeActionRequest) -> CentrifugeActionResponse:
    action = request.action
    logger.log(f"离心机手动操作: {action}", "INFO")
    result = centrifuge_controller.control_centrifuge(action)
    if result.get("status") == "success":
        return CentrifugeActionResponse(code="200", message=result.get("message", "离心机操作成功"), data=action)
    else:
        return CentrifugeActionResponse(code="500", message=result.get("message", "未知错误"))


@router.post("/speed/{rpm}", response_model=CentrifugeSpeedResponse, tags=["离心机"])
def set_cent_speed(request: CentrifugeSpeedRequest) -> CentrifugeSpeedResponse:
    '''设置离心机转速'''
    result = centrifuge_controller.set_speed(request.rpm)
    if result.get("status") == "success":
        return CentrifugeSpeedResponse(code="200", message=result.get("message", "离心机转速设置成功"), data=request.rpm)
    else:
        return CentrifugeSpeedResponse(code="500", message=result.get("message", "未知错误"))

@router.post("/time/{time}", response_model=CentrifugeTimeResponse, tags=["离心机"])
def set_cent_time(request: CentrifugeTimeRequest) -> CentrifugeTimeResponse:
    '''设置离心机时间'''
    result = centrifuge_controller.set_time(request.time)
    if result.get("status") == "success":
        return CentrifugeTimeResponse(code="200", message=result.get("message", "离心机时间设置成功"), data=request.time)
    else:
        return CentrifugeTimeResponse(code="500", message=result.get("message", "未知错误"))