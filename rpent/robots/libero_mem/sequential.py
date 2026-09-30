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

"""Sequential success checker ported from LIBERO-Mem kitchen tasks.

Vanilla LIBERO ANDs every leaf predicate. Several LIBERO-Mem goals start
already true (bowl on plate), so that checker fires at frame 0. Official
LIBERO-Mem wraps goals in ``Sequence`` / ``Or`` and requires a hold / leave /
return dwell before a repeated subgoal counts. The last subgoal must keep
holding; leaving it for too long is an overshoot fail.

Source: libero-mem/libero-mem
``libero/libero/envs/problems/libero_kitchen_tabletop_manipulation.py``
and ``bddl_base_domain.py``.
"""

from __future__ import annotations

from typing import Any

_SEQUENCE_OPS = {"sequence", "or"}


def ensure_subgoal_state(host: Any) -> None:
    """Attach sequential-checker fields if the host was built without them."""
    if not hasattr(host, "_satisfied_subgoals"):
        host._satisfied_subgoals = []
    if not hasattr(host, "_sub_goal_live_time"):
        host._sub_goal_live_time = 0
    if not hasattr(host, "_sub_goal_nonlive_time"):
        host._sub_goal_nonlive_time = 0
    if not hasattr(host, "_overshot"):
        host._overshot = False


def reset_subgoal_progress(host: Any) -> None:
    """Clear dwell counters. Also clears ``_overshot`` (official reset omits it)."""
    ensure_subgoal_state(host)
    host._satisfied_subgoals = []
    host._sub_goal_live_time = 0
    host._sub_goal_nonlive_time = 0
    host._overshot = False


def is_sequential_goal(goal_state: Any) -> bool:
    """Return True when the parsed BDDL goal uses Sequence or Or."""
    if not goal_state:
        return False
    first = goal_state[0]
    if not isinstance(first, (list, tuple)) or not first:
        return False
    return str(first[0]).lower() in _SEQUENCE_OPS


def is_subgoal_trajectory_possible(current_traj: list, testing_traj: list) -> bool:
    """True when the current prefix is a subset of the candidate Or branch."""
    set_a = {tuple(item) for clause in current_traj for item in clause[1:]}
    set_b = {tuple(item) for clause in testing_traj for item in clause[1:]}
    return set_a.issubset(set_b)


def check_success(host: Any, inc: bool = False) -> bool:
    """Evaluate the parsed goal. ``inc=True`` advances dwell counters."""
    ensure_subgoal_state(host)
    goal_state = host.parsed_problem["goal_state"]
    if not goal_state:
        return False
    is_leaf_level = not is_sequential_goal(goal_state)
    if not is_leaf_level:
        goal_state = goal_state[0]
    return eval_goal(host, goal_state, inc, is_leaf_level=is_leaf_level)


def eval_goal(
    host: Any,
    goal_state: Any,
    inc: bool = False,
    is_leaf_level: bool = False,
) -> bool:
    """Recursively evaluate ``and`` / ``or`` / ``sequence`` / leaf predicates."""
    ensure_subgoal_state(host)
    if is_leaf_level:
        result = True
        for state in goal_state:
            result = host._eval_predicate(state) and result
        return result

    op = str(goal_state[0]).lower()
    if op == "and":
        subgoal = goal_state[1:]
        return bool(eval_goal(host, subgoal, inc, is_leaf_level=True))

    if op == "sequence":
        idx = len(host._satisfied_subgoals)
        if host._overshot:
            return False

        if idx >= len(goal_state) - 1:
            idx = idx - 1

        subgoal = goal_state[idx + 1]
        if len(subgoal[1:]) != 1:
            raise ValueError(
                "LIBERO-Mem Sequence And-clauses must have exactly one predicate, "
                f"got {subgoal!r}"
            )
        success = eval_goal(host, subgoal, inc, is_leaf_level=is_leaf_level)

        if success:
            if len(host._satisfied_subgoals) >= len(goal_state) - 1:
                host._sub_goal_nonlive_time = 0
                return True

            if host._sub_goal_live_time > 5 and host._sub_goal_nonlive_time > 15:
                host._sub_goal_live_time = 0
                host._sub_goal_nonlive_time = 0
                host._satisfied_subgoals.append(subgoal)
                return True
            if inc:
                host._sub_goal_live_time += 1
            return False

        if len(host._satisfied_subgoals) >= len(goal_state) - 1:
            if host._sub_goal_nonlive_time > 5:
                host._overshot = True
                return False
        if inc:
            host._sub_goal_nonlive_time += 1
        return False

    if op == "or":
        for subgoal in goal_state[1:]:
            if str(subgoal[0]).lower() != "sequence":
                continue
            if not is_subgoal_trajectory_possible(
                current_traj=host._satisfied_subgoals,
                testing_traj=subgoal[1:],
            ):
                continue
            if eval_goal(host, subgoal, inc, is_leaf_level=is_leaf_level):
                return True
        return False

    raise ValueError(f"Unknown goal structure: {goal_state}")
