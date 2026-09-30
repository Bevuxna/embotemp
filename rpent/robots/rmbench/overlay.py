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

"""Register RMBench tasks and instructions onto the packaged RoboTwin runtime."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any

from robots.rmbench.constants import (
    RMBENCH_ENV_OVERLAY,
    RMBENCH_INSTRUCTION_DIR,
    RMBENCH_REQUIRED_ASSET_DIRECTORIES,
    RMBENCH_STEP_LIMITS,
    RMBENCH_TASK_NAMES,
)
from rpent.utils.logging import get_logger

logger = get_logger("rmbench")

_ENV_OVERLAY_INSTALLED = False
_INSTRUCTION_OVERLAY_INSTALLED = False


_SETUP_TASK_FAILFAST_INSTALLED = False
_GET_INFO_FALLBACK_INSTALLED = False
_STEP_LIMIT_OVERLAY_INSTALLED = False
_SETUP_TASK_MAX_TRIES = 8


def episode_info_from_task(task: Any) -> dict[str, Any]:
    """C2R ``setup_task`` wants ``get_info()``; RMBench tasks only fill ``info``."""
    getter = getattr(task, "get_info", None)
    if callable(getter):
        payload = getter()
        if isinstance(payload, dict):
            return payload
    info = getattr(task, "info", None)
    if isinstance(info, dict) and isinstance(info.get("info"), dict):
        return info["info"]
    return {}


def resolve_object_model_dir(modelname: str) -> str:
    """Resolve ``assets/objects/<model>`` against the configured asset root.

    Official RMBench tasks join ``assets/objects`` to the process cwd. That
    only works when the shell is already sitting in the asset snapshot root.
    """
    root = os.environ.get("ASSETS_PATH") or os.environ.get("ROBOTWIN_ASSETS_ROOT")
    if root:
        return str(Path(root) / "assets" / "objects" / modelname)
    return str(Path("assets") / "objects" / modelname)


def validate_rmbench_assets(path: str | Path) -> dict[str, Any]:
    """Check RMBench asset layout. Do not pin the RoboTwin2.0 revision."""
    root = Path(path).expanduser().resolve()
    missing = [
        str(root / value)
        for value in RMBENCH_REQUIRED_ASSET_DIRECTORIES
        if not (root / value).is_dir()
    ]
    if missing:
        raise ValueError(
            "RMBench asset snapshot is incomplete; missing directories: "
            f"{missing}. Download TianxingChen/RMBench (dataset) into this root."
        )
    return {
        "root": str(root),
        "benchmark": "rmbench",
        "repository": "TianxingChen/RMBench",
    }


def install_env_overlay(overlay_dir: Path | None = None) -> list[str]:
    """Expose RMBench task modules as ``robotwin.envs.<task>``.

    Relative imports in the vendored files keep using the installed
    ``robotwin.envs._base_task`` and ``robotwin.envs.utils``.
    """
    global _ENV_OVERLAY_INSTALLED
    overlay = Path(overlay_dir or RMBENCH_ENV_OVERLAY)
    if not overlay.is_dir():
        raise FileNotFoundError(f"RMBench env overlay directory not found: {overlay}")

    import robotwin.envs  # noqa: F401  # ensure parent package exists

    installed: list[str] = []
    for task_name in RMBENCH_TASK_NAMES:
        module_name = f"robotwin.envs.{task_name}"
        if module_name in sys.modules:
            installed.append(task_name)
            continue
        source = overlay / f"{task_name}.py"
        if not source.is_file():
            raise FileNotFoundError(f"RMBench task module missing: {source}")
        spec = importlib.util.spec_from_file_location(module_name, source)
        if spec is None or spec.loader is None:
            raise ImportError(f"failed to build spec for {module_name}")
        module = importlib.util.module_from_spec(spec)
        module.__package__ = "robotwin.envs"
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        installed.append(task_name)
    _ENV_OVERLAY_INSTALLED = True
    logger.info("RMBench env overlay installed: %s", ",".join(installed))
    return installed


def install_instruction_overlay(instruction_dir: Path | None = None) -> None:
    """Prefer RMBench JSON templates, then fall back to packaged RoboTwin files."""
    global _INSTRUCTION_OVERLAY_INSTALLED
    if _INSTRUCTION_OVERLAY_INSTALLED:
        return
    directory = Path(instruction_dir or RMBENCH_INSTRUCTION_DIR)
    import robotwin.description.instructions as instructions

    original = instructions.load_task_instructions

    def load_task_instructions(task_name: str) -> dict[str, Any]:
        local = directory / f"{task_name}.json"
        if local.is_file():
            with local.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
            if not isinstance(payload, dict):
                raise TypeError(f"RMBench instruction file must be a mapping: {local}")
            return payload
        return original(task_name)

    instructions.load_task_instructions = load_task_instructions
    _INSTRUCTION_OVERLAY_INSTALLED = True
    logger.info("RMBench instruction overlay: %s", directory)


def install_get_info_fallback() -> None:
    """Give RMBench tasks the C2R ``get_info()`` hook used by ``setup_task``."""
    global _GET_INFO_FALLBACK_INSTALLED
    if _GET_INFO_FALLBACK_INSTALLED:
        return

    from robotwin.envs._base_task import Base_Task

    if "get_info" not in Base_Task.__dict__:

        def get_info(self) -> dict[str, Any]:
            info = getattr(self, "info", None)
            if isinstance(info, dict) and isinstance(info.get("info"), dict):
                return info["info"]
            return {}

        Base_Task.get_info = get_info  # type: ignore[method-assign]
    _GET_INFO_FALLBACK_INSTALLED = True
    logger.info("RMBench Base_Task.get_info fallback installed")


def install_step_limit_overlay() -> None:
    """Merge official RMBench ``step_lim`` values into packaged eval limits."""
    global _STEP_LIMIT_OVERLAY_INSTALLED
    if _STEP_LIMIT_OVERLAY_INSTALLED:
        return

    import robotwin.config as config
    import robotwin.envs._base_task as base_task

    original = config.load_task_config

    def load_task_config(name: str) -> dict[str, Any]:
        payload = original(name)
        stem = str(name).removesuffix(".yaml").removesuffix(".yml")
        if stem == "_eval_step_limit":
            merged = dict(payload)
            merged.update(RMBENCH_STEP_LIMITS)
            return merged
        return payload

    config.load_task_config = load_task_config
    base_task.load_task_config = load_task_config
    _STEP_LIMIT_OVERLAY_INSTALLED = True
    logger.info("RMBench step-limit overlay installed")


def install_setup_task_failfast(max_tries: int = _SETUP_TASK_MAX_TRIES) -> None:
    """Stop packaged ``SubEnv.setup_task`` from retrying a hard failure forever.

    The installed runtime swallows every ``setup_demo`` exception and walks
    seeds indefinitely. A missing relative asset path then looks like a 900s
    healthz timeout instead of the real error.
    """
    global _SETUP_TASK_FAILFAST_INSTALLED
    if _SETUP_TASK_FAILFAST_INSTALLED:
        return

    from robotwin.envs.vector_env import SubEnv, class_decorator

    original_max = int(max_tries)

    def setup_task(self) -> None:
        self.close()
        self.task = class_decorator(self.task_name)
        last_error: BaseException | None = None
        episode_info = None
        with self.global_lock:
            with self.lock:
                trial_seed = self.env_seed
                for attempt in range(original_max):
                    task = None
                    try:
                        task = class_decorator(self.task_name)
                        task.setup_demo(
                            now_ep_num=trial_seed,
                            seed=trial_seed,
                            is_test=True,
                            **self.args,
                        )
                        episode_info = episode_info_from_task(task)
                        break
                    except Exception as exc:
                        last_error = exc
                        logger.exception(
                            "RMBench setup_demo failed (attempt %s/%s, seed=%s)",
                            attempt + 1,
                            original_max,
                            trial_seed,
                        )
                        if task is not None:
                            try:
                                task.close_env()
                            except Exception:
                                pass
                        trial_seed += 1
                else:
                    raise RuntimeError(
                        f"RMBench setup_demo failed after {original_max} seeds "
                        f"starting from {self.env_seed}"
                    ) from last_error
                if task is not None:
                    task.close_env()
                self.episode_info_list = [episode_info]

    SubEnv.setup_task = setup_task  # type: ignore[method-assign]
    _SETUP_TASK_FAILFAST_INSTALLED = True
    logger.info("RMBench setup_task fail-fast installed (max_tries=%s)", original_max)


def install_rmbench_runtime() -> None:
    """Install both overlays before constructing a RoboTwin env."""
    install_instruction_overlay()
    install_step_limit_overlay()
    install_get_info_fallback()
    install_env_overlay()
    install_setup_task_failfast()
