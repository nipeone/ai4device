import argparse
import json
from typing import Any, Dict, List, Tuple


def _err(path: str, msg: str) -> str:
    return f"{path}: {msg}"


def _require(obj: Dict[str, Any], key: str, path: str) -> Tuple[bool, Any, List[str]]:
    if key not in obj:
        return False, None, [_err(path, f"缺少字段 `{key}`")]
    return True, obj[key], []


def validate_add_task_payload(payload: Dict[str, Any]) -> List[str]:
    errs: List[str] = []

    ok, task_id, e = _require(payload, "task_id", "$")
    errs += e
    if ok and not isinstance(task_id, int):
        errs.append(_err("$.task_id", "应为 int（新建任务通常为 0）"))

    ok, task_name, e = _require(payload, "task_name", "$")
    errs += e
    if ok and (not isinstance(task_name, str) or not task_name.strip()):
        errs.append(_err("$.task_name", "应为非空字符串"))

    ok, task_type, e = _require(payload, "type", "$")
    errs += e
    if ok and not isinstance(task_type, int):
        errs.append(_err("$.type", "应为 int"))

    ok, layout_list, e = _require(payload, "layout_list", "$")
    errs += e
    if ok and not isinstance(layout_list, list):
        errs.append(_err("$.layout_list", "应为 list"))
        return errs

    if ok and isinstance(layout_list, list) and len(layout_list) == 0:
        errs.append(_err("$.layout_list", "不能为空"))
        return errs

    for i, unit in enumerate(layout_list):
        p = f"$.layout_list[{i}]"
        if not isinstance(unit, dict):
            errs.append(_err(p, "应为 object"))
            continue

        for k in ["resource_type", "unit_type", "unit_id", "process_json"]:
            ok_k, v, e = _require(unit, k, p)
            errs += e
            if ok_k and k in ("resource_type", "unit_type", "unit_id"):
                if not isinstance(v, str) or not v.strip():
                    errs.append(_err(f"{p}.{k}", "应为非空字符串"))

        if "process_json" in unit and isinstance(unit["process_json"], dict):
            pj = unit["process_json"]
            pjp = f"{p}.process_json"
            for k in ["substance", "chemical_id", "add_weight"]:
                ok_k, v, e = _require(pj, k, pjp)
                errs += e
                if ok_k and k == "substance" and (not isinstance(v, str) or not v.strip()):
                    errs.append(_err(f"{pjp}.substance", "应为非空字符串"))
                if ok_k and k == "chemical_id" and not isinstance(v, int):
                    errs.append(_err(f"{pjp}.chemical_id", "应为 int"))
                if ok_k and k == "add_weight" and not isinstance(v, (int, float)):
                    errs.append(_err(f"{pjp}.add_weight", "应为 number"))
        else:
            errs.append(_err(f"{p}.process_json", "应为 object"))

    return errs


def main() -> int:
    ap = argparse.ArgumentParser(description="配料 AddTask payload 结构校验（离线）")
    ap.add_argument("--input", required=True, help="AddTask 请求 JSON 文件路径")
    args = ap.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        payload = json.load(f)

    errs = validate_add_task_payload(payload)
    if errs:
        print("校验失败：")
        for e in errs:
            print(f"- {e}")
        return 2

    print("校验通过：payload 结构满足最小要求。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
