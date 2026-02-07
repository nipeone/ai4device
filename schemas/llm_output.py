"""
大模型规范输出（实验输入）的 Schema。
与 data/llm_output.json 对应，用于 POST /api/experiment/flux 的 JSON 入参。
从中可提取：原料 -> AddTaskRequest，温度程序 -> List[CurvePoint]。
"""
from typing import Optional, List, Any
from pydantic import BaseModel, Field, ConfigDict


class TargetProduct(BaseModel):
    """目标产物信息"""
    化学式: Optional[str] = None
    结构原型: Optional[str] = None
    是否二维: Optional[bool] = None
    是否半导体: Optional[bool] = None


class ProcessRecipe(BaseModel):
    """工艺配方：用于提取配料原料"""
    生长方法: Optional[str] = None
    原料: Optional[str] = None  # 如 "Y, Er, Mn, Si"
    助熔剂信息: Optional[str] = None
    容器: Optional[str] = None
    籽晶: Optional[str] = None
    原料摩尔比_原文: Optional[str] = None
    原料摩尔比_标准化: Optional[str] = None  # 如 "RE:Mn:Si = 0.5-1.5:1:1"
    助熔剂_对_溶质_摩尔比: Optional[Any] = None
    助熔剂家族标签: Optional[List[str]] = None
    配料总总量: float = Field(default=5.0, description="配料总质量（克），默认 5g，用于按比例计算各原料 add_weight")


class TemperatureProgram(BaseModel):
    """温度程序：用于生成加热炉曲线 List[CurvePoint]"""
    model_config = ConfigDict(populate_by_name=True)
    是否存在次高温预反应段: Optional[str] = None
    升温到次高温时间_h: Optional[float] = None
    次高温段温度_摄氏: Optional[float] = None
    次高温段保温时间_h: Optional[float] = None
    升温到最高温时间_h: Optional[float] = None  # 如 4.42
    最高温段保温温度_摄氏: Optional[float] = None  # 如 1350
    最高温段保温时间_h: Optional[float] = None   # 如 5
    降温速率_主降温_摄氏度每小时: Optional[float] = Field(None, alias="降温速率_主降温_℃每小时", description="如 50")
    降温时间_主降温_h: Optional[float] = None   # 如 11
    低温段保温温度_摄氏: Optional[float] = None
    低温段保温时间_h: Optional[float] = None
    冷却速率_至室温_标签: Optional[str] = None


class StartExperimentRequest(BaseModel):
    """
    实验启动入参：大模型规范输出（实验输入）。
    必填用于配料与温度曲线的字段；其余可选，与 llm_output.json 结构兼容。
    """
    文献ID: Optional[str] = None
    配方ID: Optional[str] = Field(default=None, description="用于生成 task_name，如 rec_0002")
    实验目的: Optional[str] = Field(default=None, description="用于 task_name 或描述")
    目标产物信息: Optional[TargetProduct] = None
    工艺配方: ProcessRecipe = Field(..., description="原料与摩尔比，用于生成 AddTaskRequest")
    温度程序: TemperatureProgram = Field(..., description="用于生成加热炉曲线 List[CurvePoint]")
    分离与后处理: Optional[Any] = None
    晶体信息: Optional[Any] = None
