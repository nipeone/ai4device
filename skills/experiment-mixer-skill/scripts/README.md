## scripts 目录说明（配料设备）

这些脚本用于在 skill 独立部署环境中，直接复用 `devices/` 代码完成联调与排障。

### 1) 结构校验（不访问设备）

```bash
python validate_add_task_payload.py --input ../references/add_task-input.min.json
```

### 2) 端到端执行（访问设备）

```bash
python run_mixer_task.py --input ../references/add_task-input.min.json
```

可选参数：
- `--poll-interval 5`：轮询间隔秒数
- `--timeout-seconds 7200`：最大等待时长（默认 2 小时）
- `--no-stop`：完成后不调用 `stop_task`（一般不建议）

### 注意
- `run_mixer_task.py` 只调用 `MixerController` 方法，不依赖 `flows/` 与 `schemas/`。
- 设备地址与账号密码由 `devices` 侧读取（例如环境变量/配置文件），请确保独立部署环境的配置一致。
