from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping


CANONICAL_RUNTIME_MODES = ("replay", "live_smoke", "live_full", "eval")
LIVE_ENABLE_ENV = "DECISIONRISK_ENABLE_LIVE"
LIVE_LLM_ENABLE_ENV = "DECISIONRISK_ENABLE_LIVE_LLM"
LIVE_LLM_KEY_ENVS = ("DECISIONRISK_LLM_API_KEY", "LLM_API_KEY", "OPENAI_API_KEY")


@dataclass(frozen=True)
class RuntimeMode:
    name: str
    purpose: str
    uses_live_mirofish: bool
    uses_live_llm_council: bool
    output_source: str
    final_artifact_source: str
    reduced_scope: bool = False
    council_may_be_mocked: bool = False

    def as_dict(self, env: Mapping[str, str] | None = None) -> dict[str, object]:
        available, unavailable_reasons = runtime_mode_availability(self.name, env)
        return {
            "name": self.name,
            "purpose": self.purpose,
            "uses_live_mirofish": self.uses_live_mirofish,
            "uses_live_llm_council": self.uses_live_llm_council,
            "output_source": self.output_source,
            "final_artifact_source": self.final_artifact_source,
            "reduced_scope": self.reduced_scope,
            "council_may_be_mocked": self.council_may_be_mocked,
            "available": available,
            "unavailable_reasons": unavailable_reasons,
            "preflight_requirements": preflight_requirements(self.name),
        }


RUNTIME_MODES = {
    "replay": RuntimeMode(
        name="replay",
        purpose="Deterministic demo and CI run.",
        uses_live_mirofish=False,
        uses_live_llm_council=False,
        output_source="Fixture artifacts",
        final_artifact_source="verdict.json or risk_docket.md",
    ),
    "live_smoke": RuntimeMode(
        name="live_smoke",
        purpose="Small live MiroFish integration test.",
        uses_live_mirofish=True,
        uses_live_llm_council=False,
        output_source="Live MiroFish artifacts with deterministic council output",
        final_artifact_source="verdict.json or risk_docket.md",
        reduced_scope=True,
        council_may_be_mocked=True,
    ),
    "live_full": RuntimeMode(
        name="live_full",
        purpose="Real product run with live MiroFish and live council configuration.",
        uses_live_mirofish=True,
        uses_live_llm_council=True,
        output_source="Live MiroFish plus live council artifacts",
        final_artifact_source="verdict.json or risk_docket.md",
    ),
    "eval": RuntimeMode(
        name="eval",
        purpose="Regression and golden-output evaluation.",
        uses_live_mirofish=False,
        uses_live_llm_council=False,
        output_source="Golden/eval artifacts",
        final_artifact_source="verdict.json or risk_docket.md",
    ),
}


def parse_runtime_mode(value: str) -> str:
    if value not in RUNTIME_MODES:
        allowed = ", ".join(CANONICAL_RUNTIME_MODES)
        raise ValueError(f"unsupported runtime mode: {value}. Expected one of: {allowed}")
    return value


def runtime_mode_contract(mode: str) -> RuntimeMode:
    return RUNTIME_MODES[parse_runtime_mode(mode)]


def runtime_mode_contracts(env: Mapping[str, str] | None = None) -> list[dict[str, object]]:
    return [RUNTIME_MODES[mode].as_dict(env) for mode in CANONICAL_RUNTIME_MODES]


def preflight_requirements(mode: str) -> list[str]:
    mode = parse_runtime_mode(mode)
    if mode == "live_smoke":
        return [f"{LIVE_ENABLE_ENV}=1"]
    if mode == "live_full":
        return [
            f"{LIVE_ENABLE_ENV}=1",
            f"{LIVE_LLM_ENABLE_ENV}=1",
            "one of " + ", ".join(LIVE_LLM_KEY_ENVS),
        ]
    return []


def runtime_mode_availability(
    mode: str,
    env: Mapping[str, str] | None = None,
) -> tuple[bool, list[str]]:
    mode = parse_runtime_mode(mode)
    env = os.environ if env is None else env
    reasons: list[str] = []
    if mode in {"live_smoke", "live_full"} and env.get(LIVE_ENABLE_ENV) != "1":
        reasons.append(f"{LIVE_ENABLE_ENV}=1 is required for {mode}.")
    if mode == "live_full":
        if env.get(LIVE_LLM_ENABLE_ENV) != "1":
            reasons.append(f"{LIVE_LLM_ENABLE_ENV}=1 is required for live_full.")
        if not any(env.get(name) for name in LIVE_LLM_KEY_ENVS):
            reasons.append("live_full requires one live LLM API key env: " + ", ".join(LIVE_LLM_KEY_ENVS) + ".")
    return not reasons, reasons


def assert_runtime_mode_available(
    mode: str,
    env: Mapping[str, str] | None = None,
) -> None:
    available, reasons = runtime_mode_availability(mode, env)
    if not available:
        raise RuntimeError("runtime mode preflight failed: " + " ".join(reasons))
