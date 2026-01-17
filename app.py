from fastapi import FastAPI
from contextlib import asynccontextmanager
from apis.centrifuge_api import router as centrifuge_router
from apis.oven_api import router as oven_router
from apis.door_api import router as door_router
from apis.plc_api import router as plc_router
from apis.flow_api import router as flow_router
from apis.task_api import router as task_router
from apis.system_api import router as system_router
from apis.mixer_api import router as mixer_router
from logger import sys_logger as logger
import config  # 导入配置模块以加载环境变量
from devices.robot_core import robot_controller
# ==========================================
# 应用生命周期管理
# ==========================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.log("系统服务启动...", "INFO")
    if not robot_controller.connect():
        logger.log(f"机器人连接失败: {robot_controller.get_message()}", "ERROR")

    yield  # 运行应用程序

    # Shutdown
    logger.log("系统服务关闭...", "INFO")


# ==========================================
# 初始化全局对象
# ==========================================
app = FastAPI(title="AGV总控系统", version="10.4", lifespan=lifespan)

# 注册各种路由
app.include_router(centrifuge_router)
app.include_router(oven_router)
app.include_router(door_router)
app.include_router(plc_router)
app.include_router(flow_router)
app.include_router(task_router)
app.include_router(system_router)
app.include_router(mixer_router)

# 根路径
@app.get("/")
def read_root():
    return {"message": "AGV总控系统 API", "status": "running"}