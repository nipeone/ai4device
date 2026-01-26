from fastapi import APIRouter
from datetime import datetime, timedelta
from logger import sys_logger as logger

# 导入全局实例
from devices.oven_core import oven_controller, OvenActionCode, OvenLidActionCode
from schemas.oven import (
    OvenStatusResponse,
    OvenStatus,
    OvenCurveResponse,
    OvenCurveRequest,
    CurvePoint,
    OvenCurveListResponse,
    OvenCurveListItem,
    OvenCurveByNameRequest,
    OvenActionRequest,
    OvenActionResponse,
    OvenLidActionRequest
)
from services.oven import oven_service

router = APIRouter(prefix="/api/oven", tags=["炉子"])

@router.post("/control/lid", tags=["炉盖"])
def control_oven_lid(request: OvenLidActionRequest):
    '''控制炉盖
    
    Args:
        oven_id: int
        action: 
            0: open
            1: close
    Returns:
        code: int
        message: str
        data: str
    '''
    logger.log(f"炉盖手动操作: ID={request.oven_id}, Action={request.action}", "INFO")
    result = oven_controller.control_lid(request.oven_id, OvenLidActionCode(request.action))
    if result.get("status") != "success": 
        return OvenActionResponse(code=500, message=result.get("message", "未知错误"))
    else:
        return OvenActionResponse(code=200, message="炉盖操作成功")

@router.post("/control", tags=["炉子"])
def control_oven(request: OvenActionRequest):
    '''控制炉子
    
    Args:
        oven_id: int
        action: 
            0: start
            1: stop
            2: pause
    Returns:
        code: int
        message: str
        data: str
    '''
    logger.log(f"炉子手动操作: ID={request.oven_id}, Action={request.action}", "INFO")
    result = oven_controller.control_oven(request.oven_id, OvenActionCode(request.action))
    if result.get("status") != "success": 
        return OvenActionResponse(code=500, message=result.get("message", "未知错误"))
    else:
        return OvenActionResponse(code=200, message="炉子操作成功")

@router.get("/status", tags=["炉子"], response_model=OvenStatusResponse)
def get_oven_status() -> OvenStatusResponse:
    result = oven_controller.get_running_status()
    if result.get("status") != "success":
        return OvenStatusResponse(code=500, message=result.get("message", "未知错误"))
    else:
        data: list = result.get("data")
        oven_status_list = []
        for item in data:
            oven_status_list.append(OvenStatus(
                    device_name=item["设备名称"],
                    device_address=item["设备地址"],
                    device_type=item["仪表型号"],
                    online_status=item["在线状态"],
                    actual_temperature=item["实际温度"],
                    setted_temperature=item["设定温度"],
                    running_curve=item["运行曲线"],
                    status_display=item["状态显示"],
                    end_time=item["结束时间"],
                    status=item["状态"]
                ))
        if not data:
            return OvenStatusResponse(code=500, message="数据不完整")
        else:
            return OvenStatusResponse(code=200, message="炉子运行状态获取成功", data=oven_status_list)

@router.post("/curve", tags=["炉子"], response_model=OvenCurveResponse)
def set_oven_curve(request: OvenCurveRequest) -> OvenCurveResponse:
    '''上传炉子运行曲线
    
    Args:
        request: OvenCurveRequest
    Returns:
        OvenCurveResponse
    '''

    DEVICE_TYPE = "858P"

    # 1. 预处理数据 (保持 858P 逻辑)
    processed_points: list[CurvePoint] = []
    for p in request.points:
        if p.time == 0: continue
        if p.time < 0:
            processed_points.append(CurvePoint(temperature=p.temperature, time=-121.0))
            break
        else:
            processed_points.append(CurvePoint(temperature=p.temperature, time=p.time))

    if not processed_points:
        return OvenCurveResponse(code=500, message="没有有效的曲线数据")

    # 2. 执行硬件下传
    result = oven_controller.set_curve_points(request.oven_id, processed_points)

    # 3. 自主选择保存逻辑
    if result.get("status") == "success" and request.curve_name:
        oven_service.persist_oven_curve(request.oven_id, request.curve_name, processed_points)

    if result.get("status") != "success":
        return OvenCurveResponse(code=500, message=result.get("message", "未知错误"))
    else:
        return OvenCurveResponse(code=200, message="炉子运行曲线设置成功", data=processed_points)

@router.get("/curve", tags=["炉子"], response_model=OvenCurveListResponse)
def get_oven_curve_list() -> OvenCurveListResponse:
    '''查询已保存工艺列表
    
    Returns:
        OvenCurveListResponse
    '''

    curve_list = oven_service.get_oven_curve_list()
    if not curve_list:
        return OvenCurveListResponse(code=500, message="没有已保存工艺")
    else:
        return OvenCurveListResponse(code=200, message="炉子运行曲线列表获取成功", data=curve_list)

@router.post("/curve/name", tags=["炉子"], response_model=OvenCurveResponse)
def set_oven_curve_by_name(request: OvenCurveByNameRequest) -> OvenCurveResponse:
    '''直接调用数据库里存好的曲线，不用重新填表
    
    Args:
        request: OvenCurveByNameRequest
    Returns:
        OvenCurveResponse
    '''
    processed_points =  oven_service.get_oven_curve_by_name(request.curve_name)
    if not processed_points:
        return OvenCurveResponse(code=500, message="没有找到该工艺曲线")

    result = oven_controller.set_curve_points(request.oven_id, processed_points)
    if result.get("status") != "success":
        return OvenCurveResponse(code=500, message=result.get("message", "未知错误"))
    else:
        return OvenCurveResponse(code=200, message="炉子运行曲线设置成功", data=processed_points)