from typing import Optional, Any, List
from pydantic import BaseModel, Field

from .base import BaseResponse

class SampleInfo(BaseModel):
    id_number: str = Field(..., description="样品ID")
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
    id_number: str = Field(..., description="样品ID")
    theta2: List[float] = Field(..., description="2theta")
    intensity: List[float] = Field(..., description="强度")