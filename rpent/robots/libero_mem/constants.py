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

"""LIBERO-Mem task names and shared init-file aliases."""

from __future__ import annotations

from pathlib import Path

LIBERO_MEM_SUITE = "libero_mem"
LIBERO_MEM_TASK_COUNT = 10

# Official eval order T1–T10 (task ids 0–9).
LIBERO_MEM_TASK_NAMES = (
    "KITCHEN_SCENE1_1_pick_up_the_bowl_and_place_it_back_on_the_plate",
    "KITCHEN_SCENE1_2_lift_the_bottle_and_put_it_down_on_the_plate",
    "KITCHEN_SCENE1_3_lift_the_bowl_and_place_it_back_on_the_plate_3_times",
    "KITCHEN_SCENE1_4_pick_up_the_bottle_and_put_it_down_the_plate_3_times",
    "KITCHEN_SCENE1_5_lift_the_bowl_and_place_it_back_on_the_plate_5_times",
    "KITCHEN_SCENE1_6_pick_up_the_bowl_and_place_it_on_the_plate_7_times",
    "KITCHEN_SCENE1_7_swap_the_2_bowls_on_their_plates_using_the_empty_plate",
    "KITCHEN_SCENE1_8_rotate_the_3_bowls_on_their_plates_from_left_to_right_using_the_empty_plate",
    "KITCHEN_SCENE1_9_put_the_cream_cheese_in_the_nearest_basket_and_place_that_basket_in_the_center",
    "KITCHEN_SCENE1_10_put_the_cream_cheese_in_the_nearest_basket_and_place_the_empty_basket_in_the_center",
)

# The clone only ships 4 pruned_init files. T2–T6 reuse T1's kitchen
# layout; T10 reuses T9's cream-cheese / basket layout.
_T1 = LIBERO_MEM_TASK_NAMES[0]
_T7 = LIBERO_MEM_TASK_NAMES[6]
_T8 = LIBERO_MEM_TASK_NAMES[7]
_T9 = LIBERO_MEM_TASK_NAMES[8]

LIBERO_MEM_INIT_ALIASES: dict[str, str] = {
    LIBERO_MEM_TASK_NAMES[0]: _T1,
    LIBERO_MEM_TASK_NAMES[1]: _T1,
    LIBERO_MEM_TASK_NAMES[2]: _T1,
    LIBERO_MEM_TASK_NAMES[3]: _T1,
    LIBERO_MEM_TASK_NAMES[4]: _T1,
    LIBERO_MEM_TASK_NAMES[5]: _T1,
    LIBERO_MEM_TASK_NAMES[6]: _T7,
    LIBERO_MEM_TASK_NAMES[7]: _T8,
    LIBERO_MEM_TASK_NAMES[8]: _T9,
    LIBERO_MEM_TASK_NAMES[9]: _T9,
}

LIBERO_MEM_BDDL_RELATIVE = Path("libero") / "libero" / "bddl_files" / "libero_mem"
LIBERO_MEM_INIT_RELATIVE = Path("scripts") / "__init_data"

DEFAULT_LIBERO_MEM_ROOT = Path("/root/autodl-tmp/LIBERO-Mem")
