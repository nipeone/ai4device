from typing import Optional, Literal
from pydantic import BaseModel, Field, field_validator
from enum import Enum

from .base import BaseResponse

class CentrifugeActionCode(Enum):
    '''离心机动作
    - START: 启动
    - STOP: 停止
    - OPEN: 打开
    - CLOSE: 关闭
    '''
    START = 1
    STOP = 2
    OPEN = 3
    CLOSE = 4

class CentrifugeDoorStatus(Enum):
    '''离心机门窗状态
    - UNKNOWN: 中间状态(0)
    - OPENED: 打开(1)
    - CLOSED: 关闭(2)
    '''
    UNKNOWN = 0
    OPENED = 1
    CLOSED = 2

class CentrifugeStatus(Enum):
    '''离心机运行状态
    - UNKNOWN: 状态未知(0)
    - STOPPED: 已停止(1)
    - RUNNING: 运行中(2)
    '''
    UNKNOWN = 0
    STOPPED = 1
    RUNNING = 2

class CentrifugeRotorStatus(Enum):
    '''离心机转子状态
    - UNKNOWN: 状态未知(0)
    - ACCELERATING: 加速状态(1)
    - CONSTANT_SPEED: 恒速状态(2)
    - DECELERATING: 减速状态(3)
    - LOCATION: 定位状态(4)
    '''
    UNKNOWN = 0
    ACCELERATING = 1
    CONSTANT_SPEED = 2
    DECELERATING = 3
    LOCATION = 4

class CentrifugeSpeedResponse(BaseResponse):
    data: Optional[int] = Field(default=None, description="转速")

class CentrifugeTimeResponse(BaseResponse):
    data: Optional[int] = Field(default=None, description="时间，单位为分钟")

class CentrifugeActionResponse(BaseResponse):
    data: Optional[CentrifugeActionCode] = Field(default=None, description="动作")

class CentrifugeSpeedRequest(BaseModel):
    rpm: int = Field(..., ge=10, le=3000, description="转速")

    @field_validator('rpm')
    def validate_rpm(cls, v):
        if v < 10 or v > 3000:
            raise ValueError("转速必须在10到3000之间")
        return v

class CentrifugeTimeRequest(BaseModel):
    time: int = Field(..., description="时间，单位为分钟")

    # @field_validator('time')
    # def validate_time(cls, v):
    #     if v < 1 or v > 1440:
    #         raise ValueError("时间必须在1到1440之间")
    #     return v

class CentrifugeActionRequest(BaseModel):
    action: CentrifugeActionCode = Field(..., description="动作")

class CentrifugeRunningStatus(BaseModel):
    actual_rpm: int = Field(..., description="当前转速 RPM")
    centrifuge_force: int = Field(..., description="实际离心力")
    run_time: int = Field(..., description="运行时间")
    fault_code: str = Field(..., description="故障码 0: 系统正常, 1: 转子不平衡, 4: 伺服控制器故障, 5: 离心机门未关")
    run_state: str = Field(..., description="运行状态 0: 状态未知, 1: 已停止, 2: 运行中")
    door_window: str = Field(..., description="门窗状态 0: 中间状态, 1: 门窗开启, 2: 门窗关闭")
    setted_rpm: int = Field(..., description="设置转速")
    setted_time: int = Field(..., description="设置时间")
    door_lid: str = Field(..., description="门盖状态 0: 中间状态, 1: 门盖开启, 2: 门盖关闭")
    rotor_state: str = Field(..., description="机器状态 0: 不定态, 1: 加速中, 2: 恒速运行, 3: 降速中, 4: 定位中")
    remain_time: str = Field(..., description="剩余时间 格式: HH:MM:SS")

class CentrifugeStatusResponse(BaseResponse):
    data: Optional[dict] = Field(default=None, description="数据")
