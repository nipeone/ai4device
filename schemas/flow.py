from pydantic import BaseModel, Field
from .base import BaseResponse

class StartXRDTestRequest(BaseModel):
    sample_id: str = Field(..., description="样品ID")
    start_theta: float = Field(..., description="起始角度")
    end_theta: float = Field(..., description="结束角度")
    increment: float = Field(..., description="步长")
    exp_time: float = Field(..., description="曝光时间")