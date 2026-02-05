from typing import Optional, Literal
from pydantic import BaseModel, Field, field_validator
from enum import Enum

from .base import BaseResponse

class RobotActionCode(Enum):
    reset = "reset"
    toggle = "toggle"

class RobotSystemStatus(Enum):
    '''机器人系统状态
    - DISCONNECTED: 断线(0)
    - IDLE: 空闲(1)
    - RUNNING: 运行中(2)
    - COMPLETED: 完成(3)
    - FAILED: 失败(4)
    '''
    DISCONNECTED = 0
    IDLE = 1
    RUNNING = 2
    COMPLETED = 3
    FAILED = 4

class RobotWorkingStatus(Enum):
    '''机器人状态
    - PAUSED: 暂停(0)
    - STARTED: 启动(1)
    '''
    PAUSED = 0
    STARTED = 1

class RobotHomeStatus(Enum):
    '''机器人原点状态
    - NOT_HOME: 非原点(0)
    - IN_HOME: 在原点(1)
    '''
    NOT_HOME = 0
    IN_HOME = 1

class RobotTaskStatus(Enum):
    '''机器人任务状态
    - NO_TASK: 无任务(0)
    - HAS_TASK: 有任务(1)
    '''
    NO_TASK = 0
    HAS_TASK = 1

class RobotStatus(BaseModel):
    """机器人状态
    
    - home_status: 原点状态
    - fixture_status: 夹具状态
    - system_status: 系统状态
    - robot_status: 机器人启动/暂停
    - task_status: 任务状态
    """
    home_status: bool = Field(..., description="原点状态")
    fixture_status: bool = Field(..., description="夹具状态")
    system_status: int = Field(..., description="系统状态")
    robot_status: bool = Field(..., description="机器人启动/暂停")
    task_status: int = Field(..., description="任务状态")
    
class TaskData(BaseModel):
    """任务数据
    
    - tid: 任务ID
    - st: 站点
    - qty: 数量
    """
    tid: int = Field(..., description="任务ID")
    st: int = Field(..., description="站点")
    qty: int = Field(..., description="数量")

    model_config = {
        "json_schema_extra": {
            "examples": [  # 复数examples，值为列表（支持多个示例）
                {
                    "tid": 123456,
                    "st": 1,
                    "qty": 10,
                }
            ]
        }
    }

class PlcStatus(BaseModel):
    """PLC状态
    
    - plc_connected: PLC连接状态
    - m_signals: M区控制信号状态
    - task_data: 任务数据
    - robot: 机器人状态
    """
    plc_connected: bool = Field(..., description="PLC连接状态")
    m_signals: list[bool] = Field(..., description="M区控制信号状态")
    task_data: TaskData = Field(..., description="任务数据")
    robot: RobotStatus = Field(..., description="机器人状态")

    @field_validator('m_signals')
    def validate_m_signals(cls, v):
        if len(v) != 7:
            raise ValueError("M区控制信号状态必须为7个元素")
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [  # 复数examples，值为列表（支持多个示例）
                {
                    "plc_connected": True,
                    "m_signals": [False, False, False, False, False, False, True],
                    "task_data": TaskData(tid=123456, st=1, qty=10),
                    "robot": RobotStatus(
                        home_status=True, 
                        fixture_status=True, 
                        system_status=1, 
                        robot_status=True, 
                        task_status=1)
                }
            ]
        }
    }

class RobotActionRequest(BaseModel):
    action: RobotActionCode = Field(..., description="动作")

class RobotActionResponse(BaseResponse):
    data: Optional[bool] = Field(default=None, description="动作结果")

class PlcStatusResponse(BaseResponse):
    data: Optional[PlcStatus] = Field(default=None, description="PLC状态")