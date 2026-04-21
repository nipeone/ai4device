import argparse
import json
import time
from typing import Any, Dict, Optional


def _load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _now() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


def _print_step(msg: str) -> None:
    print(f"[{_now()}] {msg}")


def _get_status_value(task_info: Any) -> Optional[Any]:
    """
    MixerController.get_task_info() 在主项目里返回 {"status": "success", "data": GetTaskInfoResponse}
    这里不依赖 schemas，因此同时兼容：
    - data 为 dict
    - data 为具备 .status 属性的对象（pydantic / dataclass 风格）
    """
    if task_info is None:
        return None
    if isinstance(task_info, dict):
        if "status" in task_info:
            return task_info.get("status")
        if "data" in task_info and isinstance(task_info["data"], dict):
            return task_info["data"].get("status")
    return getattr(task_info, "status", None)


def main() -> int:
    ap = argparse.ArgumentParser(description="配料设备端到端执行（仅依赖 devices/MixerController）")
    ap.add_argument("--input", required=True, help="AddTask 请求 JSON 文件路径")
    ap.add_argument("--poll-interval", type=float, default=5.0, help="轮询间隔（秒）")
    ap.add_argument("--timeout-seconds", type=float, default=7200.0, help="最大等待时长（秒）")
    ap.add_argument("--no-stop", action="store_true", help="完成后不调用 stop_task（一般不建议）")
    args = ap.parse_args()

    payload = _load_json(args.input)

    # 仅依赖 devices/ 的导入：部署时确保该目录可被 Python 找到（PYTHONPATH 或相对路径）
    from devices.mixer_core import MixerController

    mix = MixerController()

    _print_step("步骤0: 连接设备（connect）")
    if not mix.connect():
        _print_step(f"连接失败: {mix.get_message()}")
        return 2
    _print_step("连接成功")

    _print_step("步骤1: 获取设置信息（get_setup）")
    setup = mix.get_setup()
    _print_step(f"get_setup: {setup.get('status')}")
    if setup.get("status") != "success":
        _print_step(f"get_setup 失败: {setup.get('message')}")
        return 2

    _print_step("步骤2: 创建任务（add_task）")
    add_rtn = mix.add_task(payload)  # 兼容 devices 侧接受 dict 或 model
    if add_rtn.get("status") != "success":
        _print_step(f"add_task 失败: {add_rtn.get('message')}")
        return 2

    data = add_rtn.get("data")
    task_id = getattr(data, "task_id", None) if data is not None else None
    if task_id is None and isinstance(data, dict):
        task_id = data.get("task_id")
    if task_id is None:
        _print_step("add_task 返回缺少 task_id，无法继续")
        return 2
    _print_step(f"任务创建成功: task_id={task_id}")

    _print_step("步骤3: 资源/任务信息核验（get_resource_info / get_task_info）")
    r1 = mix.get_resource_info()
    _print_step(f"get_resource_info(1): {r1.get('status')}")
    info1 = mix.get_task_info(task_id)
    _print_step(f"get_task_info: {info1.get('status')}")
    r2 = mix.get_resource_info()
    _print_step(f"get_resource_info(2): {r2.get('status')}")

    _print_step("步骤4: 启动前校验（batch_check_task）")
    chk = mix.batch_check_task([task_id])
    if chk.get("status") != "success":
        _print_step(f"batch_check_task 失败: {chk.get('message')}")
        return 2
    chk_data = chk.get("data")
    chk_code = getattr(chk_data, "code", None)
    chk_prompt = getattr(chk_data, "prompt_msg", None)
    if chk_code != 200:
        _print_step(f"batch_check_task 未通过: code={chk_code}, prompt_msg={chk_prompt}")
        return 2
    _print_step("batch_check_task 通过")

    _print_step("步骤5: 启动任务（batch_start_task）")
    start = mix.batch_start_task([task_id])
    if start.get("status") != "success":
        _print_step(f"batch_start_task 失败: {start.get('message')}")
        return 2
    _print_step("启动成功，开始轮询任务状态（get_task_info）")

    t0 = time.time()
    last_print = 0.0
    prev_status = None
    while True:
        if time.time() - t0 > args.timeout_seconds:
            _print_step(f"超时退出（已等待 {int(time.time()-t0)}s），最后状态={last_status}")
            return 3

        info = mix.get_task_info(task_id)
        if info.get("status") != "success":
            _print_step(f"get_task_info 失败: {info.get('message')}")
            time.sleep(args.poll_interval)
            continue

        data = info.get("data")
        status_val = _get_status_value(data)
        curr_status = status_val

        # 控制台降噪：每 30 秒打印一次摘要
        if time.time() - last_print > 30:
            _print_step(f"任务进行中: task_id={task_id}, status={curr_status}")
            last_print = time.time()

        # 不依赖 schemas 枚举值：用“状态变化 + 结束时间字段”做弱判定，同时保留 status 原值输出
        task_end_time = getattr(data, "task_end_time", None)
        if isinstance(data, dict):
            task_end_time = data.get("task_end_time")

        # 常见完成信号：结束时间存在 或 status 进入终态（这里不硬编码枚举，仅做经验判定）
        if task_end_time is not None:
            _print_step(f"检测到 task_end_time={task_end_time}，认为任务已结束")
            break

        # 若设备侧 status 使用字符串，也允许直接识别 completed/success（尽量兼容）
        if isinstance(curr_status, str) and curr_status.lower() in {"completed", "complete", "success", "done"}:
            _print_step(f"检测到终态 status={curr_status}，认为任务已完成")
            break

        if prev_status is not None and curr_status != prev_status:
            _print_step(f"状态变化: {prev_status} -> {curr_status}")
        prev_status = curr_status

        time.sleep(args.poll_interval)

    if not args.no_stop:
        _print_step("步骤6: 收尾停止任务（stop_task）")
        stp = mix.stop_task(task_id)
        _print_step(f"stop_task: {stp.get('status') if isinstance(stp, dict) else stp}")

    _print_step("配料流程结束")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
