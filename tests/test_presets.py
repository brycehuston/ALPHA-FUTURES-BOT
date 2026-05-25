from __future__ import annotations

import pytest

from alpha_futures_bot.presets import BALANCED_PRESET, LOOSE_PRESET, PRESET_NAMES, STRICT_PRESET, PresetError, StrategySettings, get_preset


def test_valid_preset_names_load() -> None:
    assert PRESET_NAMES == ("strict", "balanced", "loose")
    assert get_preset("strict") is STRICT_PRESET
    assert get_preset("balanced") is BALANCED_PRESET
    assert get_preset("loose") is LOOSE_PRESET
    assert get_preset(None) is BALANCED_PRESET


def test_invalid_preset_names_fail_closed() -> None:
    for name in ("", "default", "LIVE", "remote"):
        with pytest.raises(PresetError):
            get_preset(name)


def test_balanced_preset_matches_current_defaults() -> None:
    assert BALANCED_PRESET.min_signal_score == 70.0
    assert BALANCED_PRESET.pullback_atr_tolerance == 0.5
    assert BALANCED_PRESET.stop_loss_atr_multiplier == 1.5
    assert BALANCED_PRESET.take_profit_atr_multiplier == 3.0
    assert BALANCED_PRESET.require_volume_confirmation is True
    assert BALANCED_PRESET.require_candle_confirmation is True
    assert BALANCED_PRESET.vwap_near_atr_multiplier == 0.25
    assert BALANCED_PRESET.regime_near_vwap_atr_multiplier == 0.25


def test_loose_preset_uses_lower_min_score_than_balanced() -> None:
    assert LOOSE_PRESET.min_signal_score == 60.0
    assert LOOSE_PRESET.min_signal_score < BALANCED_PRESET.min_signal_score


@pytest.mark.parametrize(
    "kwargs",
    [
        {"min_signal_score": -1.0},
        {"min_signal_score": 101.0},
        {"pullback_atr_tolerance": 0.0},
        {"stop_loss_atr_multiplier": 0.0},
        {"take_profit_atr_multiplier": 0.0},
        {"require_volume_confirmation": 1},
        {"require_candle_confirmation": "yes"},
        {"vwap_near_atr_multiplier": 0.0},
        {"regime_near_vwap_atr_multiplier": 0.0},
    ],
)
def test_invalid_strategy_settings_fail_validation(kwargs: dict[str, object]) -> None:
    values = {
        "name": "test",
        "min_signal_score": 70.0,
        "pullback_atr_tolerance": 0.5,
        "stop_loss_atr_multiplier": 1.5,
        "take_profit_atr_multiplier": 3.0,
        "require_volume_confirmation": True,
        "require_candle_confirmation": True,
        "vwap_near_atr_multiplier": 0.25,
        "regime_near_vwap_atr_multiplier": 0.25,
    }
    values.update(kwargs)

    with pytest.raises(PresetError):
        StrategySettings(**values)
