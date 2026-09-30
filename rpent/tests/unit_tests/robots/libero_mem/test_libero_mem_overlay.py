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

from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from robots.libero_mem.constants import (
    LIBERO_MEM_INIT_ALIASES,
    LIBERO_MEM_TASK_COUNT,
    LIBERO_MEM_TASK_NAMES,
)
from robots.libero.prompt_bundle import system_prompt, user_prompt
from robots.libero.robot_spec import LIBERO_SUITE_NAMES
from robots.libero_mem.overlay import (
    init_file_for_task,
    language_from_bddl,
    validate_libero_mem_assets,
)
from rpent.robots import get_robot_spec
from robots.libero_mem.sequential import check_success, reset_subgoal_progress


class _Host:
    def __init__(self, goal_state, holding: bool = True):
        self.parsed_problem = {"goal_state": goal_state}
        self.holding = holding

    def _eval_predicate(self, state):
        return bool(self.holding)


T1_GOAL = [["sequence", ["and", ["on", "akita_black_bowl_1", "plate_1"]]]]
AND_GOAL = [["on", "akita_black_bowl_1", "plate_1"]]


def test_task_table_is_ten_official_names() -> None:
    assert len(LIBERO_MEM_TASK_NAMES) == LIBERO_MEM_TASK_COUNT
    assert set(LIBERO_MEM_INIT_ALIASES) == set(LIBERO_MEM_TASK_NAMES)
    assert len(set(LIBERO_MEM_INIT_ALIASES.values())) == 4


def test_t1_init_satisfied_is_not_success() -> None:
    host = _Host(T1_GOAL, holding=True)
    assert check_success(host, inc=True) is False
    for _ in range(10):
        assert check_success(host, inc=True) is False
    assert host._satisfied_subgoals == []


def test_t1_leave_and_return_counts() -> None:
    host = _Host(T1_GOAL, holding=True)
    for _ in range(6):
        check_success(host, inc=True)
    host.holding = False
    for _ in range(16):
        assert check_success(host, inc=True) is False
    host.holding = True
    assert check_success(host, inc=True) is True


def test_and_goal_still_succeeds_immediately() -> None:
    host = _Host(AND_GOAL, holding=True)
    # Sequential wrapper is not used for flat AND; callers keep the stock
    # kitchen checker. The helper still ANDs leaves when asked.
    assert check_success(host, inc=True) is True


def test_reset_clears_overshoot() -> None:
    host = _Host(T1_GOAL, holding=True)
    for _ in range(6):
        check_success(host, inc=True)
    host.holding = False
    for _ in range(16):
        check_success(host, inc=True)
    host.holding = True
    assert check_success(host, inc=True) is True
    host.holding = False
    for _ in range(7):
        check_success(host, inc=True)
    assert host._overshot is True
    reset_subgoal_progress(host)
    assert host._overshot is False
    assert host._satisfied_subgoals == []


def test_validate_libero_mem_assets_requires_layout(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="incomplete"):
        validate_libero_mem_assets(tmp_path)


def test_suite_is_registered_on_libero_robot() -> None:
    assert "libero_mem" in LIBERO_SUITE_NAMES


def test_parse_config_rejects_out_of_range_mem_task(tmp_path: Path) -> None:
    args = argparse.Namespace(
        suite="libero_mem",
        task=10,
        seed=0,
        explore=False,
        memory_profile=None,
        memory_dir=None,
        explore_sessions=3,
        output_dir=tmp_path / "out",
    )
    with pytest.raises(ValueError, match="0..9"):
        get_robot_spec("libero").parse_config(args)


def test_mem_prompts_drop_libero10_levers() -> None:
    system = system_prompt({"suite": "libero_mem", "mode": "eval", "memory_profile": "hf"})
    assert "LIBERO-MEM SEQUENTIAL GOALS" in system
    assert "PROVEN LEVERS" not in " ".join(system)
    user = user_prompt({"suite": "libero_mem"})
    assert "sequential" in user["CELL"].lower()


def test_validate_real_clone_if_present() -> None:
    try:
        identity = validate_libero_mem_assets()
    except ValueError:
        pytest.skip("LIBERO-Mem sparse clone is not on this machine")
    assert identity["n_tasks"] == 10
    t2 = LIBERO_MEM_TASK_NAMES[1]
    assert init_file_for_task(t2).name.startswith("KITCHEN_SCENE1_1_")
    t1_bddl = Path(identity["bddl_dir"]) / f"{LIBERO_MEM_TASK_NAMES[0]}.bddl"
    assert "pick up the bowl" in language_from_bddl(t1_bddl)
