from typing import Optional, Any, List
from pydantic import BaseModel, Field

from .base import BaseResponse

class SampleInfo(BaseModel):
    id_name: str = Field(..., description="样品ID")
    theta2: List[float] = Field(..., description="2theta")
    intensity: List[float] = Field(..., description="强度")

class XRDResultResponse(BaseModel):
    '从文档构造的XRD结果数据'
    status: bool = Field(..., description="状态")
    timestamp: str = Field(..., description="时间戳")
    message: Optional[str] = Field(default=None, description="消息")
    sample_info: Optional[SampleInfo] = Field(default=None, description="数据")

class RealXRDResultResponse(BaseModel):

    status: bool = Field(..., description="状态")
    timestamp: str = Field(..., description="时间戳")
    message: Optional[str] = Field(default=None, description="消息")
    id_name: str = Field(..., description="样品ID")
    theta2: List[float] = Field(..., description="2theta")
    intensity: List[float] = Field(..., description="强度")

class SetAutoModeRequest(BaseModel):
    status: bool = Field(..., description="True-启动自动模式，False-停止自动模式")

class SetVoltageCurrentRequest(BaseModel):
    voltage: float = Field(..., description="电压 (kV)，范围0-40.0")
    current: float = Field(..., description="电流 (mA)，范围0-40.0")

class SetPowerRequest(BaseModel):
    status: bool = Field(..., description="True-开启高压电源，False-关闭高压电源")

class GetSampleRequest(BaseModel):
    sample_id: str = Field(..., description="样品ID")
    start_theta: float = Field(..., description="起始角度")
    end_theta: float = Field(..., description="结束角度")
    increment: float = Field(..., description="步长")
    exp_time: float = Field(..., description="曝光时间")

class SendSampleReadyRequest(BaseModel):
    sample_id: str = Field(..., description="样品ID")
    start_theta: float = Field(..., description="起始角度")
    end_theta: float = Field(..., description="结束角度")
    increment: float = Field(..., description="步长")
    exp_time: float = Field(..., description="曝光时间")

class GetSampleDownRequest(BaseModel):
    sample_station: int = Field(..., description="下样工位 (1-30)")