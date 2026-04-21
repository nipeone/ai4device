---
name: experiment-mixer-skill
description: 用于配料设备任务创建、启动、监控和收尾的标准化技能，覆盖接口调用顺序、参数校验、异常处理与结果汇报。
---

# 配料实验技能（Mixer Experiment Skill）

## 适用场景
- 用户希望执行配料任务的完整流程（新建任务、启动任务、跟踪状态、结束任务）。
- 用户提供了配方/任务参数，希望转换为 `AddTaskRequest` 并下发到配料设备。
- 用户希望排查配料流程失败原因（连接失败、任务校验失败、启动失败、超时、状态异常）。

## 核心目标
- 严格遵循设备侧工作流顺序，避免越步骤调用导致任务失败。
- 在每个关键步骤给出明确的执行结果、失败原因和下一步建议。
- 对长时任务进行可观测轮询，直到完成或超时退出。

## 依赖上下文（脱离主项目部署）
- 仅依赖：`devices/mixer_core.py` 中 `MixerController` 暴露的方法能力。
- 不依赖：`flows/`、`schemas/`、主项目中的工作流管理器实现。
- 输入约束：由调用方提供“可被 `add_task()` 接收的任务对象/字典”，skill 只约束字段语义与流程顺序，不绑定项目内模型类。

## 标准执行流程（必须按顺序）
1. **设备就绪**
   - 检查 `mix_controller.is_connected`。
   - 若未连接，先执行 `connect()` 获取 Token。
   - 连接失败立即返回，不进入后续步骤。

2. **初始化查询**
   - 调用 `get_setup()`（对应 `/api/GetSetUp`）确认设备配置可读取。

3. **创建任务**
   - 调用 `add_task(add_task_request)`（对应 `/api/AddTask`）。
   - 返回成功后提取 `task_id`，作为后续唯一任务标识。
   - 若 `status != success` 或业务 `code != 200`，立即失败退出。

4. **创建后状态核验**
   - 调用 `get_resource_info()`（第一次资源检查）。
   - 调用 `get_task_info(task_id)`（确认任务状态可读取）。
   - 再次调用 `get_resource_info()`（第二次资源检查）。
   - 调用 `get_setup()`（再次确认设备设置信息）。

5. **启动前校验**
   - 调用 `batch_check_task([task_id])`（对应 `/api/BatchCheckTask`）。
   - 只有当接口成功且 `data.code == 200` 才允许启动。

6. **启动任务**
   - 调用 `batch_start_task([task_id])`（对应 `/api/BatchStartTask`）。
   - 启动失败立即退出并报告原因。

7. **执行中监控**
   - 循环调用 `get_task_info(task_id)` 轮询任务状态。
   - 轮询间隔建议 5 秒，最大等待 2 小时。
   - 识别 `TaskStatus.COMPLETED` 视为完成；超时或异常则失败退出。

8. **收尾动作**
   - 调用 `stop_task(task_id)`（对应 `/api/StopTask`）结束当前任务。
   - 返回“配料流程结束”及关键执行摘要。

## 可调用方法白名单（仅 devices 能力）
- 连接与状态：`connect()`、`disconnect()`、`get_status()`、`get_message()`
- 任务相关：`add_task()`、`get_task_info()`、`batch_check_task()`、`batch_start_task()`、`start_task()`、`stop_task()`、`cancel_task()`、`del_task()`
- 资源与配置：`get_setup()`、`get_resource_info()`、`get_chemicals()`、`add_chemical()`

> 说明：若部署环境只提供 `devices/`，优先使用上述方法；不要假设存在外部 flow manager 帮你封装步骤。

## 参数与数据约束
- `task_id` 必须为创建任务后返回值，不可手工猜测。
- `batch_check_task` 与 `batch_start_task` 入参使用同一任务列表，通常为单元素 `[task_id]`。
- 任何接口返回 `{"status": "error", ...}` 都应被视为失败，不可继续后续流程。
- 对用户输入的配方参数执行基础校验：必填字段齐全、数值范围合理、类型可被 `add_task()` 序列化并下发。

## 错误处理策略
- **连接失败**：提示检查设备 IP、账号密码、网络连通性。
- **AddTask 失败**：反馈设备返回 `msg`，并提示检查任务结构与化学品配置。
- **BatchCheckTask 失败**：优先展示 `prompt_msg`，这是最关键的可执行错误信息。
- **BatchStartTask 失败**：建议先 `get_task_info` 查看当前任务状态，再决定重试或取消。
- **轮询超时**：输出已等待时长、最近一次任务状态，并建议人工介入检查设备端。

## 输出模板（建议）
每次执行后输出以下结构化结果：
- `执行结论`：成功 / 失败
- `task_id`：数字或 `None`
- `当前阶段`：如“启动前校验”“任务执行中”
- `关键接口结果`：`GetSetUp / AddTask / BatchCheckTask / BatchStartTask / GetTaskInfo`
- `失败原因`：仅失败时必填
- `下一步建议`：重试、修正参数、人工检查设备

## 与用户交互建议
- 在启动前明确告知“即将开始任务检查与启动”，避免误启动风险。
- 在长轮询期间定期汇报状态（例如每 30~60 秒一次摘要）。
- 用户请求停止时，优先设置停止标记并尽快执行收尾逻辑。

## 禁止事项
- 不要跳过 `batch_check_task` 直接启动任务。
- 不要在未连接状态调用业务接口。
- 不要在 `AddTask` 失败后继续执行资源查询或启动步骤。
- 不要在任务未结束时重复创建同名任务而不提示冲突风险。