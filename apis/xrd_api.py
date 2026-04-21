from fastapi import APIRouter
from datetime import datetime, timedelta
from logger import sys_logger as logger

from schemas.xrd import (
    SetAutoModeRequest,
    SetVoltageCurrentRequest,
    SetPowerRequest,
    SendSampleReadyRequest,
    GetSampleDownRequest
)
from devices.xrd_core import xrd_controller

router = APIRouter(prefix="/api/xrd", tags=["xrd衍射仪"])


@router.get("/status", tags=["xrd衍射仪"])
def get_xrd_status():
    return xrd_controller.get_sample_status()

@router.post("/realtime", tags=["xrd衍射仪"])
def get_realtime_data():
    '''上样请求'''
    return xrd_controller.get_current_acquire_data()

@router.post("/start_auto_mode", tags=["xrd衍射仪"])
def start_auto_mode(request: SetAutoModeRequest):
    """启动或停止自动模式
    :param status: True-启动自动模式，False-停止自动模式
    :return: 响应字典
    """
    return xrd_controller.start_auto_mode(request.status)

@router.post("/set_voltage_current", tags=["xrd衍射仪"])
def set_voltage_current(request: SetVoltageCurrentRequest):
    """设置电压电流
    :param voltage: 电压 (kV)，范围0-40.0
    :param current: 电流 (mA)，范围0-40.0
    :return: 响应字典
    """
    if request.voltage < 0 or request.current < 0:
        return {"status": False, "message": "电压或电流不能小于0"}
    if request.voltage > 40.0 or request.current > 40.0:
        return {"status": False, "message": "电压或电流不能大于40.0"}
    return xrd_controller.set_voltage_current(request.voltage, request.current)

@router.post("/set_power", tags=["xrd衍射仪"])
def set_power(request: SetPowerRequest):
    """设置高压电源
    :param status: True-开启高压电源，False-关闭高压电源
    :return: 响应字典
    """
    if request.status:
        return xrd_controller.set_power_on()
    else:
        return xrd_controller.set_power_off()

@router.post("/get_sample_request", tags=["xrd衍射仪"])
def get_sample_request():
    """获取上样请求
    :return: 响应字典
    """
    return xrd_controller.get_sample_request()

@router.post("/send_sample_ready", tags=["xrd衍射仪"])
def send_sample_ready(request: SendSampleReadyRequest):
    """发送上样请求
    :param sample_id: 样品标识符
    :param start_theta: 起始角度（≥5°），默认10.0
    :param end_theta: 结束角度（≥5.5°，且必须大于start_theta），默认80.0
    :param increment: 角度增量（≥0.005），默认0.05
    :param exp_time: 曝光时间（0.1-5.0秒），默认0.1
    :return: 响应字典
    """
    if request.start_theta <= 5.0 or request.end_theta > 120.0 or request.increment < 0.005 or request.exp_time < 0.1 or request.exp_time > 5.0:
        return {"status": False, "message": "参数错误"}
    if request.end_theta <= request.start_theta:
        return {"status": False, "message": "结束角度必须大于起始角度"}
    if request.end_theta - request.start_theta < 10:
        return {"status": False, "message": "起始角度和结束角度之差应该≥10"}
    return xrd_controller.send_sample_ready(request.sample_id, request.start_theta, request.end_theta, request.increment, request.exp_time)

@router.post("/get_sample_down", tags=["xrd衍射仪"])
def get_sample_down(request: GetSampleDownRequest):
    """获取下样请求
    :param sample_station: 下样工位 (1-30)
    :return: 响应字典
    """
    if request.sample_station < 1 or request.sample_station > 30:
        return {"status": False, "message": "下样工位范围错误"}
    return xrd_controller.get_sample_down(request.sample_station)

@router.post("/send_sample_down_ready", tags=["xrd衍射仪"])
def send_sample_down_ready():
    """发送下样完成请求
    :return: 响应字典
    """
    return xrd_controller.send_sample_down_ready()