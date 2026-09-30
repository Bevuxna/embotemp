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

"""Register LIBERO-Mem on the installed liberopro / RLinf runtime."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from robots.libero_mem.constants import (
    DEFAULT_LIBERO_MEM_ROOT,
    LIBERO_MEM_BDDL_RELATIVE,
    LIBERO_MEM_INIT_ALIASES,
    LIBERO_MEM_INIT_RELATIVE,
    LIBERO_MEM_SUITE,
    LIBERO_MEM_TASK_NAMES,
)
from robots.libero_mem.sequential import (
    check_success,
    is_sequential_goal,
    reset_subgoal_progress,
)
from rpent.utils.logging import get_logger

logger = get_logger("libero_mem")

_LANG_TAG_RE = re.compile(r"\(:language\s+([^)]+)\)")

_BENCHMARK_INSTALLED = False
_SUCCESS_PATCHED = False
_ENV_FN_WRAPPED = False


def resolve_libero_mem_root(path: str | Path | None = None) -> Path:
    """Resolve the sparse LIBERO-Mem clone (BDDL + pruned_init + source)."""
    if path is not None:
        return Path(path).expanduser().resolve()
    env = os.environ.get("LIBERO_MEM_PATH")
    if env:
        return Path(env).expanduser().resolve()
    try:
        from rpent.utils.config import get_repo_root

        sibling = get_repo_root().parent / "LIBERO-Mem"
    except Exception:
        sibling = DEFAULT_LIBERO_MEM_ROOT
    for candidate in (DEFAULT_LIBERO_MEM_ROOT, sibling):
        if (candidate / LIBERO_MEM_BDDL_RELATIVE).is_dir():
            return candidate.resolve()
    return DEFAULT_LIBERO_MEM_ROOT


def bddl_dir(root: Path | None = None) -> Path:
    return resolve_libero_mem_root(root) / LIBERO_MEM_BDDL_RELATIVE


def init_dir(root: Path | None = None) -> Path:
    return resolve_libero_mem_root(root) / LIBERO_MEM_INIT_RELATIVE


def init_file_for_task(task_name: str, root: Path | None = None) -> Path:
    alias = LIBERO_MEM_INIT_ALIASES.get(task_name, task_name)
    return init_dir(root) / f"{alias}.pruned_init"


def language_from_bddl(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    match = _LANG_TAG_RE.search(text)
    if match:
        return match.group(1).strip()
    return path.stem.replace("_", " ")


def validate_libero_mem_assets(path: str | Path | None = None) -> dict[str, Any]:
    """Check the sparse clone has the 10 BDDLs and 4 shared init files."""
    root = resolve_libero_mem_root(path)
    missing: list[str] = []
    bddl_root = bddl_dir(root)
    for name in LIBERO_MEM_TASK_NAMES:
        candidate = bddl_root / f"{name}.bddl"
        if not candidate.is_file():
            missing.append(str(candidate))
    needed_inits = {f"{alias}.pruned_init" for alias in LIBERO_MEM_INIT_ALIASES.values()}
    init_root = init_dir(root)
    for filename in sorted(needed_inits):
        candidate = init_root / filename
        if not candidate.is_file():
            missing.append(str(candidate))
    if missing:
        raise ValueError(
            "LIBERO-Mem sparse clone is incomplete; missing: "
            f"{missing}. Set LIBERO_MEM_PATH to the libero-mem/libero-mem "
            "checkout (BDDL + scripts/__init_data only; do not pip-install it)."
        )
    return {
        "root": str(root),
        "suite": LIBERO_MEM_SUITE,
        "n_tasks": len(LIBERO_MEM_TASK_NAMES),
        "bddl_dir": str(bddl_root),
        "init_dir": str(init_root),
    }


def _register_benchmark(root: Path) -> None:
    global _BENCHMARK_INSTALLED
    if _BENCHMARK_INSTALLED:
        return

    import torch
    from rlinf.envs.libero.utils import benchmark as bench

    identity = validate_libero_mem_assets(root)
    tasks: dict[str, Any] = {}
    for name in LIBERO_MEM_TASK_NAMES:
        bddl_path = bddl_dir(root) / f"{name}.bddl"
        tasks[name] = bench.Task(
            name=name,
            language=language_from_bddl(bddl_path),
            problem="Libero",
            problem_folder=LIBERO_MEM_SUITE,
            bddl_file=f"{name}.bddl",
            init_states_file=f"{LIBERO_MEM_INIT_ALIASES[name]}.pruned_init",
        )

    bench.task_maps[LIBERO_MEM_SUITE] = tasks
    if LIBERO_MEM_SUITE not in getattr(bench, "libero_suites", []):
        try:
            bench.libero_suites.append(LIBERO_MEM_SUITE)
        except Exception:
            pass

    class LIBERO_MEM(bench.Benchmark):
        def __init__(self, task_order_index: int = 0):
            super().__init__(task_order_index=task_order_index)
            self.name = LIBERO_MEM_SUITE
            self._make_benchmark()

        def _make_benchmark(self):
            self.tasks = list(bench.task_maps[LIBERO_MEM_SUITE].values())
            self.n_tasks = len(self.tasks)

        def get_task_bddl_file_path(self, i: int) -> str:
            return str(bddl_dir(root) / self.tasks[i].bddl_file)

        def get_task_init_states(self, i: int):
            path = init_file_for_task(self.tasks[i].name, root)
            return torch.load(path, weights_only=False)

    bench.BENCHMARK_MAPPING[LIBERO_MEM_SUITE] = LIBERO_MEM
    bench.BENCHMARK_MAPPING["libero_mem"] = LIBERO_MEM
    _BENCHMARK_INSTALLED = True
    logger.info(
        "LIBERO-Mem benchmark registered (%s tasks) from %s",
        identity["n_tasks"],
        identity["root"],
    )


def install_success_patches() -> None:
    """Patch kitchen success + reset so Sequence goals do not fire at t=0.

    Workers spawn a fresh interpreter, so this must also run inside env_fn.
    Only kitchen Sequence/Or goals use the sequential checker; flat AND
    goals keep the original leaf-AND behavior.
    """
    global _SUCCESS_PATCHED
    if _SUCCESS_PATCHED:
        return

    import liberopro.liberopro.envs as libero_envs
    from liberopro.liberopro.envs.bddl_base_domain import BDDLBaseDomain, TASK_MAPPING
    from liberopro.liberopro.envs.env_wrapper import ControlEnv

    kitchen_cls = TASK_MAPPING.get("libero_kitchen_tabletop_manipulation")
    if kitchen_cls is None:
        kitchen_cls = getattr(
            libero_envs, "Libero_Kitchen_Tabletop_Manipulation", None
        )
    if kitchen_cls is None:
        raise RuntimeError(
            "liberopro kitchen problem class is not registered; "
            "cannot install LIBERO-Mem sequential success patches"
        )

    original_kitchen_check = kitchen_cls._check_success
    original_domain_step = BDDLBaseDomain.step
    original_control_reset = ControlEnv.reset
    original_regen = ControlEnv.regenerate_obs_from_state

    def _check_success(self, inc: bool = False):
        goal_state = getattr(self, "parsed_problem", {}).get("goal_state")
        if is_sequential_goal(goal_state):
            return check_success(self, inc=inc)
        return original_kitchen_check(self)

    def _domain_step(self, action):
        obs, reward, done, info = original_domain_step(self, action)
        # Stock step already called _check_success() without inc (no dwell).
        if is_sequential_goal(getattr(self, "parsed_problem", {}).get("goal_state")):
            done = self._check_success(inc=True)
        return obs, reward, done, info

    def _control_reset(self):
        ret = original_control_reset(self)
        reset_subgoal_progress(self.env)
        return ret

    def _regenerate_obs_from_state(self, mujoco_state):
        reset_subgoal_progress(self.env)
        return original_regen(self, mujoco_state)

    kitchen_cls._check_success = _check_success
    BDDLBaseDomain.step = _domain_step
    ControlEnv.reset = _control_reset
    ControlEnv.regenerate_obs_from_state = _regenerate_obs_from_state
    _SUCCESS_PATCHED = True
    logger.info("LIBERO-Mem sequential success patches installed")


def _wrap_worker_env_fn(inner):
    def env_fn():
        install_success_patches()
        return inner()

    return env_fn


def install_env_fn_wrapper() -> None:
    """Make spawn workers install success patches before OffScreenRenderEnv."""
    global _ENV_FN_WRAPPED
    if _ENV_FN_WRAPPED:
        return

    from rlinf.envs.libero.libero_env import LiberoEnv

    original_get_env_fns = LiberoEnv.get_env_fns
    original_get_env_fn_params = LiberoEnv.get_env_fn_params

    def get_env_fns(self):
        fns = original_get_env_fns(self)
        if str(self.cfg.task_suite_name).lower() != LIBERO_MEM_SUITE:
            return fns
        return [_wrap_worker_env_fn(fn) for fn in fns]

    def get_env_fn_params(self, env_idx=None):
        params = original_get_env_fn_params(self, env_idx)
        if str(self.cfg.task_suite_name).lower() != LIBERO_MEM_SUITE:
            return params
        import numpy as np

        if env_idx is None:
            env_idx = np.arange(self.num_envs)
        included = [int(i) for i in range(self.num_envs) if i in env_idx]
        for param, env_id in zip(params, included):
            task_id = int(self.task_ids[env_id])
            param["bddl_file_name"] = self.task_suite.get_task_bddl_file_path(task_id)
        return params

    LiberoEnv.get_env_fns = get_env_fns
    LiberoEnv.get_env_fn_params = get_env_fn_params
    _ENV_FN_WRAPPED = True
    logger.info("LIBERO-Mem env_fn wrapper installed")


def install_libero_mem_runtime(path: str | Path | None = None) -> dict[str, Any]:
    """Register the suite, point BDDL/init at the clone, patch success."""
    root = resolve_libero_mem_root(path)
    os.environ.setdefault("LIBERO_MEM_PATH", str(root))
    identity = validate_libero_mem_assets(root)
    _register_benchmark(root)
    install_env_fn_wrapper()
    install_success_patches()
    return identity
