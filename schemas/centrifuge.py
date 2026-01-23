from typing import Optional, Literal
from pydantic import BaseModel, Field, field_validator

from .base import BaseResponse

class CentrifugeSpeedResponse(BaseResponse):
    data: Optional[int] = Field(default=None, description="转速", example=1000)

class CentrifugeTimeResponse(BaseResponse):
    data: Optional[int] = Field(default=None, description="时间", example=1000)

class CentrifugeActionResponse(BaseResponse):
    data: Optional[str] = Field(default=None, description="动作", example="start")

class CentrifugeSpeedRequest(BaseModel):
    rpm: int = Field(..., ge=10, le=3000, description="转速", example=1000)

    @field_validator('rpm')
    def validate_rpm(cls, v):
        if v < 10 or v > 3000:
            raise ValueError("转速必须在10到3000之间")
        return v

class CentrifugeTimeRequest(BaseModel):
    time: int = Field(..., description="时间", example=1000)

    # @field_validator('time')
    # def validate_time(cls, v):
    #     if v < 1 or v > 1440:
    #         raise ValueError("时间必须在1到1440之间")
    #     return v

class CentrifugeActionRequest(BaseModel):
    action: Literal["start", "stop", "open", "close"] = Field(..., description="动作", example="start")

    @field_validator('action')
    def validate_action(cls, v):
        if v not in ["start", "stop", "open", "close"]:
            raise ValueError("动作必须在start、stop、open、close之间")
        return v

class CentrifugeStatus(BaseModel):
    actual_rpm: int = Field(..., description="当前转速 RPM", example=1000)
    centrifuge_force: int = Field(..., description="实际离心力", example=1000)
    run_time: int = Field(..., description="运行时间", example=1000)
    fault_code: str = Field(..., description="故障码 0: 系统正常, 1: 转子不平衡, 4: 伺服控制器故障, 5: 离心机门未关", example=0)
    run_state: str = Field(..., description="运行状态 0: 状态未知, 1: 已停止, 2: 运行中", example=0)
    door_window: str = Field(..., description="门窗状态 1: 门窗开启, 2: 门窗关闭", example=0)
    setted_rpm: int = Field(..., description="设置转速", example=1000)
    setted_time: int = Field(..., description="设置时间", example=1000)
    door_lid: str = Field(..., description="门盖状态 1: 门盖开启, 2: 门盖关闭", example=0)
    rotor_state: str = Field(..., description="机器状态 0: 不定态, 1: 加速中, 2: 恒速运行, 3: 降速中, 4: 定位中", example=0)
    remain_time: str = Field(..., description="剩余时间 格式: HH:MM:SS", example="00:00:00")

class CentrifugeStatusResponse(BaseResponse):
    data: Optional[dict] = Field(default=None, description="数据")
