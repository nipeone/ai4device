from fastapi import APIRouter, Body
import time
from snap7.type import Area
from logger import sys_logger as logger

# 导入全局实例
from devices.plc_manager import plc_mgr

router = APIRouter(prefix="/api/plc", tags=["PLC"])

# ==========================================
# 4. PLC 模块
# ==========================================
@router.get("/status", tags=["PLC"])
def get_plc_status():
    """获取 PLC 连接及机器人状态。
        第 1 个值 (Index 0): 对应 M10.0 (任务下发) -> false (未触发)。
        第 2 个值 (Index 1): 对应 M10.1 (任务清除) -> false。
        第 3 个值 (Index 2): 对应 M10.2 (开玻璃门) -> false。
        第 4 个值 (Index 3): 对应 M10.3 (开加热炉) -> false。
        第 5 个值 (Index 4): 对应 M10.4 (开离心机门) -> false。
        第 6 个值 (Index 5): 对应 M10.5 (机器人停止) -> true。(触发)。
         DB1.218.0 (原点状态) - 1=原点。
         DB1.218.1 (夹具状态) - 1=打开。
         DB1.242 (系统状态) - 0=断线, 1=空闲, 2=执行中, 3=完成, 4=失败。
         DB2.40 (任务状态) - 0=无任务, 1=有任务。"""
    # 注意：此处不频繁调用 log，避免日志刷屏，仅在连接状态变化时由 try_connect 记录
    plc_mgr.try_connect()
    return {
        "PLC连接状态": plc_mgr.connected,
        "M 区控制信号状态": [plc_mgr.read_m(10, i) for i in range(7)],
        "任务数据": {"工号": plc_mgr.read_db_int(3, 0), "工位类型/炉号": plc_mgr.read_db_int(3, 2),
                     "数量": plc_mgr.read_db_int(3, 4)},
        "robot": {
            "原点状态": plc_mgr.read_db_bit(1, 218, 0),
            "夹具状态": plc_mgr.read_db_bit(1, 218, 1),
            "系统状态": plc_mgr.read_db_int(1, 242, 4),
            "机器人启动/暂停": plc_mgr.read_db_bit(2, 18, 4),
            "任务状态": plc_mgr.read_db_int(2, 40, 4)
        }
    }


@router.post("/task", tags=["PLC"])
def set_task(tid: int = Body(...), st: int = Body(...), qty: int = Body(...)):
    """写入 PLC 任务数据 (底层接口)。
手动向 DB3 写入任务。需在 Body 中填写 tid (任务ID), st (站点), qty (数量)。一般仅供调试使用。"""
    return plc_mgr.write_task(tid, st, qty)


@router.post("/toggle_m/{bit}", tags=["PLC"])
def toggle_m(bit: int):
    """翻转M区信号。
    在bit输入位地址(0 - 5)，执行后将对应的M10.x信号取反。M10.0	任务下发	标签3	反转控制
M10.1	任务清除	标签8	反转控制
M10.2	开玻璃门	标签7	反转控制
M10.3   开加热炉    标签1   反转控制
M10.4   开离心机门  标签2   反转控制
M10.5	机器人停止	标签13	反转控制。"""
    return plc_mgr.toggle_m(10, bit)


@router.post("/pulse_m/{bit}", tags=["PLC"])
def pulse_m(bit: int):
    """"""
    return plc_mgr.pulse_m(10, bit)


@router.post("/robot/{action}", tags=["PLC"])
def robot_act(action: str):
    """控制 DB2 块中的机器人专用信号。
在 action 参数中输入以下指令：
reset: 对应 DB2.18.0 (机器人复位)。瞬动控制，用于清除机器人报警。
toggle: 对应 DB2.18.4 (机器人启动/暂停)。反转控制，切换机器人的运行/暂停状态。"""

    if not plc_mgr.try_connect():
        logger.log(f"机器人操作{action}失败: PLC未连接", "ERROR")
        return False
    try:
        logger.log(f"发送机器人指令: {action}", "INFO")
        if action == "reset":
            plc_mgr.client.write_area(Area.DB, 2, 18, b'\x01')
            time.sleep(0.5)
            plc_mgr.client.write_area(Area.DB, 2, 18, b'\x00')
        elif action == "toggle":
            d = plc_mgr.client.read_area(Area.DB, 2, 18, 1)
            v = bytearray(d)
            if (v[0] >> 4) & 1:
                v[0] &= ~(1 << 4)
            else:
                v[0] |= (1 << 4)
            plc_mgr.client.write_area(Area.DB, 2, 18, v)
    except Exception as e:
        plc_mgr.connected = False
        logger.log(f"机器人指令异常: {e}", "ERROR")