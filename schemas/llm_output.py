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
    has_pre_high_temperature_reaction_segment: Optional[str] = Field(None, description="是否存在次高温预反应段", alias="是否存在次高温预反应段")
    ramp_to_sub_hight_termperature_time_h: Optional[float] = Field(None, description="升温到次高温时间_h", alias="升温到次高温时间_h")
    sub_high_temperature_temperature_celsius: Optional[float] = Field(None, description="次高温段温度_摄氏", alias="次高温段温度_摄氏")
    sub_high_temperature_hold_time_h: Optional[float] = Field(None, description="次高温段保温时间_h", alias="次高温段保温时间_h")
    ramp_to_high_temperature_time_h: Optional[float] = Field(None, description="升温到最高温时间_h", alias="升温到最高温时间_h")
    high_temperature_hold_temperature_celsius: Optional[float] = Field(None, description="最高温段保温温度_摄氏", alias="最高温段保温温度_摄氏")
    high_temperature_hold_time_h: Optional[float] = Field(None, description="最高温段保温时间_h", alias="最高温段保温时间_h")
    main_cooling_rate_celsius_per_hour: Optional[float] = Field(None, description="降温速率_主降温_℃每小时", alias="降温速率_主降温_℃每小时")
    main_cooling_time_h: Optional[float] = Field(None, description="降温时间_主降温_h", alias="降温时间_主降温_h")
    low_temperature_hold_temperature_celsius: Optional[float] = Field(None, description="低温段保温温度_摄氏", alias="低温段保温温度_摄氏")
    low_temperature_hold_time_h: Optional[float] = Field(None, description="低温段保温时间_h", alias="低温段保温时间_h")
    cool_to_room_temperature_label: Optional[str] = Field(None, description="冷却速率_至室温_标签", alias="冷却速率_至室温_标签")


class TargetMaterial(BaseModel):
    """目标材料信息"""
    chemical_formula: Optional[str] = Field(None, description="化学式", alias="化学式")
    structure_prototype: Optional[str] = Field(None, description="结构原型", alias="结构原型")
    is_two_dimensional: Optional[bool] = Field(None, description="是否二维", alias="是否二维")
    is_semiconductor: Optional[bool] = Field(None, description="是否半导体", alias="是否半导体")
    material_family: Optional[List[str]] = Field([], description="材料族系", alias="材料族系")

class ProcessRecipe(BaseModel):
    """工艺配方：用于提取配料原料"""
    raw_material_info: Optional[str] = Field(None, description="原料信息", alias="原料信息")
    raw_material_standardization: Optional[str] = Field(None, description="原料标准化", alias="原料标准化")
    flux_info: Optional[str] = Field(None, description="助熔剂信息", alias="助熔剂信息")
    flux_standardization: Optional[str] = Field(None, description="助熔剂标准化", alias="助熔剂标准化")
    container: Optional[str] = Field(None, description="容器", alias="容器")
    seed_crystal: Optional[str] = Field(None, description="籽晶", alias="籽晶")
    temperature_program: Optional[TemperatureProgram] = Field(None, description="温度程序", alias="温度程序")
    separation_and_post_processing: Optional[Any] = Field(None, description="分离与后处理", alias="分离与后处理")

class RecommendExperimentScheme(BaseModel):
    """推荐实验方案信息"""
    scheme_id: Optional[str] = Field(None, description="方案ID", alias="方案ID")
    scheme_type: Optional[str] = Field(None, description="方案类型", alias="方案类型")
    scheme_description: Optional[str] = Field(None, description="方案给人的一句话说明", alias="方案给人的一句话说明")
    process_recipe: Optional[ProcessRecipe] = Field(None, description="工艺参数", alias="工艺参数")
    expected_result_label: Optional[Dict[str, Any]] = Field(None, description="预期结果标签", alias="预期结果标签")
    source_info: Optional[Dict[str, Any]] = Field(None, description="溯源信息", alias="溯源信息")

class RecommendExperimentRecipes(BaseModel):
    """
    实验启动入参：大模型规范输出（实验输入），与 data/llm_output.json 结构一致。
    recommend_schemes 的顺序即试管序号：配料按该列表顺序出料，加热/离心/XRD 与同一序号对应。
    """
    target_material: Optional[TargetMaterial] = Field(None, description="目标材料", alias="目标材料")
    recommend_schemes: Optional[List[RecommendExperimentScheme]] = Field([], description="推荐实验方案列表", alias="推荐实验方案列表")
    overall_notes: Optional[List[str]] = Field([], description="整体备注", alias="整体备注")
