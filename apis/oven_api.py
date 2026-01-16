from fastapi import APIRouter
from datetime import datetime, timedelta
from logger import sys_logger as logger

# 导入全局实例
from devices.furnace_core import oven_driver

router = APIRouter(prefix="/api/oven", tags=["炉子"])

# ==========================================
# 2. 炉子模块
# ==========================================
@router.get("/status", tags=["炉子"])
def get_oven_status():
    devices_list = oven_driver.get_device_list()
    realtime_map = oven_driver.get_realtime_data(duration=10.0)
    summary_result = []
    for device in devices_list:
        sid = int(device.get('SlaveID') or device.get('SlaveId') or device.get('ID') or 0)
        item = {"设备名称": device.get('DeviceName') or f"J{sid:02d}", "设备地址": sid,
                "仪表型号": device.get('DeviceType') or "858P", "在线状态": "离线", "实际温度": 0.0, "设定温度": 0.0,
                "运行曲线": "-", "状态显示": "无数据", "结束时间": "-", "状态": "未知"}
        rt_data = realtime_map.get(sid)
        if rt_data:
            detail = oven_driver.get_specific_device_info(sid)
            curve_name = detail.get('CurrentRunName') or detail.get('CurrentRun') or detail.get('CurrentWave') or "-"
            item["在线状态"] = "在线";
            item["实际温度"] = rt_data['pv'];
            item["设定温度"] = rt_data['sv'];
            item["运行曲线"] = curve_name;
            item["状态"] = "停止" if rt_data['status'] == 1 else "运行"
            minutes = rt_data['runtime_raw']
            if item["仪表型号"] == "858P": minutes /= 10.0
            item["状态显示"] = f"阶段{rt_data['step']} 剩余{(minutes / 60.0):.1f}h"
            if minutes > 0: item["结束时间"] = (datetime.now() + timedelta(minutes=minutes)).strftime("%Y-%m-%d %H:%M")
        summary_result.append(item)
    return {"设备列表": summary_result}


@router.post("/{id}/{action}", tags=["炉子"])
def control_oven(id: int, action: int):
    logger.log(f"炉子手动操作: ID={id}, Action={action}", "INFO")
    success, msg = oven_driver.control_lid(id, action)
    if not success: logger.log(f"炉子操作失败: {msg}", "ERROR")
    return {"status": success, "msg": msg}