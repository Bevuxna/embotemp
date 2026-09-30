# LIBERO `move_to` gripper hold（夹碗相关改动）

对照开关：`--libero-move-to-hold` / 环境变量 `LIBERO_MOVE_TO_HOLD`。
**默认 false = 上游原逻辑**（漏传 gripper 就是张开 `-1`）。

## 改过什么

只动了 **脚本 `move_to` 的默认夹爪命令**，没有改 Pi0 / `pi0_pick` / `set_gripper` / `release`。

| 路径 | 改动 |
|------|------|
| `robots/libero/tools.py` | `LiberoPrimitives.move_to`：flag on 时默认 hold latch（开始时已闭合则全程 `+1`，已张开则全程 `-1`）；flag off 时默认 `-1`。曾试过按指宽 P 伺服，会在 OSC `±1` 满开/满闭上抖，已废弃。 |
| `robots/libero/tools.py` `tools_spec()` | flag on 时工具 schema 写成 default `'hold'` |
| `robots/libero/robot_spec.py` | CLI `--libero-move-to-hold` / `--no-libero-move-to-hold`，并传入 primitives |
| `robots/libero/toolkit.py` | 按 flag 注册对应 schema |
| `robots/libero/prompts/system.py` | GRIPPER SIGN：原「搬运必须 `+1`」；若 live schema 是 hold 则允许省略 |
| `robots/libero/guides/strict_hybrid_guide.md` | 示例仍是 `gripper: -1`；注明 live schema 优先 |

**没改：** `pi0_pick` 成功判定、VLA 动作、碗 rim 的 `eef_y + 0.045` 提示、LIBERO-Mem overlay。

## 为什么会抖

LIBERO OSC 的 `action[6]` 是满开/满闭设定，不是指宽速度。按开口做 P 控制时，接触让开口抖 1–2 mm 就会打满到另一头。hold latch 不再跟开口。

## 用法

```bash
# 原逻辑（默认）——测「是不是 Pi0 / 任务本身」请用这个
rpent --robot libero ... --no-libero-move-to-hold
# 或不写该 flag

# 打开改过的 hold
rpent --robot libero ... --libero-move-to-hold
# 或 export LIBERO_MOVE_TO_HOLD=1
```

`run.log` 里会有 `move_to gripper: original default -1` 或 `hold latch (modified)`。
