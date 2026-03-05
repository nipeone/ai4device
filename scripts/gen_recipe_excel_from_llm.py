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
from services.experiment_input import llm_output_to_add_task_request
from services.mixer import add_task_request_to_excel_bytes


def main():
    json_path = ROOT / "data" / "output_result-AlInS3-0303.json"
    out_path = ROOT / "recipe_from_llm_output.xlsx"

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    req = StartExperimentRequest.model_validate(data)
    add_task = llm_output_to_add_task_request(req)
    excel_bytes = add_task_request_to_excel_bytes(add_task)

    with open(out_path, "wb") as f:
        f.write(excel_bytes)
    print(f"已生成: {out_path}")


if __name__ == "__main__":
    main()
