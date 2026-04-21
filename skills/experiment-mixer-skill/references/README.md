## references 目录说明（配料设备）

此目录用于在 **脱离主项目** 部署 skill 时，仍能提供“请求/响应长什么样”的可靠参照，避免模型臆造字段。

### 文件列表

- `**add_task-input.min.json`**：`/api/AddTask` 的最小可用请求样例（可作为模板填参）。
- `**add_task-output.example.json**`：`/api/AddTask` 成功响应样例（用于提取 `task_id`）。
- `**get_resource_info-input.min.json**`：`/api/GetResourceInfo` 的最小请求样例。
- `**get_resource_info-output.example.json**`：`/api/GetResourceInfo` 成功响应样例。
- `**get_setup-output.example.json**`：`/api/GetSetUp` 响应样例（用于确认设备配置、精度、超时等）。
- `**get_task_info-input.min.json**`：`/api/GetTaskInfo` 的请求样例（需要指定`task_id`）。
- `**get_task_info-output.min.json**`：`/api/GetTaskInfo` 的“关键字段子集”样例（用于轮询判定任务完成/异常）。
- `**batch_check_task-output.json**`：`/api/BatchCheckTask` 的响应样例（用于判断创建的任务是否符合规范）。

### 关键判据（来自 devices 实现）

- **连接**：先 `connect()` 拿到 token，后续请求才会带 `Authorization`。
- **创建任务成功**：
  - 设备侧业务字段：`code == 200` 且 `msg == "success"`
  - 并从响应中读取 `task_id`
- **启动前校验**：`batch_check_task([task_id])` 返回成功且 `data.code == 200` 才能继续启动。
- **启动前校验**：`batch_start_task([task_id])` 返回成功且 `data.code == 200` 才算任务启动成功。
- **完成判定**：轮询 `get_task_info(task_id)`，以设备返回的 `status` 字段为准（在主项目 flow 中映射为 `TaskStatus.COMPLETED`）。

