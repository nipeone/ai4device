from typing import Optional, Literal
from pydantic import BaseModel, Field, field_validator
from enum import Enum

from .base import BaseResponse

class RobotActionCode(Enum):
    reset = "reset"
    toggle = "toggle"

class RobotStatus(BaseModel):
    """机器人状态
    
    - home_status: 原点状态
    - fixture_status: 夹具状态
    - system_status: 系统状态
    - robot_status: 机器人启动/暂停
    - task_status: 任务状态
    """
    home_status: bool = Field(..., description="原点状态", example=True)
    fixture_status: bool = Field(..., description="夹具状态", example=True)
    system_status: int = Field(..., description="系统状态", example=1)
    robot_status: bool = Field(..., description="机器人启动/暂停", example=True)
    task_status: int = Field(..., description="任务状态", example=1)
    
class TaskData(BaseModel):
    """任务数据
    
    - tid: 任务ID
    - st: 站点
    - qty: 数量
    """
    tid: int = Field(..., description="任务ID", example=123456)
    st: int = Field(..., description="站点", example=1)
    qty: int = Field(..., description="数量", example=10)

class PlcStatus(BaseModel):
    """PLC状态
    
    - plc_connected: PLC连接状态
    - m_signals: M区控制信号状态
    - task_data: 任务数据
    - robot: 机器人状态
    """
    plc_connected: bool = Field(..., description="PLC连接状态", example=True)
    m_signals: list[bool] = Field(..., description="M区控制信号状态", example=[False, False, False, False, False, False, True])
    task_data: TaskData = Field(..., description="任务数据", example=TaskData(tid=123456, st=1, qty=10))
    robot: RobotStatus = Field(..., description="机器人状态", example=RobotStatus(
        home_status=True, 
        fixture_status=True, 
        system_status=1, 
        robot_status=True, 
        task_status=1))

    @field_validator('m_signals')
    def validate_m_signals(cls, v):
        if len(v) != 7:
            raise ValueError("M区控制信号状态必须为7个元素")
        return v

class RobotActionRequest(BaseModel):
    action: RobotActionCode = Field(..., description="动作", example=RobotActionCode.reset)

class RobotActionResponse(BaseResponse):
    data: Optional[bool] = Field(default=None, description="动作结果")

class PlcStatusResponse(BaseResponse):
    data: Optional[PlcStatus] = Field(default=None, description="PLC状态")