# RMBench 接入改动记录

目标：在现有 `--robot robotwin` 上评测 RMBench，不新建 `--robot`，不替换
`rlinf-robotwin-runtime` 的 `_base_task.py`。

上游：https://github.com/RoboTwin-Platform/RMBench  
资产：Hugging Face dataset `TianxingChen/RMBench`（与 C2R 的 `TianxingChen/RoboTwin2.0` 不是同一包）。

---

## 新增文件

| 路径 | 作用 |
|------|------|
| `robots/rmbench/__init__.py` | 对外导出 overlay / 任务表 |
| `robots/rmbench/constants.py` | 10 个任务名 + 官方 `step_lim` |
| `robots/rmbench/overlay.py` | 把任务模块挂到 `robotwin.envs.*`；指令 JSON overlay；资产目录校验（不钉 RoboTwin2.0 revision） |
| `robots/rmbench/env_overlay/<task>.py` | 从 RMBench `envs/` 原样拷贝的任务类（相对 import 指向已安装的 `robotwin.envs`） |
| `robots/rmbench/task_instruction/<task>.json` | 从 RMBench `description/task_instruction/` 拷贝 |
| `robots/rmbench/SOURCE.txt` | 说明拷贝来源，禁止用 RMBench 的 `_base_task.py` 覆盖 site-packages |
| `robots/robotwin/eval/rmbench.json` | 任务 / 步数 / 冒烟 seed 清单 |
| `tests/unit_tests/robots/rmbench/test_rmbench_overlay.py` | 默认值、指令 overlay、资产校验单测 |

未接入（RMBench 有 instruction 但没有 `envs/*.py`）：`classify_blocks`、`place_object_box`、`storage_blocks`。

---

## 修改文件

### `robots/robotwin/robot_spec.py`

- 增加 `ROBOTWIN_BENCHMARKS = ("robotwin", "rmbench")` 和 `_DEFAULT_MAX_EPISODE_STEPS`。
- 新函数 `apply_benchmark_defaults(args)`：
  - 校验 `task_name` 属于 RMBench；
  - `--task-config` 为默认 `demo_randomized` 时改成 `demo_clean`；
  - `--max-episode-steps` 仍为 10000 时改成官方 per-task limit。用户显式传入其它正数则保留。
- CLI 增加 `--benchmark {robotwin,rmbench}`，默认 `robotwin`。
- `--robotwin-assets-path` 默认改为 `None`，解析顺序：CLI → `RMBENCH_ASSETS_PATH`（仅 rmbench）→ `ROBOTWIN_ASSETS_PATH`。
- `_parse_config`：调用 defaults；日志目录 / recipe_tag 使用 `rmbench_` 前缀；`prompt_vars` / `task_desc` 增加 `benchmark`。
- `_resolve_env_runtime_path`：rmbench 走 `validate_rmbench_assets`，不再要求 `.robotwin-assets.json` 的 C2R revision。
- `_spawn_env_server`：向 `env_server.py` 追加 `--benchmark`。
- `_init_runtime` 开头再调一次 `apply_benchmark_defaults`（dashboard 路径兜底）。

### `robots/robotwin/env_server.py`

- `make_env(..., benchmark="robotwin")`：`rmbench` 时先 `install_rmbench_runtime()`，再用 RMBench 资产校验。
- CLI 增加 `--benchmark`。

### `robots/robotwin/prompt_bundle.py`

- `benchmark == "rmbench"` 时插入系统段 `RMBENCH MEMORY TASKS`。

### `robots/robotwin/prompts/system.py`

- `ROLE` 去掉写死的 `demo_randomized`。
- 新增 `RMBENCH`：说明遮挡/记忆、LingBot 未在这些任务上训练、成功只看 `eval_success`。

### `robots/robotwin/prompts/user.py`

- CELL 增加 `benchmark: {{benchmark}}`。

### `AUTODL.md`

- 新增 §2.3：RMBench 资产下载步骤、冒烟命令、路径表。

### `~/.bashrc`（`# >>> rpent >>>` 段）

- 增加注释掉的 `RMBENCH_ASSETS_PATH`。资产下完后取消注释，再 `source ~/.bashrc`。

---

## 运行时行为

`robotwin.envs.vector_env.class_decorator` 仍然 `import robotwin.envs.<task>`。
overlay 在 import 前把 `robots/rmbench/env_overlay/<task>.py` 注册进 `sys.modules["robotwin.envs.<task>"]`，并设置 `__package__ = "robotwin.envs"`，因此 `from ._base_task import Base_Task` 用的是 **已安装 runtime** 的基类。

`load_task_instructions` 被替换：先读 `robots/rmbench/task_instruction/<task>.json`，没有再回落到包装内的 C2R 指令。

### 2026-09-09：env server 900s `Connection refused`

现象：`robotwin_env_server.log` 打出 `robotwin_assets {...}` 后不再听端口。父进程等 900s 后报 healthz Connection refused。

原因：
1. 官方 `observe_and_pickup` 用 **cwd 相对路径** `assets/objects/<model>/model_data*.json` 找变体。从 `rmbench_assets/assets` 或仓库根启动都会找不到。
2. site-packages 里 `SubEnv.setup_task` 吞掉所有 `setup_demo` 异常并无限 `seed += 1`，看起来像卡死。

修复：
- `robots/rmbench/overlay.py`：新增 `resolve_object_model_dir()`（走 `ASSETS_PATH` / `ROBOTWIN_ASSETS_ROOT`）；新增 `install_setup_task_failfast()`，最多试 8 个 seed，失败把真实异常抛出。
- `robots/rmbench/env_overlay/observe_and_pickup.py`：`get_available_model_ids` 改用上面的绝对路径。
- `robots/robotwin/env_server.py`：构造 `RoboTwinAgentEnv` 前多打一行 flush 日志，避免再静默卡住。

### 2026-09-09：`get_info` 缺失导致 env server exit 1

现象：`setup_demo` 已成功，随后 `AttributeError: 'observe_and_pickup' object has no attribute 'get_info'`，8 个 seed 全失败。

原因：C2R 每个任务自己实现 `get_info()` 给指令模板填占位符。RMBench 任务只在 `play_once()` 里写 `self.info["info"] = {}`，指令 JSON 也没有 `{A}` 这类占位符。

修复：
- `episode_info_from_task()`：有 `get_info` 就用，否则读 `info["info"]`，再否则 `{}`。
- `install_get_info_fallback()`：给包装里的 `Base_Task` 补默认 `get_info()`。
- `install_step_limit_overlay()`：把官方 RMBench `step_lim` 合并进 `_eval_step_limit`（否则 eval_mode 会打印 `not in step limit file, set to 1000`）。

---

## 刻意没改

- 没有新的 `--robot`。
- 没有改 site-packages 里的 `rlinf-robotwin-runtime`。
- 没有把 RMBench 资产和现有 `robotwin_assets` 混在同一目录（物体 ID 冲突，例如 C2R 的 `008_tray` vs RMBench 的 `008_shelf`）。
- LingBot checkpoint 仍用现有 EEF 权重（这些记忆任务上会偏弱，靠 planner）。
