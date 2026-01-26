from typing import Optional, Any
from pydantic import BaseModel, Field

class BaseResponse(BaseModel):
    code: int = Field(..., description="状态码", example=200)
    message: str = Field(..., description="消息", example="操作成功")
    data: Optional[Any] = Field(default=None, description="数据")