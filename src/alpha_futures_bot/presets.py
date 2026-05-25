"""Local strategy research presets for offline BTC paper simulations."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite


class PresetError(ValueError):
    """Raised when a local strategy preset cannot be safely accepted."""


@dataclass(frozen=True, slots=True)
class StrategySettings:
    name: str
    min_signal_score: float
    pullback_atr_tolerance: float
    stop_loss_atr_multiplier: float
    take_profit_atr_multiplier: float
    require_volume_confirmation: bool
    require_candle_confirmation: bool
    vwap_near_atr_multiplier: float
    regime_near_vwap_atr_multiplier: float

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name:
            raise PresetError("Preset name must be a non-empty string")
        numeric_values = (
            self.min_signal_score,
            self.pullback_atr_tolerance,
            self.stop_loss_atr_multiplier,
            self.take_profit_atr_multiplier,
            self.vwap_near_atr_multiplier,
            self.regime_near_vwap_atr_multiplier,
        )
        if any(not _finite_number(value) for value in numeric_values):
            raise PresetError("Preset numeric settings must be finite numbers")
        if not 0 <= self.min_signal_score <= 100:
            raise PresetError("Preset min_signal_score must be in [0, 100]")
        if self.pullback_atr_tolerance <= 0:
            raise PresetError("Preset pullback_atr_tolerance must be greater than 0")
        if self.stop_loss_atr_multiplier <= 0 or self.take_profit_atr_multiplier <= 0:
            raise PresetError("Preset ATR stop/take-profit multipliers must be greater than 0")
        if self.vwap_near_atr_multiplier <= 0 or self.regime_near_vwap_atr_multiplier <= 0:
            raise PresetError("Preset VWAP near multipliers must be greater than 0")
        if not isinstance(self.require_volume_confirmation, bool):
            raise PresetError("Preset require_volume_confirmation must be bool")
        if not isinstance(self.require_candle_confirmation, bool):
            raise PresetError("Preset require_candle_confirmation must be bool")


def _finite_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(value)


STRICT_PRESET = StrategySettings(
    name="strict",
    min_signal_score=80.0,
    pullback_atr_tolerance=0.35,
    stop_loss_atr_multiplier=1.25,
    take_profit_atr_multiplier=3.0,
    require_volume_confirmation=True,
    require_candle_confirmation=True,
    vwap_near_atr_multiplier=0.15,
    regime_near_vwap_atr_multiplier=0.15,
)

BALANCED_PRESET = StrategySettings(
    name="balanced",
    min_signal_score=70.0,
    pullback_atr_tolerance=0.5,
    stop_loss_atr_multiplier=1.5,
    take_profit_atr_multiplier=3.0,
    require_volume_confirmation=True,
    require_candle_confirmation=True,
    vwap_near_atr_multiplier=0.25,
    regime_near_vwap_atr_multiplier=0.25,
)

LOOSE_PRESET = StrategySettings(
    name="loose",
    min_signal_score=60.0,
    pullback_atr_tolerance=0.75,
    stop_loss_atr_multiplier=1.75,
    take_profit_atr_multiplier=2.5,
    require_volume_confirmation=False,
    require_candle_confirmation=False,
    vwap_near_atr_multiplier=0.35,
    regime_near_vwap_atr_multiplier=0.35,
)

PRESETS = {
    STRICT_PRESET.name: STRICT_PRESET,
    BALANCED_PRESET.name: BALANCED_PRESET,
    LOOSE_PRESET.name: LOOSE_PRESET,
}
PRESET_NAMES = tuple(PRESETS.keys())


def get_preset(name: str | StrategySettings | None = None) -> StrategySettings:
    if isinstance(name, StrategySettings):
        return name
    normalized = "balanced" if name is None else str(name).strip().lower()
    try:
        return PRESETS[normalized]
    except KeyError as exc:
        raise PresetError(f"Unknown strategy preset: {name}") from exc
