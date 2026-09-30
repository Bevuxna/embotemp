# AutoDL 上跑 RPent：LIBERO-PRO 与 RoboTwin

本机笔记，不是上游文档。仓库在 `/root/autodl-tmp/rpent`（RLinf/RPent）。官方教程：

- LIBERO：https://rpent.readthedocs.io/zh-cn/latest/rst_source/usage/libero.html
- RoboTwin：https://rpent.readthedocs.io/zh-cn/latest/rst_source/usage/robotwin.html
- Planner：https://rpent.readthedocs.io/zh-cn/latest/rst_source/usage/configure_planner.html

两套 **不能混装**。Python、仿真器和 VLA 都不同，共用同一份源码树，但各用各的 venv。

| | LIBERO-PRO | RoboTwin |
|---|---|---|
| `--robot` | `libero` | `robotwin` |
| venv | `/root/autodl-tmp/envs/rpent` | `/root/autodl-tmp/envs/robotwin` |
| Python | 3.12 | **3.11** |
| 仿真 | MuJoCo 3.3.0 + robosuite + LIBERO-PRO | SAPIEN **3.0.0b1** |
| VLA | Pi0.5 | LingBot-VLA |
| extra | `.[libero-pro]` | `.[robotwin]` |
| GPU | 同一张 4090，不要并行跑两套 | 同左 |

系统盘 `/` 只有约 30G，包、缓存、权重、资源全部放 `/root/autodl-tmp`。

---

## 0. 公共部分（`~/.bashrc` 的 `# >>> rpent >>>` 段）

新开终端后 `source ~/.bashrc`。当前 **不会** 自动 `activate` 任一 venv，需要自己切。

共用变量已经写在 bashrc：

- `CUDA_HOME=/usr/local/cuda-12.8`，`uv` 在 `~/.local/bin`
- 缓存：`UV_CACHE_DIR` / `HF_HOME` / `MODELSCOPE_CACHE` / `TORCH_HOME` → `/root/autodl-tmp/.cache/...`
- `HF_HUB_DISABLE_XET=1`；默认 `HF_ENDPOINT=https://hf-mirror.com`（memory 语料等小文件）。下 Pi0.5 等大权重时先 `unset HF_ENDPOINT` 再 `proxy_on`
- `unset UV_PYTHON`（设成 conda 解释器会把包装进系统盘的 `base`）
- Codex：`CODEX_API_KEY`、`CODEX_BASE_URL`（`--planner codex` **只读这两个**，不读 `OPENAI_*`）
- `proxy_on` / `proxy_off`；`no_proxy` 含国内镜像和 Codex 网关 `43.159.47.118`（流式 `/v1/responses` 走 clash 容易 502）

切环境：

```bash
# LIBERO
source /root/autodl-tmp/envs/rpent/bin/activate

# RoboTwin
source /root/autodl-tmp/envs/robotwin/bin/activate
```

`deactivate` 后再切另一套。Planner 示例（两边通用）：

```bash
--planner codex --model gpt-5.6-luna
```

`--planner codex` 的 `--model` 用网关裸 id（`gpt-5.6-luna`、`gpt-5.5`、`gpt-5.3-codex-spark` 等），不要加 `openai:` 前缀。

---

## 1. LIBERO-PRO

### 1.1 环境（已装好，复装才需要）

```bash
unset UV_PYTHON
export UV_CACHE_DIR=/root/autodl-tmp/.cache/uv
uv venv /root/autodl-tmp/envs/rpent --python /root/miniconda3/bin/python3.12
source /root/autodl-tmp/envs/rpent/bin/activate

cd /root/autodl-tmp/rpent
uv pip install -e ".[libero-pro]" \
  --python /root/autodl-tmp/envs/rpent/bin/python \
  --torch-backend=cu128 \
  --default-index https://mirrors.aliyun.com/pypi/simple

# 仿真资源（scenes/ 在但未下完时不要用 --skip-existing）
liberopro-download-assets   # 小文件已默认走 hf-mirror；大文件请 unset HF_ENDPOINT && proxy_on

# Pi0.5（约 7.5G，不要镜像）
unset HF_ENDPOINT
export HF_HUB_DISABLE_XET=1
hf download RLinf/RLinf-Pi05-LIBERO-130-fullshot-SFT \
  --local-dir /root/autodl-tmp/rpent/checkpoints/RLinf-Pi05-LIBERO-130-fullshot-SFT
# 不必下 optimizer.pt

# SAM3（可用 ModelScope）
modelscope download --model facebook/sam3 sam3.pt \
  --local_dir /root/autodl-tmp/rpent/checkpoints/sam3
```

bashrc 里已有：

```bash
export MUJOCO_GL=egl
export LIBERO_TYPE=pro
export PI05_CHECKPOINT_PATH=/root/autodl-tmp/rpent/checkpoints/RLinf-Pi05-LIBERO-130-fullshot-SFT
export SAM3_CHECKPOINT_PATH=/root/autodl-tmp/rpent/checkpoints/sam3/sam3.pt
```

系统包：`libegl1`、`ninja-build`。`mujoco` 必须锁 **3.3.0**（3.4+ 会改 LIBERO 结算）。

**本地补丁（重装 `rpent-liberopro` 会丢）：**  
`.../site-packages/liberopro/liberopro/envs/robots/on_the_ground_panda.py` 的 `default_base` 必须是 `"NullBase"`，否则 robosuite 1.5.2 在 `env.reset` 报 `'str' object is not callable`。

自检：

```bash
python -c "import torch, mujoco; print(torch.__version__, torch.cuda.is_available(), mujoco.__version__)"
# 期望: 2.7.x+cu128  True  3.3.0
```

### 1.2 用法

必须带 `--robot libero`。

```bash
source /root/autodl-tmp/envs/rpent/bin/activate
cd /root/autodl-tmp/rpent

# 短任务冒烟（object swap t2）
rpent --robot libero --suite libero_object_swap --task 2 --seed 0 \
  --cuda-device 0 --planner codex --model gpt-5.6-luna

# 长程 = LIBERO-Long = libero_10（PRO 扰动版更有区分度）
rpent --robot libero --suite libero_10_swap --task 0 --seed 0 \
  --cuda-device 0 --planner codex --model gpt-5.6-luna
```

CLI 套件：`libero_{object,goal,spatial,10}` 以及 `_task` / `_swap` / `_lan`。`libero_90` 是 90 个短任务，不是更长程。`--task` 一般 `0–9`，`--libero-type` 可省略（bashrc 已是 `pro`）。

`move_to` 夹爪默认是上游原逻辑（漏传 = 张开 `-1`）。本地 hold latch 要用 `--libero-move-to-hold`（记录：`robots/libero/CHANGES_MOVE_TO_HOLD.md`）。测碗类任务请先关掉 hold，避免和 Pi0 抓取混在一起。

`libero_10_swap` 指令（seed 0 memory）：

| task | 指令 | 备注 |
|------|------|------|
| 0 | 两罐（alphabet soup + tomato sauce）入篮 | 已跑通 |
| 1 | 奶油芝士盒 + 黄油盒入篮 | 两盒可叠，相对容易 |
| 2 | 开炉 + moka pot 上炉 |
| 3 | 黑碗进底层抽屉并关上 |
| 4 | 白杯→左盘，黄白杯→右盘 | 杯子一倒几乎不可恢复 |
| 5 | 书放到 caddy 后格 | “后”是容器坐标系 |
| 6 | 白杯放盘 + 布丁放盘右侧 |
| 7 | alphabet soup + 奶油芝士盒入篮 |
| 8 | 两只 moka pot 上炉 |
| 9 | （swap 无 seed-0 memory）微波炉+关门 | 最难；对应 `libero_10_task` t9 |

成功看 transcript 里 `finish.status == success` 且环境 `terminated: true`，并写出 `*_recipe.jsonl`。日志：`logs/<时间戳>_<suite>_t<task>_s<seed>/`。502 中途断流则 recipe 不会写。

### 1.3 LIBERO-Mem（记忆评测，10 个厨房任务）

评测环境：https://github.com/libero-mem/libero-mem（只要 BDDL + `pruned_init` + 时序判定，不要 `pip install`，不要 211GB 示教）。稀疏 clone 在 `/root/autodl-tmp/LIBERO-Mem`（约 1.8M）。场景网格仍用现有 LIBERO-PRO 资产。

可选：`export LIBERO_MEM_PATH=/root/autodl-tmp/LIBERO-Mem`

```bash
source /root/autodl-tmp/envs/rpent/bin/activate
cd /root/autodl-tmp/rpent

rpent --robot libero --suite libero_mem --task 0 --seed 0 \
  --cuda-device 0 --planner codex --model gpt-5.6-luna
```

`--task` 为 `0–9`（T1–T10）。成功仍看 `finish.status == success` 且 `terminated: true`。**第 0 帧就 `terminated` 说明时序判定没挂上**（碗一开始就在盘子上，官方 Sequential 不算成功）。

| task | 指令要点 | 记忆类型 |
|------|----------|----------|
| 0 | 拿起碗再放回盘 | 离开再回来 |
| 1 | 拿起瓶子再放回盘 | 同上 |
| 2 / 3 / 4 / 5 | 碗或瓶放回 3 / 3 / 5 / 7 次 | 重复计数 |
| 6 | 两碗用空盘对换 | 序列 / 或 |
| 7 | 三碗从左往右轮转 | 序列 |
| 8 | 奶油芝士进最近篮子，再把**那个**篮子放到中间 | 最近 + 同一篮子 |
| 9 | 奶油芝士进最近篮子，再把**空**篮子放到中间 | 最近 + 另一只 |

日志：`logs/<时间戳>_libero_mem_t<task>_s<seed>/`。改动记录：`robots/libero_mem/CHANGES.md`。

---

## 2. RoboTwin

### 2.1 环境

需要 **Python 3.11**、编译链、CUDA 12.8、`libvulkan1`。装 3.11 和 GitHub 依赖时开 `proxy_on`。

```bash
source ~/.bashrc
proxy_on
unset UV_PYTHON
export UV_CACHE_DIR=/root/autodl-tmp/.cache/uv
export UV_PYTHON_INSTALL_DIR=/root/autodl-tmp/.cache/uv/python

cd /root/autodl-tmp/rpent
uv python install 3.11
uv venv /root/autodl-tmp/envs/robotwin --python 3.11
source /root/autodl-tmp/envs/robotwin/bin/activate

uv pip install -e ".[robotwin]" \
  --python /root/autodl-tmp/envs/robotwin/bin/python \
  --torch-backend=cu128 \
  --default-index https://mirrors.aliyun.com/pypi/simple \
  --index https://pypi.tuna.tsinghua.edu.cn/simple
```

`.[robotwin]` 会从 GitHub 固定提交装 RoboTwin runtime 和 LingBot；镜像只加速 PyPI。SAPIEN 必须是 **3.0.0b1**。

```bash
# 资源（小文件可用镜像）
mkdir -p /root/autodl-tmp/rpent/robotwin_assets
HF_ENDPOINT=https://hf-mirror.com robotwin-download-assets \
  --output /root/autodl-tmp/rpent/robotwin_assets

# LingBot（大权重：官方 HF + 代理，不要镜像）
unset HF_ENDPOINT
export HF_HUB_DISABLE_XET=1
hf download RLinf/LingBot-VLA-RoboTwin-EEF-ckpt1500 \
  --revision e727b46cd220b66981ea4d2fd9ba84adc189e2cc \
  --local-dir /root/autodl-tmp/rpent/checkpoints/LingBot-VLA-RoboTwin-EEF-ckpt1500
```

bashrc 里已有：

```bash
export ROBOTWIN_ASSETS_PATH=/root/autodl-tmp/rpent/robotwin_assets
export LINGBOT_MODEL_PATH=/root/autodl-tmp/rpent/checkpoints/LingBot-VLA-RoboTwin-EEF-ckpt1500
export VK_ICD_FILENAMES=/etc/vulkan/icd.d/nvidia_icd.json
```

`VK_ICD_FILENAMES` 用来消 SAPIEN 的 “Failed to find Vulkan ICD”：驱动 ICD 在 `/etc`，SAPIEN 默认只找 `/usr/share/vulkan/icd.d/nvidia_icd.json`。

自检：

```bash
python -c "import torch, sapien; print(torch.__version__, torch.cuda.is_available(), sapien.__version__)"
# 期望: 2.8.x+cu128  True  3.0.0b1，且不应再刷 ICD 警告
```

### 2.2 用法

```bash
source /root/autodl-tmp/envs/robotwin/bin/activate
cd /root/autodl-tmp/rpent

rpent --robot robotwin \
  --task-name beat_block_hammer \
  --seed 100000 \
  --cuda-device 0 \
  --planner codex \
  --model gpt-5.6-luna
```

- `--task-config` 默认 `demo_randomized`（C2R 扰动）。干净场景用 `demo_clean`。
- `--seed` 是场景精确种子。评测请用 `robots/robotwin/eval/demo_randomized.json` 里 **每个任务各自的 5 个 verified seed**，不要所有任务共用同一组。冒烟：`beat_block_hammer` + `100000`。
- 成功看工具结果里的 **`TASK_ENV.eval_success`**，不要只看 planner 有没有 `finish`。
- 日志：`logs/<时间戳>_robotwin_<task-name>_s<seed>/`

50 个 `demo_randomized` 任务名：

```
adjust_bottle beat_block_hammer blocks_ranking_rgb blocks_ranking_size
click_alarmclock click_bell dump_bin_bigbin grab_roller handover_block
handover_mic hanging_mug lift_pot move_can_pot move_pillbottle_pad
move_playingcard_away move_stapler_pad open_laptop open_microwave
pick_diverse_bottles pick_dual_bottles place_a2b_left place_a2b_right
place_bread_basket place_bread_skillet place_burger_fries place_can_basket
place_cans_plasticbox place_container_plate place_dual_shoes place_empty_cup
place_fan place_mouse_pad place_object_basket place_object_scale
place_object_stand place_phone_stand place_shoe press_stapler
put_bottles_dustbin put_object_cabinet rotate_qrcode scan_object
shake_bottle shake_bottle_horizontally stack_blocks_three stack_blocks_two
stack_bowls_three stack_bowls_two stamp_seal turn_switch
```

论文复现量级（`reproduce/robotwin`、gpt-5.5、xhigh）：250 episode，约 58%。单格示例还要加 `--reasoning-effort xhigh --max-turns 100 --planner-timeout-s 4800`。

---

## 3. 踩坑（这台机器上真实遇到过）

1. **`UV_PYTHON` 指向 conda** → 包装进 `/root/miniconda3`，撑满系统盘。始终 `unset`。
2. **HF 镜像下大模型** → Xet/`X-Repo-Commit` 失败。Pi0.5、LingBot 用官方 + 代理 + `HF_HUB_DISABLE_XET=1`。
3. **Codex 走代理** → 长流式 502。`43.159.47.118` 必须在 `no_proxy`。
4. **LIBERO `OnTheGroundPanda.default_base`** → 必须 `"NullBase"`。
5. **`mujoco>=3.4`** → 不要升。
6. **SAPIEN 非 3.0.0b1** → 观测会变，LingBot 变差。
7. **同一张 GPU 并行两套** → 不要。
8. **RoboTwin 成功判据** 是 `eval_success`，不是 `finish`。
9. 重装 `rpent-liberopro` 后复查 Panda 补丁。

---

## 4. 路径速查

| 用途 | 路径 |
|------|------|
| 源码 | `/root/autodl-tmp/rpent` |
| LIBERO venv | `/root/autodl-tmp/envs/rpent` |
| RoboTwin venv | `/root/autodl-tmp/envs/robotwin` |
| Pi0.5 | `$PI05_CHECKPOINT_PATH` |
| SAM3 | `$SAM3_CHECKPOINT_PATH` |
| LingBot | `$LINGBOT_MODEL_PATH` |
| RoboTwin 资源 | `$ROBOTWIN_ASSETS_PATH` |
| 运行日志 | `/root/autodl-tmp/rpent/logs/` |
| LIBERO memory | `/root/autodl-tmp/rpent/memory/libero/` |
| LIBERO-Mem 稀疏 clone | `/root/autodl-tmp/LIBERO-Mem`（或 `$LIBERO_MEM_PATH`） |
| RoboTwin seed 表 | `robots/robotwin/eval/demo_randomized.json` |
