from typing import Optional, Literal
from pydantic import BaseModel, Field, field_validator

from .base import BaseResponse

class RobotStatus(BaseModel):
    home_status: bool = Field(..., description="原点状态", example=True)
    fixture_status: bool = Field(..., description="夹具状态", example=True)
    system_status: int = Field(..., description="系统状态", example=1)
    robot_status: bool = Field(..., description="机器人启动/暂停", example=True)
    task_status: int = Field(..., description="任务状态", example=1)
    
class TaskData(BaseModel):
    tid: int = Field(..., description="任务ID", example=123456)
    st: int = Field(..., description="站点", example=1)
    qty: int = Field(..., description="数量", example=10)

class PlcStatus(BaseModel):
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
