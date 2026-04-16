import asyncio
import sys
import uvicorn
from app import app
import config  # 导入配置模块以加载环境变量


if __name__ == "__main__":
    # Windows + Python 3.13 下，ProactorEventLoop 在客户端断连时可能抛出
    # _ProactorBasePipeTransport._call_connection_lost 的 WinError 10054。
    # 切换到 SelectorEventLoop 可避免该类噪音异常影响服务稳定性。
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    uvicorn.run(app, host=config.APP_HOST, port=config.APP_PORT, workers=1, reload=False)