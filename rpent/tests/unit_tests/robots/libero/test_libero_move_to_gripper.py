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

"""LIBERO move_to gripper default: original open vs optional hold latch."""

from __future__ import annotations

from typing import Any

import numpy as np
import pytest

from robots.libero.tools import LiberoPrimitives, tools_spec


class _FakeEnv:
    terminated = False
    truncated = False
    return_all_frames = False

    def __init__(
        self, eef: list[float], opening: float, *, drift: float = 0.0
    ) -> None:
        self.actions: list[np.ndarray] = []
        self._eef = np.asarray(eef, dtype=np.float32)
        self._opening = float(opening)
        self._drift = float(drift)

    def _obs(self) -> dict[str, Any]:
        half = self._opening / 2.0
        states = np.zeros(8, dtype=np.float32)
        states[:3] = self._eef
        states[6] = half
        states[7] = -half
        return {
            "states": states,
            "main_images": np.zeros((4, 4, 3), dtype=np.uint8),
        }

    def step(self, action: np.ndarray) -> tuple[dict[str, Any], float, bool, bool, dict]:
        action = np.asarray(action, dtype=np.float32)
        self.actions.append(action.copy())
        self._eef = self._eef + action[:3] * 0.05
        self._opening = min(0.08, self._opening + self._drift)
        return self._obs(), 0.0, False, False, {}

    def raw_obs(self) -> dict[str, Any]:
        return {"robot0_eef_quat": [1.0, 0.0, 0.0, 0.0]}


def _primitives(
    opening: float = 0.01,
    *,
    drift: float = 0.0,
    move_to_hold: bool = False,
) -> tuple[LiberoPrimitives, _FakeEnv]:
    env = _FakeEnv(eef=[0.0, 0.0, 1.0], opening=opening, drift=drift)
    prim = LiberoPrimitives(
        env=env,
        model=object(),
        sam3_client=object(),
        check_cancelled=lambda: None,
        move_to_hold=move_to_hold,
    )
    prim.set_obs(env._obs())
    return prim, env


def test_move_to_original_default_opens() -> None:
    prim, env = _primitives(opening=0.01, move_to_hold=False)
    prim.move_to([0.0, 0.0, 1.04], max_steps=8, step_clip=0.02, tol=0.001)
    assert env.actions
    assert all(float(a[6]) == -1.0 for a in env.actions)


def test_move_to_hold_keeps_closed_command() -> None:
    prim, env = _primitives(opening=0.01, move_to_hold=True)
    prim.move_to([0.0, 0.0, 1.04], max_steps=8, step_clip=0.02, tol=0.001)
    assert env.actions
    assert all(float(a[6]) == 1.0 for a in env.actions)


def test_move_to_hold_keeps_open_command() -> None:
    prim, env = _primitives(opening=0.08, move_to_hold=True)
    prim.move_to(
        [0.0, 0.0, 1.04], gripper="hold", max_steps=4, step_clip=0.02, tol=0.001
    )
    assert env.actions
    assert all(float(a[6]) == -1.0 for a in env.actions)


def test_move_to_hold_does_not_chatter_when_opening_drifts() -> None:
    prim, env = _primitives(opening=0.01, drift=0.02, move_to_hold=True)
    prim.move_to(
        [0.0, 0.0, 1.04], gripper="hold", max_steps=4, step_clip=0.02, tol=0.001
    )
    assert env.actions
    assert all(float(a[6]) == 1.0 for a in env.actions)


def test_move_to_original_rejects_hold_string() -> None:
    prim, env = _primitives(opening=0.01, move_to_hold=False)
    with pytest.raises(ValueError, match="libero-move-to-hold"):
        prim.move_to(
            [0.0, 0.0, 1.04], gripper="hold", max_steps=4, step_clip=0.02, tol=0.001
        )
    assert not env.actions


def test_move_to_explicit_open_still_sends_minus_one() -> None:
    prim, env = _primitives(opening=0.01)
    prim.move_to([0.0, 0.0, 1.04], gripper=-1, max_steps=4, step_clip=0.02, tol=0.001)
    assert env.actions
    assert all(float(a[6]) == -1.0 for a in env.actions)


def test_move_to_explicit_close_still_sends_plus_one() -> None:
    prim, env = _primitives(opening=0.08)
    prim.move_to([0.0, 0.0, 1.04], gripper=1, max_steps=4, step_clip=0.02, tol=0.001)
    assert env.actions
    assert all(float(a[6]) == 1.0 for a in env.actions)


def test_tools_spec_hold_overlay() -> None:
    original = {item["name"]: item for item in tools_spec(move_to_hold=False)}["move_to"]
    hold = {item["name"]: item for item in tools_spec(move_to_hold=True)}["move_to"]
    assert original["input_schema"]["properties"]["gripper"]["type"] == "number"
    assert hold["input_schema"]["properties"]["gripper"]["type"] == ["number", "string"]
    assert "hold" in hold["description"].lower()
