# Copyright 2026 The RPent Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""RMBench task names and official eval step limits."""

from __future__ import annotations

from pathlib import Path

RMBENCH_ROOT = Path(__file__).resolve().parent
RMBENCH_ENV_OVERLAY = RMBENCH_ROOT / "env_overlay"
RMBENCH_INSTRUCTION_DIR = RMBENCH_ROOT / "task_instruction"

# Tasks that ship an env class in RMBench. Instruction-only names
# (classify_blocks, place_object_box, storage_blocks) are omitted.
RMBENCH_TASK_NAMES = (
    "observe_and_pickup",
    "put_back_block",
    "swap_T",
    "rearrange_blocks",
    "swap_blocks",
    "battery_try",
    "press_button",
    "cover_blocks",
    "place_block_mat",
    "blocks_ranking_try",
)

# From RMBench task_config/_eval_step_limit.yml (null entries omitted).
RMBENCH_STEP_LIMITS: dict[str, int] = {
    "observe_and_pickup": 250,
    "put_back_block": 500,
    "swap_T": 600,
    "rearrange_blocks": 700,
    "swap_blocks": 1000,
    "battery_try": 1000,
    "press_button": 1500,
    "cover_blocks": 1500,
    "place_block_mat": 1500,
    "blocks_ranking_try": 3500,
}

RMBENCH_DEFAULT_TASK_CONFIG = "demo_clean"
RMBENCH_ASSET_REPO = "TianxingChen/RMBench"
RMBENCH_REQUIRED_ASSET_DIRECTORIES = (
    "assets/embodiments/aloha-agilex",
    "assets/objects",
)
