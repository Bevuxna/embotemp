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

from robots.rmbench.constants import RMBENCH_TASK_NAMES
from robots.rmbench.overlay import (
    episode_info_from_task,
    install_instruction_overlay,
    resolve_object_model_dir,
    validate_rmbench_assets,
)
from robots.robotwin.robot_spec import _DEFAULT_MAX_EPISODE_STEPS, apply_benchmark_defaults


def test_rmbench_defaults_force_demo_clean_and_step_limit() -> None:
    args = argparse.Namespace(
        benchmark="rmbench",
        task_name="observe_and_pickup",
        task_config="demo_randomized",
        max_episode_steps=_DEFAULT_MAX_EPISODE_STEPS,
    )
    apply_benchmark_defaults(args)
    assert args.task_config == "demo_clean"
    assert args.max_episode_steps == 250


def test_rmbench_unknown_task_rejected() -> None:
    args = argparse.Namespace(
        benchmark="rmbench",
        task_name="beat_block_hammer",
        task_config="demo_clean",
        max_episode_steps=10000,
    )
    with pytest.raises(ValueError, match="unknown RMBench task"):
        apply_benchmark_defaults(args)


def test_instruction_overlay_reads_vendored_json() -> None:
    install_instruction_overlay()
    import robotwin.description.instructions as instructions

    payload = instructions.load_task_instructions("observe_and_pickup")
    assert "seen" in payload
    assert payload["seen"]


def test_validate_rmbench_assets_requires_layout(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="incomplete"):
        validate_rmbench_assets(tmp_path)
    (tmp_path / "assets" / "embodiments" / "aloha-agilex").mkdir(parents=True)
    (tmp_path / "assets" / "objects").mkdir(parents=True)
    identity = validate_rmbench_assets(tmp_path)
    assert identity["benchmark"] == "rmbench"


def test_episode_info_from_task_reads_empty_rmbench_info() -> None:
    class _Task:
        info = {"info": {}}

    assert episode_info_from_task(_Task()) == {}

    class _C2R:
        def get_info(self):
            return {"{A}": "020_hammer/base0"}

    assert episode_info_from_task(_C2R()) == {"{A}": "020_hammer/base0"}


def test_resolve_object_model_dir_uses_assets_path(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("ASSETS_PATH", raising=False)
    monkeypatch.delenv("ROBOTWIN_ASSETS_ROOT", raising=False)
    assert resolve_object_model_dir("009_toycar") == str(
        Path("assets") / "objects" / "009_toycar"
    )
    monkeypatch.setenv("ASSETS_PATH", str(tmp_path))
    assert resolve_object_model_dir("009_toycar") == str(
        tmp_path / "assets" / "objects" / "009_toycar"
    )


def test_rmbench_task_list_matches_overlay_files() -> None:
    overlay = Path(__file__).resolve().parents[4] / "robots" / "rmbench" / "env_overlay"
    files = {path.stem for path in overlay.glob("*.py")}
    assert files == set(RMBENCH_TASK_NAMES)
