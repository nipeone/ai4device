from typing import Optional, Any, Literal
from pydantic import BaseModel, Field

class BaseResponse(BaseModel):
    code: int = Field(..., description="状态码")
    message: str = Field(..., description="消息")
    data: Optional[Any] = Field(default=None, description="数据")

    # 模型级批量配置完整示例，替代单个字段的example
    model_config = {
        "json_schema_extra": {
            "examples": [  # 复数examples，值为列表（支持多个示例）
                {
                    "code": 200,
                    "message": "操作成功",
                    "data": {"key": "value"}
                },
                {
                    "code": 400,
                    "message": "参数错误",
                    "data": None
                }
            ]
        }
    }