from typing import Optional, Literal, List
from pydantic import BaseModel, Field, field_validator
from enum import Enum

from .base import BaseResponse

class DoorActionCode(Enum):
    open = 1
    close = 2

class DoorActionRequest(BaseModel):
    door_id: int = Field(..., description="门ID")
    action: DoorActionCode = Field(..., description="动作", example=DoorActionCode.open)

class DoorActionResponse(BaseResponse):
    data: Optional[str] = Field(default=None, description="动作结果")

class DoorStatusResponse(BaseResponse):
    data: Optional[dict] = Field(default=None, description="门状态")