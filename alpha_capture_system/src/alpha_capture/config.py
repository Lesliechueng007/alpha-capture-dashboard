from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

from .models import StrategyConfig, UniverseAsset


def _read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_universe(path: Path) -> Dict[str, UniverseAsset]:
    raw = _read_json(path)
    universe: Dict[str, UniverseAsset] = {}
    for item in raw.get("assets", []):
        asset = UniverseAsset(
            symbol=item["symbol"],
            name=item["name"],
            sector=item["sector"],
            fundamental_score=float(item["fundamental_score"]),
            binance_spot_symbol=item.get("binance_spot_symbol"),
            binance_perp_symbol=item.get("binance_perp_symbol"),
            coingecko_id=item.get("coingecko_id"),
        )
        universe[asset.symbol] = asset
    return universe


def load_strategy(path: Path) -> StrategyConfig:
    raw = _read_json(path)
    return StrategyConfig(
        starting_capital=float(raw["starting_capital"]),
        lookback_momentum=int(raw["lookback_momentum"]),
        lookback_volume=int(raw["lookback_volume"]),
        lookback_open_interest=int(raw["lookback_open_interest"]),
        top_n_long=int(raw["top_n_long"]),
        top_n_short=int(raw["top_n_short"]),
        long_threshold=float(raw["long_threshold"]),
        short_threshold=float(raw["short_threshold"]),
        enable_short=bool(raw["enable_short"]),
        max_gross_exposure=float(raw["max_gross_exposure"]),
        max_single_weight=float(raw["max_single_weight"]),
        fee_bps=float(raw["fee_bps"]),
        slippage_bps=float(raw["slippage_bps"]),
        target_annual_vol=float(raw["target_annual_vol"]),
        risk_lookback_days=int(raw["risk_lookback_days"]),
        max_daily_loss=float(raw["max_daily_loss"]),
        emergency_deleverage_ratio=float(raw["emergency_deleverage_ratio"]),
        factor_weights=dict(raw["weights"]),
    )
