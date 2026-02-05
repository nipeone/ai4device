from typing import Optional, Literal, List
from pydantic import BaseModel, Field, field_validator
from enum import Enum

from .base import BaseResponse

class OvenActionCode(Enum):
    '''炉子动作
    - START: 启动
    - STOP: 停止
    - PAUSE: 暂停
    '''
    START = 0
    STOP = 1
    PAUSE = 2

class OvenLidActionCode(Enum):
    '''炉盖动作
    - OPEN: 打开
    - CLOSE: 关闭
    '''
    OPEN = 1
    CLOSE = 2

class OvenLidStatus(Enum):
    '''炉盖状态
    - OPENED: 打开
    - CLOSED: 关闭
    '''
    OPENED = 1
    CLOSED = 2

class OvenStatus(Enum):
    '''炉子工作状态
    - RUNNING: 运行中
    - STOPPED: 停止
    - PAUSED: 暂停
    '''
    RUNNING = 0
    STOPPED = 1
    PAUSED = 2

class OvenActionRequest(BaseModel):
    oven_id: int = Field(..., description="炉子ID")
    action: OvenActionCode = Field(..., description="动作")

class OvenLidActionRequest(BaseModel):
    oven_id: int = Field(..., description="炉子ID")
    action: OvenLidActionCode = Field(..., description="动作")

class OvenActionResponse(BaseResponse):
    data: Optional[str] = Field(default=None, description="动作结果")

class OvenSystemStatus(BaseModel):
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

class OvenCurveListItem(BaseModel):
    id: int = Field(..., description="曲线ID")
    curve_name: str = Field(..., description="曲线名称")
    save_time: str = Field(..., description="保存时间")

class OvenStatusResponse(BaseResponse):
    data: Optional[List[OvenSystemStatus]] = Field(default=None, description="所有炉子状态数据")

class CurvePoint(BaseModel):
    temperature: float = Field(default=0.0, description="温度")
    time: float = Field(default=0.0, description="时间")

class OvenCurveResponse(BaseResponse):
    data: Optional[List[CurvePoint]] = Field(default=None, description="曲线点数据")

class OvenCurveListResponse(BaseResponse):
    data: Optional[List[OvenCurveListItem]] = Field(default=None, description="曲线列表数据")

class OvenCurveRequest(BaseModel):
    oven_id: int = Field(..., description="炉子ID")
    curve_name: str = Field(default=None, description="曲线名称，如果不填则不保存")
    points: List[CurvePoint] = Field(
        default=[CurvePoint(temperature=0.0, time=0.0) for _ in range(10)],
        description="曲线点列表，包含温度和时间。建议上传10段数据。")

class OvenCurveByNameRequest(BaseModel):
    oven_id: int = Field(..., description="炉子ID")
    curve_name: str = Field(..., description="曲线名称")
