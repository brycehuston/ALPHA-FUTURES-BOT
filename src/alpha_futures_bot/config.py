"""Safe configuration defaults and validation for V1."""

from __future__ import annotations

from dataclasses import dataclass, fields
from enum import Enum
from typing import Any, Mapping

from alpha_futures_bot.models import BotMode, Symbol


class ConfigError(ValueError):
    """Raised when configuration cannot be safely accepted."""


SECRET_LIKE_KEYS = {
    "api_key",
    "apikey",
    "api_secret",
    "secret",
    "private_key",
    "privatekey",
    "wallet",
    "wallet_address",
    "mnemonic",
    "seed",
    "seed_phrase",
    "token",
    "password",
    "passphrase",
    "exchange_key",
    "exchange_secret",
}

FORBIDDEN_MODES = {"LIVE", "MAINNET", "REAL", "PRODUCTION_TRADING"}
ALLOWED_TOP_LEVEL_KEYS = {"mode", "symbol", "risk"}


@dataclass(frozen=True, slots=True)
class RiskSettings:
    """Static risk settings required before any future paper order is allowed."""

    max_position_notional: float = 1_000.0
    max_risk_per_trade_pct: float = 1.0
    min_signal_score: float = 0.65
    max_leverage: float = 1.0


@dataclass(frozen=True, slots=True)
class BotConfig:
    """Validated V1 config.

    This type intentionally exposes no exchange, API key, wallet, or private-key
    fields. V1 is config-only and cannot execute real or testnet trades.
    """

    mode: BotMode = BotMode.PAPER
    symbol: Symbol = Symbol.BTC
    risk: RiskSettings = RiskSettings()


def default_config() -> BotConfig:
    """Return a validated safe default config."""

    return validate_config(BotConfig())


def load_config(raw: Mapping[str, Any] | None = None) -> BotConfig:
    """Load config from an in-memory mapping.

    No files, environment variables, secret stores, or .env files are read in V1.
    Passing a mapping represents an explicit external config, so all required
    top-level sections must be present.
    """

    if raw is None:
        return default_config()

    _assert_mapping(raw, "config")
    _reject_secret_like_keys(raw)
    _reject_unknown_keys(raw.keys(), ALLOWED_TOP_LEVEL_KEYS, "config")

    missing = ALLOWED_TOP_LEVEL_KEYS - set(raw.keys())
    if missing:
        raise ConfigError(f"Missing required config key(s): {', '.join(sorted(missing))}")

    return validate_config(
        BotConfig(
            mode=_parse_mode(raw["mode"]),
            symbol=_parse_symbol(raw["symbol"]),
            risk=_parse_risk(raw["risk"]),
        )
    )


def validate_config(config: BotConfig) -> BotConfig:
    """Fail closed unless config is explicitly within V1 safety boundaries."""

    if not isinstance(config, BotConfig):
        raise ConfigError("Config must be a BotConfig instance")
    if config.mode not in {BotMode.PAPER, BotMode.TEST}:
        raise ConfigError(f"Unsupported mode: {config.mode}")
    if config.symbol is not Symbol.BTC:
        raise ConfigError(f"Unsupported symbol: {config.symbol}")
    _validate_risk(config.risk)
    return config


def _parse_mode(value: Any) -> BotMode:
    normalized = _normalize_enum_value(value)
    if normalized in FORBIDDEN_MODES:
        raise ConfigError(f"Forbidden mode: {normalized}")
    try:
        return BotMode(normalized)
    except ValueError as exc:
        raise ConfigError(f"Unsupported mode: {value}") from exc


def _parse_symbol(value: Any) -> Symbol:
    normalized = _normalize_enum_value(value)
    try:
        return Symbol(normalized)
    except ValueError as exc:
        raise ConfigError(f"Unsupported symbol: {value}") from exc


def _parse_risk(value: Any) -> RiskSettings:
    _assert_mapping(value, "risk")
    _reject_secret_like_keys(value)
    allowed = {field.name for field in fields(RiskSettings)}
    _reject_unknown_keys(value.keys(), allowed, "risk")
    missing = allowed - set(value.keys())
    if missing:
        raise ConfigError(f"Missing required risk key(s): {', '.join(sorted(missing))}")
    return RiskSettings(
        max_position_notional=_parse_number(value["max_position_notional"], "max_position_notional"),
        max_risk_per_trade_pct=_parse_number(value["max_risk_per_trade_pct"], "max_risk_per_trade_pct"),
        min_signal_score=_parse_number(value["min_signal_score"], "min_signal_score"),
        max_leverage=_parse_number(value["max_leverage"], "max_leverage"),
    )


def _validate_risk(risk: RiskSettings) -> None:
    if not isinstance(risk, RiskSettings):
        raise ConfigError("Risk settings must be a RiskSettings instance")
    if risk.max_position_notional <= 0:
        raise ConfigError("max_position_notional must be greater than 0")
    if not 0 < risk.max_risk_per_trade_pct <= 100:
        raise ConfigError("max_risk_per_trade_pct must be in the range (0, 100]")
    if not 0 <= risk.min_signal_score <= 1:
        raise ConfigError("min_signal_score must be in the range [0, 1]")
    if risk.max_leverage != 1.0:
        raise ConfigError("max_leverage must remain 1.0 in V1")


def _parse_number(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigError(f"{name} must be numeric")
    return float(value)


def _normalize_enum_value(value: Any) -> str:
    if isinstance(value, Enum):
        value = value.value
    if not isinstance(value, str):
        raise ConfigError(f"Enum value must be a string, got {type(value).__name__}")
    return value.strip().upper()


def _assert_mapping(value: Any, name: str) -> None:
    if not isinstance(value, Mapping):
        raise ConfigError(f"{name} must be a mapping")


def _reject_unknown_keys(keys: Any, allowed: set[str], section: str) -> None:
    unknown = set(keys) - allowed
    if unknown:
        raise ConfigError(f"Unknown {section} key(s): {', '.join(sorted(unknown))}")


def _reject_secret_like_keys(mapping: Mapping[str, Any]) -> None:
    for key, value in mapping.items():
        normalized = str(key).lower().replace("-", "_")
        if normalized in SECRET_LIKE_KEYS:
            raise ConfigError(f"Secret-like config key is not allowed: {key}")
        if isinstance(value, Mapping):
            _reject_secret_like_keys(value)
