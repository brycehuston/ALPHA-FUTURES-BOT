"""ALPHA-FUTURES-BOT safe V1 package skeleton."""

from alpha_futures_bot.config import BotConfig, ConfigError, RiskSettings, default_config, load_config
from alpha_futures_bot.indicators import IndicatorSnapshot, calculate_indicators
from alpha_futures_bot.models import (
    BotMode,
    Candle,
    OrderRequest,
    PaperPosition,
    Regime,
    Side,
    Signal,
    SignalAction,
    Symbol,
)
from alpha_futures_bot.regime import detect_regime
from alpha_futures_bot.strategy import generate_signal

__all__ = [
    "BotConfig",
    "BotMode",
    "Candle",
    "ConfigError",
    "IndicatorSnapshot",
    "OrderRequest",
    "PaperPosition",
    "Regime",
    "RiskSettings",
    "Side",
    "Signal",
    "SignalAction",
    "Symbol",
    "calculate_indicators",
    "default_config",
    "detect_regime",
    "generate_signal",
    "load_config",
]
