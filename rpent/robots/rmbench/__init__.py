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

"""RMBench overlay for the existing RoboTwin RPent robot."""

from robots.rmbench.constants import RMBENCH_STEP_LIMITS, RMBENCH_TASK_NAMES
from robots.rmbench.overlay import (
    install_rmbench_runtime,
    resolve_object_model_dir,
    validate_rmbench_assets,
)

__all__ = [
    "RMBENCH_STEP_LIMITS",
    "RMBENCH_TASK_NAMES",
    "install_rmbench_runtime",
    "resolve_object_model_dir",
    "validate_rmbench_assets",
]
