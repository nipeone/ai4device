from typing import Literal
from fastapi import APIRouter, Body, HTTPException
import time
from snap7.type import Area
from logger import sys_logger as logger

# 导入全局实例
from devices.robot_core import robot_controller

router = APIRouter(prefix="/api/plc", tags=["PLC"])

# ==========================================
# 4. PLC 模块
# ==========================================
@router.get("/status", tags=["PLC"])
def get_plc_status():
    """获取 PLC 连接及机器人状态。
        第 1 个值 (Index 0): 对应 M10.0 (任务下发) -> false (未触发)
        第 2 个值 (Index 1): 对应 M10.1 (任务清除) -> false
        第 3 个值 (Index 2): 对应 M10.2 (开玻璃门) -> false
        第 4 个值 (Index 3): 对应 M10.3 (开加热炉) -> false
        第 5 个值 (Index 4): 对应 M10.4 (开离心机门) -> false
        第 6 个值 (Index 5): 对应 M10.5 (机器人停止) -> true (触发)
         DB1.218.0 (原点状态) - 1=原点
         DB1.218.1 (夹具状态) - 1=打开
         DB1.242 (系统状态) - 0=断线, 1=空闲, 2=执行中, 3=完成, 4=失败
         DB2.40 (任务状态) - 0=无任务, 1=有任务"""
    # 注意：此处不频繁调用 log，避免日志刷屏，仅在连接状态变化时由 connect 记录
    return robot_controller.get_status()


@router.post("/task", tags=["PLC"])
def set_task(tid: int = Body(...), st: int = Body(...), qty: int = Body(...)):
    """写入 PLC 任务数据 (底层接口)。
    手动向 DB3 写入任务。需在 Body 中填写 tid (任务ID), st (站点), qty (数量)。一般仅供调试使用。"""
    success = robot_controller.write_task(tid, st, qty)
    if not success:
        raise HTTPException(status_code=500, detail=f"写入任务数据失败")
    return {"success": success}


@router.post("/toggle_m/{bit}", tags=["PLC"])
def toggle_m(bit: int):
    """翻转控制M10.x区信号。在bit输入位地址(0 - 5)，执行后将对应的M10.x信号取反。
    M10.0: 任务下发	标签3	反转控制
    M10.1: 任务清除	标签8	反转控制
    M10.2: 开玻璃门	标签7	反转控制
    M10.3: 开加热炉    标签1   反转控制
    M10.4: 开离心机门  标签2   反转控制
    M10.5: 机器人停止	标签13	反转控制。
    返回值: 是否成功
    """
    if bit < 0 or bit > 5:
        raise ValueError("bit 必须在 0 到 5 之间")
    success = robot_controller.toggle_m(10, bit)
    if not success:
        raise HTTPException(status_code=500, detail=f"翻转控制M10.{bit}区信号失败")
    return {"success": success}


@router.post("/pulse_m/{bit}", tags=["PLC"])
def pulse_m(bit: int):
    """点动控制M10.x区信号。
    在bit输入位地址(0 - 5)，执行后将对应的M10.x信号置位1 -> 等待0.5s -> 复位0 (安全模式)。"""
    if bit < 0 or bit > 5:
        raise ValueError("bit 必须在 0 到 5 之间")
    success = robot_controller.pulse_m(10, bit)
    if not success:
        raise HTTPException(status_code=500, detail=f"点动控制M10.{bit}区信号失败")
    return {"success": success}


@router.post("/robot/{action}", tags=["PLC"])
def robot_act(action: Literal["reset", "toggle"]):
    """控制 DB2 块中的机器人专用信号。
    在 action 参数中输入以下指令：
    reset: 对应 DB2.18.0 (机器人复位)。瞬动控制，用于清除机器人报警。
    toggle: 对应 DB2.18.4 (机器人启动/暂停)。反转控制，切换机器人的运行/暂停状态。"""

    if action not in ["reset", "toggle"]:
        raise HTTPException(status_code=400, detail=f"无效的机器人指令: {action}")

    if not robot_controller.connect():
        raise HTTPException(status_code=500, detail=f"机器人操作{action}失败: PLC未连接")

    success = False
    if action == "reset":
        success = robot_controller.reset_robot()
    elif action == "toggle":
        success = robot_controller.toggle_robot()
    else:
        raise HTTPException(status_code=400, detail=f"无效的机器人指令: {action}")
    logger.log(f"发送机器人指令: {action}", "INFO")
    if not success:
        raise HTTPException(status_code=500, detail=f"机器人指令{action}失败")
    return {"success": success}