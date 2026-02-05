from typing import Optional, Literal, List
from pydantic import BaseModel, Field, field_validator
from enum import Enum

from .base import BaseResponse

class DoorActionCode(Enum):
    '''门动作
    - OPEN: 打开
    - CLOSE: 关闭
    '''
    OPEN = 1
    CLOSE = 2

class DoorStatus(Enum):
    '''门状态
    - OPENED: 打开
    - CLOSED: 关闭
    '''
    OPENED = 1
    CLOSED = 2

class DoorActionRequest(BaseModel):
    door_id: int = Field(..., description="门ID")
    action: DoorActionCode = Field(..., description="动作")

class DoorActionResponse(BaseResponse):
    data: Optional[str] = Field(default=None, description="动作结果")

class DoorStatusResponse(BaseResponse):
    data: Optional[dict] = Field(default=None, description="门状态")