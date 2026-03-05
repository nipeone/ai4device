"""
使用 data/llm_output.json 生成配方 Excel 并保存到项目根目录（一次性测试脚本）。
"""
import json
import sys
from pathlib import Path

# 项目根目录
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from schemas.llm_output import StartExperimentRequest
from services.experiment_input import llm_output_to_curve_points, get_selected_scheme


def main():
    json_path = ROOT / "data" / "output_result-AlInSe3-0303.json"

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    req = StartExperimentRequest.model_validate(data)
    scheme = get_selected_scheme(req)
    recipe = scheme.工艺参数
    curve_points = llm_output_to_curve_points(req)

    temperature_program = (
        recipe.温度程序.model_dump(by_alias=True) if recipe and recipe.温度程序 else None
    )
    print(f"temperature_program:\n {json.dumps(temperature_program, indent=2)}")
    print(f"curve_points: \n{json.dumps([p.model_dump() for p in curve_points], indent=2)}")

if __name__ == "__main__":
    main()
