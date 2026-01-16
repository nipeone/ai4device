from fastapi import APIRouter
import struct
from utils import cent_format_time, CENT_CMDS, CENT_FAULT_MAP, CENT_RUN_MAP, \
    CENT_ROTOR_MAP, CENT_DOOR_MAP
from logger import sys_logger as logger

# 导入全局实例
from devices.centrifuge_core import cent_sender

router = APIRouter(prefix="/api/centrifuge", tags=["离心机"])

# ==========================================
# 1. 离心机模块
# ==========================================

@router.get("/status", tags=["离心机"])
def get_centrifuge_status():
    raw_res = cent_sender.send_raw(CENT_CMDS["read_all"])
    if raw_res["status"] != "success": return raw_res
    data = raw_res["bytes"]
    if len(data) < 33: return {"error": "数据不完整"}

    def gv(i):
        return struct.unpack('>H', bytes(data[3 + i * 2:3 + i * 2 + 2]))[0]

    actual_rpm = gv(1);
    fault_code = gv(4);
    run_state = gv(5);
    door_window = gv(6);
    door_lid = gv(11);
    rotor_state = gv(12);
    remain_time = gv(13)
    return {
        "面板数据": {"当前转速": f"{actual_rpm} RPM", "剩余时间": cent_format_time(remain_time),
                     "运行状态": CENT_RUN_MAP.get(run_state, f"未知({run_state})"),
                     "机器状态文字": CENT_ROTOR_MAP.get(rotor_state, "静止")},
        "门状态对比": {"1_门窗状态(2206H)": CENT_DOOR_MAP.get(door_window, f"未知代码:{door_window}")},
        "安全监控": {"故障状态": CENT_FAULT_MAP.get(fault_code, f"未知故障码: {fault_code}"),
                     "最终判定安全": (fault_code == 0) and (door_window == 2 or door_lid == 2)},
        "详细参数": {"实际转速_raw": actual_rpm, "实际离心力": gv(2), "设置转速": gv(8), "设置时间": gv(9),
                     "运行时间": gv(3)}
    }


@router.post("/{action}", tags=["离心机"])
def control_centrifuge(action: str):
    logger.log(f"离心机手动操作: {action}", "INFO")
    if action in CENT_CMDS: cent_sender.send_raw(CENT_CMDS[action])
    return {"action": action}


@router.post("/speed/{rpm}", tags=["离心机"])
def set_cent_speed(rpm: int):
    cmd = cent_sender.build_write_command(0x2101, rpm)
    return cent_sender.send_raw(cmd)