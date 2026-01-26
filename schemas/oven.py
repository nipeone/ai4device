from typing import Optional, Literal, List
from pydantic import BaseModel, Field, field_validator

from .base import BaseResponse

class OvenStatus(BaseModel):
    device_name: str = Field(..., description="设备名称")
    device_address: int = Field(..., description="设备地址")
    device_type: str = Field(..., description="仪表型号")
    online_status: str = Field(..., description="在线状态")
    actual_temperature: float = Field(..., description="实际温度")
    setted_temperature: float = Field(..., description="设定温度")
    running_curve: str = Field(..., description="运行曲线")
    status_display: str = Field(..., description="状态显示")
    end_time: str = Field(..., description="结束时间")
    status: str = Field(..., description="运行状态")

class OvenStatusResponse(BaseResponse):
    data: Optional[List[OvenStatus]] = Field(default=None, description="所有炉子状态数据")