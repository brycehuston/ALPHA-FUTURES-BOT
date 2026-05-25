from __future__ import annotations

from dataclasses import fields

import pytest

from alpha_futures_bot.config import BotConfig, ConfigError, RiskSettings, default_config, load_config
from alpha_futures_bot.models import BotMode, Symbol


def test_default_config_validates() -> None:
    config = default_config()

    assert config.mode is BotMode.PAPER
    assert config.symbol is Symbol.BTC
    assert isinstance(config.risk, RiskSettings)
    assert config.risk.min_signal_score == 70.0
    assert config.risk.max_position_notional == 10_000.0
    assert config.risk.max_risk_per_trade_pct == 0.005
    assert config.risk.daily_max_loss_pct == 0.02
    assert config.risk.max_open_positions == 1


@pytest.mark.parametrize("mode", ["PAPER", "TEST", BotMode.PAPER, BotMode.TEST])
def test_paper_and_test_modes_validate(valid_config_dict, mode) -> None:
    raw = valid_config_dict()
    raw["mode"] = mode

    config = load_config(raw)

    assert config.mode in {BotMode.PAPER, BotMode.TEST}


@pytest.mark.parametrize("mode", ["LIVE", "MAINNET", "REAL", "PRODUCTION_TRADING", "SANDBOX"])
def test_forbidden_and_unknown_modes_fail_closed(valid_config_dict, mode: str) -> None:
    raw = valid_config_dict()
    raw["mode"] = mode

    with pytest.raises(ConfigError):
        load_config(raw)


@pytest.mark.parametrize("symbol", ["ETH", "SOL", "BTC-PERP", "UNKNOWN"])
def test_only_btc_is_allowed(valid_config_dict, symbol: str) -> None:
    raw = valid_config_dict()
    raw["symbol"] = symbol

    with pytest.raises(ConfigError):
        load_config(raw)


@pytest.mark.parametrize(
    "key",
    [
        "api_key",
        "secret",
        "private_key",
        "wallet",
        "mnemonic",
        "seed",
        "token",
        "password",
        "exchange_secret",
    ],
)
def test_secret_like_top_level_keys_fail(valid_config_dict, key: str) -> None:
    raw = valid_config_dict()
    raw[key] = "not-allowed"

    with pytest.raises(ConfigError):
        load_config(raw)


def test_secret_like_nested_keys_fail(valid_config_dict) -> None:
    raw = valid_config_dict()
    raw["risk"]["api_key"] = "not-allowed"

    with pytest.raises(ConfigError):
        load_config(raw)


def test_unknown_top_level_keys_fail(valid_config_dict) -> None:
    raw = valid_config_dict()
    raw["exchange"] = "hyperliquid"

    with pytest.raises(ConfigError):
        load_config(raw)


def test_unknown_risk_keys_fail(valid_config_dict) -> None:
    raw = valid_config_dict()
    raw["risk"]["daily_loss_limit"] = 100

    with pytest.raises(ConfigError):
        load_config(raw)


def test_missing_top_level_risk_fails(valid_config_dict) -> None:
    raw = valid_config_dict()
    del raw["risk"]

    with pytest.raises(ConfigError):
        load_config(raw)


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("max_position_notional", 0),
        ("max_position_notional", -1),
        ("max_risk_per_trade_pct", 0),
        ("max_risk_per_trade_pct", 1.01),
        ("min_signal_score", -0.01),
        ("min_signal_score", 100.01),
        ("max_leverage", 2.0),
        ("max_leverage", 0.0),
        ("daily_max_loss_pct", 0),
        ("daily_max_loss_pct", 1.01),
        ("max_open_positions", 0),
        ("max_open_positions", 1.5),
    ],
)
def test_invalid_risk_settings_fail(valid_config_dict, key: str, value: float) -> None:
    raw = valid_config_dict()
    raw["risk"][key] = value

    with pytest.raises(ConfigError):
        load_config(raw)


@pytest.mark.parametrize(
    "missing_key",
    [
        "max_position_notional",
        "max_risk_per_trade_pct",
        "min_signal_score",
        "max_leverage",
        "daily_max_loss_pct",
        "max_open_positions",
    ],
)
def test_missing_risk_settings_fail(valid_config_dict, missing_key: str) -> None:
    raw = valid_config_dict()
    del raw["risk"][missing_key]

    with pytest.raises(ConfigError):
        load_config(raw)


def test_config_models_do_not_expose_exchange_or_private_key_fields() -> None:
    forbidden_fragments = ("exchange", "api", "secret", "private", "key", "wallet")
    config_field_names = {field.name for field in fields(BotConfig)}
    risk_field_names = {field.name for field in fields(RiskSettings)}

    exposed = {
        name
        for name in config_field_names | risk_field_names
        if any(fragment in name.lower() for fragment in forbidden_fragments)
    }

    assert exposed == set()
