from fastapi import FastAPI
from contextlib import asynccontextmanager
from apis.centrifuge_api import router as centrifuge_router
from apis.oven_api import router as oven_router
from apis.door_api import router as door_router
from apis.plc_api import router as plc_router
from apis.flow_api import router as flow_router
from apis.experiment_api import router as experiment_router
from apis.system_api import router as system_router
from apis.mixer_api import router as mixer_router
from apis.xrd_api import router as xrd_router
from logger import sys_logger as logger
import config
from utils import initialize_oven_curve_db
from services.experiment_persistence import init_experiment_db
from devices.robot_core import robot_controller
from devices.mixer_core import mixer_controller
from devices.centrifuge_core import centrifuge_controller
from devices.oven_core import oven_controller
from devices.door_core import door_controller
from swagger_monkey import swagger_monkey_patch, redoc_monkey_patch
# ==========================================
# 应用生命周期管理
# ==========================================
@asynccontextmanager
async def lifespan(app: FastAPI):

    from fastapi import applications
    applications.get_swagger_ui_html = swagger_monkey_patch
    applications.get_redoc_html = redoc_monkey_patch

    # Startup
    logger.log("系统服务启动...", "INFO")
    if getattr(config, "MOCK_DEVICES", False):
        logger.log("MOCK_DEVICES 已开启，跳过设备连接，实验流程将模拟执行", "WARN")
    else:
        if not robot_controller.connect():
            logger.log(f"机器人连接失败: {robot_controller.get_message()}", "ERROR")
        if not mixer_controller.connect():
            logger.log(f"配料设备连接失败: {mixer_controller.get_message()}", "ERROR")
        if not centrifuge_controller.connect():
            logger.log(f"离心机连接失败: {centrifuge_controller.get_message()}", "ERROR")
        if not oven_controller.connect():
            logger.log(f"高温炉连接失败: {oven_controller.get_message()}", "ERROR")
        if not door_controller.connect():
            logger.log(f"玻璃门连接失败: {door_controller.get_message()}", "ERROR")

    initialize_oven_curve_db()
    init_experiment_db()
    yield  # 运行应用程序

    # Shutdown
    logger.log("系统服务关闭...", "INFO")


# ==========================================
# 初始化全局对象
# ==========================================
app = FastAPI(title="智能设备AI总控系统", version="1.0.4", lifespan=lifespan)

# 注册各种路由
app.include_router(centrifuge_router)
app.include_router(oven_router)
app.include_router(door_router)
app.include_router(plc_router)
app.include_router(flow_router)
app.include_router(experiment_router)
app.include_router(system_router)
app.include_router(mixer_router)
app.include_router(xrd_router)

# 根路径
@app.get("/")
def read_root():
    return {"message": "AGV总控系统 API", "status": "running"}

def register_static_file(app: FastAPI):
    """
    静态文件交互开发模式使用，生产使用 nginx 静态资源服务，这里是开发是方便本地
    :param app:
    :return:
    """
    import os
    from fastapi.staticfiles import StaticFiles
    app.mount("/static", StaticFiles(directory="assets/static"), name="static")

register_static_file(app)