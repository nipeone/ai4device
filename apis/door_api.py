from fastapi import APIRouter
from logger import sys_logger as logger

# 导入全局实例
from devices.door_core import door_controller
from schemas.door import DoorActionRequest, DoorActionResponse, DoorActionCode, DoorStatusResponse

router = APIRouter(prefix="/api/door", tags=["玻璃门"])

# ==========================================
# 3. 玻璃门模块
# ==========================================
@router.get("/status", response_model=DoorStatusResponse, tags=["玻璃门"])
def get_door_status() -> DoorStatusResponse:
    '''获取所有玻璃门状态
    
    Returns:
        code: int
        message: str
        data: dict
    '''
    status_dict = {}
    for i in range(1, 7): 
        result = door_controller.get_door_status(i)
        if result.get("status") == "success":
            status_dict[i] = result.get("data")
        else:
            return DoorStatusResponse(code=500, message=result.get("message", "未知错误"))
    return DoorStatusResponse(code=200, message="玻璃门状态获取成功", data=status_dict)


@router.post("/control", response_model=DoorActionResponse, tags=["玻璃门"])
def control_door(request: DoorActionRequest) -> DoorActionResponse:
    '''控制玻璃门
    
    Args:
        - door_id: int
        - action: 
           - 0: open
           - 1: close

    Returns:
        - code: int
        - message: str
        - data: str
    '''
    logger.log(f"玻璃门手动操作: ID={request.door_id}, Action={request.action}", "INFO")
    result = door_controller.send_command(request.door_id, DoorActionCode(request.action))
    if result.get("status") != "success": 
        return DoorActionResponse(code=500, message=result.get("message", "未知错误"))
    else:
        return DoorActionResponse(code=200, message="玻璃门操作成功")