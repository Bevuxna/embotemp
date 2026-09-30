# LIBERO-Mem 接入改动记录

目标：在现有 `--robot libero` 上评测 LIBERO-Mem 的 10 个厨房记忆任务，不新建
`--robot`，不 `pip install` LIBERO-Mem，不覆盖 `liberopro`。

上游评测环境：https://github.com/libero-mem/libero-mem  
论文：https://arxiv.org/abs/2511.11478

---

## 新增文件

| 路径 | 作用 |
|------|------|
| `robots/libero_mem/__init__.py` | 对外导出 overlay / 任务表 |
| `robots/libero_mem/constants.py` | T1–T10 任务名 + 4 份 `pruned_init` 的共享别名 |
| `robots/libero_mem/sequential.py` | 官方 Sequential / Or 成功判定（含 dwell / overshoot） |
| `robots/libero_mem/overlay.py` | 动态注册 `libero_mem`；把 BDDL/init 指到稀疏 clone；给 spawn worker 打时序补丁 |
| `robots/libero_mem/SOURCE.txt` | 来源说明，禁止把他们的 `libero` 包装进 rpent venv |
| `tests/unit_tests/robots/libero_mem/test_libero_mem_overlay.py` | 资产校验、init 别名、T1 第 0 帧不应成功 |

---

## 修改文件

### `rpent/robots/base.py`

- `enumerate_robots()` 只收带 `get_robot_spec` 的包，避免把 `libero_mem` /
  `rmbench` 这类 overlay 当成 `--robot`。

### `robots/libero/robot_spec.py`

- `LIBERO_SUITE_NAMES` 增加 `libero_mem`。
- `--suite libero_mem` 时校验 `--task` 为 `0–9`。
- env_server 环境变量带上 `LIBERO_MEM_PATH`（若已设置）。

### `robots/libero/env_server.py`

- `make_env` 在 `suite == libero_mem` 时先 `install_libero_mem_runtime()`，再
  `get_benchmark`。

### `robots/libero/prompt_bundle.py` / `prompts/system.py` / `prompts/user.py`

- `libero_mem` 不用 libero_10 的 PROVEN LEVERS，改插入记忆任务说明。
- CELL 标明 suite。

### `AUTODL.md`

- 新增 §1.3：稀疏 clone 路径、冒烟命令、T1–T10 表。

---

## 运行时行为

- 套件仍走 `--robot libero --suite libero_mem --task 0..9`。
- BDDL 读 `/root/autodl-tmp/LIBERO-Mem/libero/libero/bddl_files/libero_mem/`。
- init：T1 共享给 T2–T6，T9 共享给 T10；T7 / T8 各用自己的 `pruned_init`。
- 成功判定在 worker 里打补丁（`multiprocessing` spawn 不会继承父进程 monkeypatch）。
- Sequence 目标：初始 `On bowl plate` **不是**成功；需要拿起再放回（hold / leave /
  return）。重复子目标要按序完成；最后一项目标离开太久会 `_overshot`，之后一直失败。
- 场景网格仍用 LIBERO-PRO 资产。Pi0.5 的 `pi0_pick(prompt=)` 仍然会覆盖子指令。

冒烟：若 `terminated` 在第 0 帧为 true，时序判定没有挂上。

2026-09-09：本机 `make_env(libero_mem, t0, seed=0)` reset 后第一步
`terminated=[False]`，指令为 `pick up the bowl and place it back on the plate`。
每个任务 120 条 init（`seed % 120`）。
