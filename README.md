# AGV总控系统

这是一个基于FastAPI开发的自动化控制系统，用于控制AGV（自动导引车）及相关设备，包括离心机、炉子和玻璃门等设备。

## 架构概览

```
AGV总控系统
├── app.py                  # 主应用文件，包含FastAPI应用实例
├── main.py                 # 主入口文件，启动FastAPI服务器
├── apis/                   # API路由模块目录
│   ├── centrifuge_api.py   # 离心机API路由
│   ├── oven_api.py         # 炉子API路由
│   ├── door_api.py         # 玻璃门API路由
│   ├── plc_api.py          # PLC控制API路由
│   ├── flow_api.py         # 流程管理API路由
│   ├── task_api.py         # 任务管理API路由
│   └── system_api.py       # 系统API路由
├── utils.py                # 工具函数和常量定义
├── logger.py               # 系统日志管理器
├── devices/
│   ├── door_core.py        # 玻璃门控制模块
│   ├── centrifuge_core.py  # 离心机控制模块
│   ├── furnace_core.py     # 炉子控制模块
│   ├── mixer_core.py       # 配料设备控制模块
│   └── mixer_api.py        # 配料设备API路由
├── schemas/                # 数据模型定义
│   └── add_task.py         # 任务数据模型
├── services/               # 业务逻辑服务
│   └── mixer_task.py       # 配料任务服务
├── docker/
│   ├── Dockerfile          # Docker构建文件
│   └── docker-compose.yaml # Docker Compose配置文件
└── README.md               # 项目说明文档
```

## 模块说明

### 1. app.py

- **功能**: 主应用文件，包含FastAPI应用实例
- **作用**: 定义FastAPI应用实例，注册所有API路由

### 2. main.py

- **功能**: 项目的主入口文件
- **作用**: 启动FastAPI服务器，监听指定端口

### 3. apis/文件夹

- **功能**: 存放所有API路由模块
- **包含**:
  - `centrifuge_api.py`: 离心机相关API路由
  - `oven_api.py`: 炉子相关API路由
  - `door_api.py`: 玻璃门相关API路由
  - `plc_api.py`: PLC控制相关API路由
  - `flow_api.py`: 流程管理相关API路由
  - `task_api.py`: 任务管理相关API路由
  - `system_api.py`: 系统相关API路由

### 4. utils.py

- **功能**: 存放工具函数和常量定义
- **包含**:
  - `cent_format_time`: 离心机时间格式化函数
  - 离心机命令字典及状态映射

### 5. logger.py

- **功能**: 系统日志管理器
- **提供**: 统一的日志记录和管理功能

### 6. devices/文件夹

- **功能**: 存放各类设备控制模块
- **包含**:
  - `door_core.py`: 玻璃门控制模块
  - `centrifuge_core.py`: 离心机控制模块
  - `furnace_core.py`: 炉子控制模块
  - `mixer_core.py`: 配料设备控制模块
  - `mixer_api.py`: 配料设备API路由

### 7. schemas/文件夹

- **功能**: 存放数据模型定义
- **包含**:
  - `add_task.py`: 任务数据模型定义

### 8. services/文件夹

- **功能**: 存放业务逻辑服务
- **包含**:
  - `mixer_task.py`: 配料任务处理服务

### 9. docker/文件夹

- **功能**: Docker相关配置文件
- **包含**:
  - `Dockerfile`: Docker构建文件
  - `docker-compose.yaml`: Docker Compose配置文件

## API端点分类

### 配料设备模块 (`/mixer/*`)

- `/mixer/status` - 获取配料设备状态
- `/mixer/connect` - 连接配料设备
- `/mixer/disconnect` - 断开配料设备连接
- `/mixer/start-mixing` - 开始搅拌
- `/mixer/stop-mixing` - 停止搅拌
- `/mixer/add-material` - 添加原料
- `/mixer/discharge` - 排料
- `/mixer/reset` - 重置设备

### 任务模块 (`/api/task/*`)

- `/api/task/experiment` - 上传Excel文件并解析为任务模型

### 离心机模块 (`/api/centrifuge/*`)

- `/api/centrifuge/status` - 获取离心机状态
- `/api/centrifuge/{action}` - 控制离心机操作
- `/api/centrifuge/speed/{rpm}` - 设置离心机转速

### 炉子模块 (`/api/oven/*`)

- `/api/oven/status` - 获取炉子状态
- `/api/oven/{id}/{action}` - 控制指定炉子

### 玻璃门模块 (`/api/door/*`)

- `/api/door/status` - 获取玻璃门状态
- `/api/door/{id}/{action}` - 控制指定玻璃门

### PLC模块 (`/api/plc/*`)

- `/api/plc/status` - 获取PLC连接状态
- `/api/plc/task` - 设置PLC任务数据
- `/api/plc/toggle_m/{bit}` - 翻转M区信号
- `/api/plc/pulse_m/{bit}` - 点动控制M区信号
- `/api/plc/robot/{action}` - 控制机器人信号

### 流程管理模块 (`/api/flow/*`)

- `/api/flow/confirm_continue` - 流程确认继续
- `/api/flow/start_input` - 启动上料流程
- `/api/flow/start_output` - 启动出料流程
- `/api/flow/status` - 获取流程状态

### 系统模块 (`/api/system/*`)

- `/api/system/logs` - 获取系统日志

## 运行方式

### 直接运行

```bash
python main.py
```

服务将在 `http://0.0.0.0:8113` 上启动。

### Docker运行

#### 构建和运行Docker容器

1. 确保已安装Docker和Docker Compose
2. 进入项目根目录
3. 构建并启动服务：

```bash
cd docker
docker-compose up --build
```

#### 后台运行

```bash
docker-compose up -d
```

#### 停止服务

```bash
docker-compose down
```

## 依赖项

- FastAPI
- python-snap7 (用于PLC通信)
- uvicorn (ASGI服务器)
- 其他相关硬件控制库

## 特性

1. **模块化设计**: 控制逻辑与API路由分离，便于维护
2. **实时监控**: 提供设备状态实时监控功能
3. **流程自动化**: 支持复杂的自动化流程控制
4. **安全机制**: 包含确认机制和错误处理
5. **日志记录**: 提供详细的系统日志
6. **容器化部署**: 支持Docker和Docker Compose部署