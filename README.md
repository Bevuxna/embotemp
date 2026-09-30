# embotemp

这台 AutoDL 机器上需要留下的代码快照。拍下来的时间是 2026-09-30。

真正有本地改动的只有 [RLinf/RPent](https://github.com/RLinf/RPent) 的一份工作树，基线提交是 `014a0fa`（`main`，与当时的 `origin/main` 一致）。目录在 `rpent/`。

## 没有放进来的东西

下面这些和开源仓库完全一致，工作区干净、没有超前提交，所以没有再复制一份：

| 本地目录 | 上游 |
|---|---|
| `LIBERO-Mem` | https://github.com/libero-mem/libero-mem `0eee0de` |
| `RMBench` | https://github.com/RoboTwin-Platform/RMBench `e43d39f` |
| `embodied_agent/GPT-as-Policy` | https://github.com/anonymous-report-421/GPT-as-Policy `8f3d362` |

按体积排除、需要在新机器上重新下载的内容：

| 路径 | 大约体积 | 是什么 |
|---|---|---|
| `rpent/checkpoints/RLinf-Pi05-LIBERO-130-fullshot-SFT` | 7.0G | Hugging Face `RLinf/RLinf-Pi05-LIBERO-130-fullshot-SFT` |
| `rpent/checkpoints/LingBot-VLA-RoboTwin-EEF-ckpt1500` | 23G | LingBot-VLA RoboTwin 权重 |
| `rpent/checkpoints/sam3` | 6.5G | SAM3 权重 |
| `rpent/robotwin_assets` | 16G | RoboTwin 仿真资源 |
| `rpent/rmbench_assets` | 1.3G | RMBench 仿真资源（含单个 205MB 的 mesh，超过 GitHub 单文件限制） |
| `rpent/logs` | 1.4G | 评测日志 |
| `rpent/memory` | 约 2.3M | 本地 memory，上游 `.gitignore` 本来就不跟踪 |

环境（`/root/autodl-tmp/envs`，约 35G）和代理配置、shell 里的密钥都没有放进来。复现步骤写在 `rpent/AUTODL.md`。

## 相对上游 RPent 多出来的代码

已改文件（17 个，大约 +378 / −29）：LIBERO `move_to` 夹爪 hold、RoboTwin / memory / robot spec 相关改动。说明见 `rpent/robots/libero/CHANGES_MOVE_TO_HOLD.md`。

未跟踪的新代码：

- `rpent/robots/libero_mem/`：LIBERO-Mem 评测 overlay，不内嵌上游 `libero` 包
- `rpent/robots/rmbench/`：从 RMBench 拷来的任务模块，运行时挂到已安装的 robotwin 环境上
- `rpent/robots/robotwin/eval/rmbench.json`
- 对应的单测在 `rpent/tests/unit_tests/robots/libero_mem/`、`rmbench/`，以及 `libero/test_libero_move_to_gripper.py`
- `rpent/AUTODL.md`：这台机器上的环境笔记
