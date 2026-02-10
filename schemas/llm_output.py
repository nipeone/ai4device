"""
大模型规范输出（实验输入）的 Schema。
与 data/llm_output.json 对应，用于 POST /api/experiment/flux 的 JSON 入参。
从中可提取：原料 -> AddTaskRequest，温度程序 -> List[CurvePoint]。
"""
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, Field, ConfigDict

"""
{
  "目标材料": {
    "化学式": "AlInSe3",
    "结构原型": "Chalcopyrite-type",
    "是否二维": false,
    "是否半导体": true,
    "材料族系": []
  },
  "推荐实验方案列表": [
    {
      "方案ID": "方案_A",
      "方案类型": "baseline",
      "方案给人的一句话说明": "中规中矩方案：基于统计窗口的推荐值，平衡了生长时间与晶体质量，适合首轮探索。",
      "工艺参数": {
        "原料信息": "Al, In, Se (按化学计量比 1:1:3)",
        "原料标准化": "Al:In:Se=1:1:3",
        "助熔剂信息": "Na 助熔剂",
        "助熔剂标准化": "Na:(Al+In+Se)=2.7:1",
        "容器": "Alumina crucible",
        "籽晶": "Not specified",
        "温度程序": {
          "是否存在次高温预反应段": "否",
          "升温到次高温时间_h": 11.5,
          "次高温段温度_摄氏": 600.0,
          "次高温段保温时间_h": 2.0,
          "升温到最高温时间_h": 1.0,
          "最高温段保温温度_摄氏": 870.0,
          "最高温段保温时间_h": 24.0,
          "降温速率_主降温_℃每小时": 1.8,
          "降温时间_主降温_h": 150.0,
          "低温段保温温度_摄氏": 600.0,
          "低温段保温时间_h": 0.0,
          "冷却速率_至室温_标签": "炉冷"
        },
        "分离与后处理": {
          "分离方式": "Dissolution in ethanol and water",
          "分离温度_摄氏": 25.0,
          "晶体的进一步处理": "Washing with ethanol and water, dried at 65°C"
        }
      },
      "预期结果标签": {
        "预期晶体尺寸": "mm 级",
        "预期风险水平": "低",
        "风险来源简述": [
          "参数接近统计均值，风险可控。",
          "降温速率适中，不易产生热应力开裂。"
        ]
      },
      "溯源信息": {
        "主要参考配方ID": [
          "rec_0282",
          "rec_0322"
        ],
        "参考材料ID-化学式": [
          "mat_273-ZnSiP2",
          "mat_315-ZnSnP2"
        ],
        "参考方案类型ID-名称": [
          "scheme_001-高助熔剂稀释慢冷方案"
        ]
      }
    }]
}
"""

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


class TargetMaterial(BaseModel):
    """目标材料信息"""
    化学式: Optional[str] = None
    结构原型: Optional[str] = None
    是否二维: Optional[bool] = None
    是否半导体: Optional[bool] = None
    材料族系: Optional[List[str]] = []

class ProcessRecipe(BaseModel):
    """工艺配方：用于提取配料原料"""
    原料信息: Optional[str] = None
    原料标准化: Optional[str] = None
    助熔剂信息: Optional[str] = None
    助熔剂标准化: Optional[str] = None
    容器: Optional[str] = None
    籽晶: Optional[str] = None
    温度程序: Optional[TemperatureProgram] = None
    分离与后处理: Optional[Any] = None

class RecommendExperimentScheme(BaseModel):
    """推荐实验方案信息"""
    方案ID: Optional[str] = None
    方案类型: Optional[str] = None
    方案给人的一句话说明: Optional[str] = None
    工艺参数: Optional[ProcessRecipe] = None
    预期结果标签: Optional[Dict[str, Any]] = None
    溯源信息: Optional[Dict[str, Any]] = None

class StartExperimentRequest(BaseModel):
    """
    实验启动入参：大模型规范输出（实验输入）。
    与 data/llm_output.json 结构一致：目标材料 + 推荐实验方案列表。
    使用 方案索引 指定运行第几个方案（默认 0）。
    """
    目标材料: Optional[TargetMaterial] = None
    推荐实验方案列表: Optional[List[RecommendExperimentScheme]] = []
    整体备注: Optional[List[str]] = []
    方案索引: Optional[int] = Field(default=0, description="使用推荐实验方案列表中的第几个方案（从 0 开始）")
