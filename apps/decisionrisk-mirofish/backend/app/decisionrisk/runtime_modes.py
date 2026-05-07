"""Adapter for the clean DecisionRisk runtime mode contract."""

from __future__ import annotations

import sys
from pathlib import Path


def _ensure_spec_package_on_path() -> None:
    repo_root = Path(__file__).resolve().parents[5]
    spec_src = repo_root / "packages" / "decisionrisk-spec" / "src"
    if spec_src.exists() and str(spec_src) not in sys.path:
        sys.path.insert(0, str(spec_src))


_ensure_spec_package_on_path()

from decisionrisk.runtime_modes import (  # noqa: E402,F401
    CANONICAL_RUNTIME_MODES,
    LIVE_ENABLE_ENV,
    LIVE_LLM_ENABLE_ENV,
    LIVE_LLM_KEY_ENVS,
    assert_runtime_mode_available,
    parse_runtime_mode,
    runtime_mode_availability,
    runtime_mode_contract,
    runtime_mode_contracts,
)
