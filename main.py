import uvicorn
from app import app
import config  # 导入配置模块以加载环境变量


if __name__ == "__main__":
    uvicorn.run(app, host=config.APP_HOST, port=config.APP_PORT)