from fastapi import APIRouter
import struct

from utils import cent_format_time
from logger import sys_logger as logger
from devices.cent_core import (
    cent_controller,
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
    CentrifugeRunningStatus,
    CentrifugeActionCode
)

router = APIRouter(prefix="/api/centrifuge", tags=["离心机"])

# ==========================================
# 1. 离心机模块
# ==========================================

@router.get("/status", response_model=CentrifugeStatusResponse, tags=["离心机"])
def get_centrifuge_status() -> CentrifugeStatusResponse:
    '''获取离心机运行状态

    Args:
      - actual_rpm: int 实际运行转速
      - run_time: int 实际运行时间
      - setted_rpm: int 用户设置的转速
      - setted_time: int 用户设置的时间
      - centrifuge_force: int 实际运行离心力
      - remain_time: str 剩余时间
      - run_state: str 运行状态 0 unkown 1 离心机停止, 2 离心机运行
      - rotor_state: str 转子状态 0 unkown, 1 加速, 2 恒速, 3 减速, 4 定位
      - fault_code: str 故障码 0: 系统正常, 1: 转子不平衡, 4: 伺服控制器故障, 5: 离心机门窗未关
      - door_window: str 门窗状态 0 unknown, 1 离心机门窗开, 2 离心机门窗关
      - door_lid: str 门盖状态 1 门盖开, 2 门盖关
    
    Returns:
        code: int
        message: str
        data: dict
    '''
    result = cent_controller.get_running_status()
    if result.get("status") != "success": 
        return CentrifugeStatusResponse(code=500, message=result.get("message", "未知错误"))
    else:
        data: dict = result.get("data")
        if not data:
            return CentrifugeStatusResponse(code=500, message="数据不完整")
        else:
            parsed_data = CentrifugeRunningStatus(
                actual_rpm = data.get('actual_rpm'),
                run_time = data.get('run_time', 0),
                setted_rpm = data.get('setted_rpm', 0),
                setted_time = data.get('setted_time', 0),
                centrifuge_force = data.get('centrifuge_force', 0),

                remain_time = cent_format_time(data.get('remain_time', 0)),
                run_state = CENT_RUN_MAP.get(data.get('run_state'), "状态未知"),
                rotor_state = CENT_ROTOR_MAP.get(data.get('rotor_state'), "不定态"),
                fault_code = CENT_FAULT_MAP.get(data.get('fault_code'), f"未知故障码({data.get('fault_code')})"),
                door_window = CENT_DOOR_MAP.get(data.get('door_window'), "中间状态"),
                door_lid = CENT_LID_MAP.get(data.get('door_lid'), "中间状态")

            ).model_dump()
        return CentrifugeStatusResponse(code=200, message="离心机运行状态获取成功", data=parsed_data)

@router.post("/control", response_model=CentrifugeActionResponse, tags=["离心机"])
def control_centrifuge(request: CentrifugeActionRequest) -> CentrifugeActionResponse:
    '''控制离心机启动、停止，控制门窗开闭
    Args:
        action:
            1: start 启动离心机
            2: stop  停止离心机
            3: open  开离心机门窗
            4: close 关离心机门窗
    Returns:
        code: int
        message: str
        data: str
    '''
    action = request.action
    if action not in [CentrifugeActionCode.START, CentrifugeActionCode.STOP, CentrifugeActionCode.OPEN, CentrifugeActionCode.CLOSE]:
        return CentrifugeActionResponse(code=400, message="无效的操作类型", data=None)
    logger.log(f"离心机手动操作: {action.name}", "INFO")
    result = cent_controller.control_centrifuge(action)
    if result.get("status") == "success":
        return CentrifugeActionResponse(code=200, message=result.get("message", "离心机操作成功"), data=action)
    else:
        return CentrifugeActionResponse(code=500, message=result.get("message", "未知错误"))


@router.post("/speed", response_model=CentrifugeSpeedResponse, tags=["离心机"])
def set_cent_speed(request: CentrifugeSpeedRequest) -> CentrifugeSpeedResponse:
    '''设置离心机转速；单位：RPM'''
    result = cent_controller.set_speed(request.rpm)
    if result.get("status") == "success":
        return CentrifugeSpeedResponse(code=200, message=result.get("message", "离心机转速设置成功"), data=request.rpm)
    else:
        return CentrifugeSpeedResponse(code=500, message=result.get("message", "未知错误"))

@router.post("/time", response_model=CentrifugeTimeResponse, tags=["离心机"])
def set_cent_time(request: CentrifugeTimeRequest) -> CentrifugeTimeResponse:
    '''设置离心机时间；单位：秒'''
    result = cent_controller.set_time(request.time)
    if result.get("status") == "success":
        return CentrifugeTimeResponse(code=200, message=result.get("message", "离心机时间设置成功"), data=request.time)
    else:
        return CentrifugeTimeResponse(code=500, message=result.get("message", "未知错误"))