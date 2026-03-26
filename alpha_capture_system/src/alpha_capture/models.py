from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Dict, List


@dataclass
class UniverseAsset:
    symbol: str
    name: str
    sector: str
    fundamental_score: float
    binance_spot_symbol: str | None = None
    binance_perp_symbol: str | None = None
    coingecko_id: str | None = None


@dataclass
class StrategyConfig:
    starting_capital: float
    lookback_momentum: int
    lookback_volume: int
    lookback_open_interest: int
    top_n_long: int
    top_n_short: int
    long_threshold: float
    short_threshold: float
    enable_short: bool
    max_gross_exposure: float
    max_single_weight: float
    fee_bps: float
    slippage_bps: float
    target_annual_vol: float
    risk_lookback_days: int
    max_daily_loss: float
    emergency_deleverage_ratio: float
    factor_weights: Dict[str, float]


@dataclass
class MarketBar:
    dt: date
    symbol: str
    close: float
    volume: float
    open_interest: float


@dataclass
class TradeRecord:
    dt: date
    symbol: str
    from_weight: float
    to_weight: float
    price: float
    turnover_weight: float
    fee_cost_rate: float
    slippage_cost_rate: float
    reason: str


@dataclass
class DailyRecord:
    dt: date
    equity: float
    gross_return: float
    cost_rate: float
    net_return: float
    turnover: float
    realized_vol_annualized: float
    risk_note: str
    weights: Dict[str, float] = field(default_factory=dict)
    decision_reason: Dict[str, str] = field(default_factory=dict)


@dataclass
class BacktestResult:
    daily_records: List[DailyRecord]
    trade_records: List[TradeRecord]
    metrics: Dict[str, float]
    symbol_contribution: Dict[str, float]
