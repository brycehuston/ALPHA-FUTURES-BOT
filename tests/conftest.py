"""Shared pytest helpers for Phase 1 safety tests."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest


@pytest.fixture
def valid_config_dict() -> Callable[[], dict[str, Any]]:
    def make_config() -> dict[str, Any]:
        return {
            "mode": "PAPER",
            "symbol": "BTC",
            "risk": {
                "max_position_notional": 1_000.0,
                "max_risk_per_trade_pct": 1.0,
                "min_signal_score": 0.65,
                "max_leverage": 1.0,
            },
        }

    return make_config
