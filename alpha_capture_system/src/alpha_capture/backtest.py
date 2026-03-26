from __future__ import annotations

import math
from statistics import fmean, pstdev
from typing import Dict, List

from .execution import ExecutionModel
from .models import BacktestResult, DailyRecord, MarketBar, StrategyConfig, TradeRecord, UniverseAsset
from .risk import RiskManager
from .strategy import AlphaStrategy


def _compute_max_drawdown(equity_curve: List[float]) -> float:
    if not equity_curve:
        return 0.0
    peak = equity_curve[0]
    max_dd = 0.0
    for value in equity_curve:
        peak = max(peak, value)
        if peak > 0:
            dd = 1.0 - value / peak
            max_dd = max(max_dd, dd)
    return max_dd


class Backtester:
    def __init__(self, cfg: StrategyConfig, universe: Dict[str, UniverseAsset]) -> None:
        self.cfg = cfg
        self.strategy = AlphaStrategy(cfg, universe)
        self.risk = RiskManager(cfg)
        self.execution = ExecutionModel(cfg)
        self.universe = universe

    def run(self, history_by_symbol: Dict[str, List[MarketBar]]) -> BacktestResult:
        symbols = list(history_by_symbol.keys())
        if not symbols:
            raise ValueError("No symbols in history.")
        length = min(len(v) for v in history_by_symbol.values())
        if length < 3:
            raise ValueError("Insufficient history length for backtest.")

        equity = self.cfg.starting_capital
        prev_weights = {s: 0.0 for s in symbols}
        recent_returns: List[float] = []
        equity_curve = [equity]

        daily_records: List[DailyRecord] = []
        trade_records: List[TradeRecord] = []
        symbol_contribution = {s: 0.0 for s in symbols}

        for idx in range(1, length):
            dt = history_by_symbol[symbols[0]][idx].dt
            gross_return = 0.0
            for symbol in symbols:
                prev_price = history_by_symbol[symbol][idx - 1].close
                cur_price = history_by_symbol[symbol][idx].close
                r = 0.0 if prev_price == 0 else (cur_price / prev_price - 1.0)
                gross_return += prev_weights[symbol] * r
                symbol_contribution[symbol] += prev_weights[symbol] * r

            proposed_weights, reasons = self.strategy.generate_target_weights(idx, history_by_symbol)
            adjusted_weights, realized_vol, risk_note = self.risk.apply(proposed_weights, recent_returns)
            turnover, fee_rate, slippage_rate = self.execution.turnover_and_cost(prev_weights, adjusted_weights)
            cost_rate = fee_rate + slippage_rate
            net_return = gross_return - cost_rate

            prev_equity = equity
            equity = equity * (1.0 + net_return)
            equity_curve.append(equity)
            recent_returns.append(net_return)

            for symbol in symbols:
                from_w = prev_weights.get(symbol, 0.0)
                to_w = adjusted_weights.get(symbol, 0.0)
                diff = to_w - from_w
                if abs(diff) > 1e-8:
                    bar = history_by_symbol[symbol][idx]
                    trade_records.append(
                        TradeRecord(
                            dt=dt,
                            symbol=symbol,
                            from_weight=from_w,
                            to_weight=to_w,
                            price=bar.close,
                            turnover_weight=abs(diff),
                            fee_cost_rate=abs(diff) * self.cfg.fee_bps / 10000.0,
                            slippage_cost_rate=abs(diff) * self.cfg.slippage_bps / 10000.0,
                            reason=reasons.get(symbol, ""),
                        )
                    )

            daily_records.append(
                DailyRecord(
                    dt=dt,
                    equity=equity,
                    gross_return=gross_return,
                    cost_rate=cost_rate,
                    net_return=net_return,
                    turnover=turnover,
                    realized_vol_annualized=realized_vol,
                    risk_note=risk_note,
                    weights=dict(adjusted_weights),
                    decision_reason=reasons,
                )
            )
            prev_weights = adjusted_weights

            if equity <= prev_equity * 0.2:
                break

        metrics = self._metrics(recent_returns, equity_curve)
        return BacktestResult(
            daily_records=daily_records,
            trade_records=trade_records,
            metrics=metrics,
            symbol_contribution=symbol_contribution,
        )

    def _metrics(self, returns: List[float], equity_curve: List[float]) -> Dict[str, float]:
        if not returns:
            return {
                "total_return": 0.0,
                "annualized_return": 0.0,
                "annualized_vol": 0.0,
                "sharpe": 0.0,
                "max_drawdown": 0.0,
                "win_rate": 0.0,
            }
        total_return = equity_curve[-1] / equity_curve[0] - 1.0
        days = len(returns)
        annualized_return = math.pow(1.0 + total_return, 365.0 / days) - 1.0 if total_return > -1 else -1.0
        annualized_vol = pstdev(returns) * math.sqrt(365.0) if len(returns) > 1 else 0.0
        sharpe = annualized_return / annualized_vol if annualized_vol > 0 else 0.0
        max_drawdown = _compute_max_drawdown(equity_curve)
        win_rate = sum(1 for r in returns if r > 0) / len(returns)
        return {
            "total_return": total_return,
            "annualized_return": annualized_return,
            "annualized_vol": annualized_vol,
            "sharpe": sharpe,
            "max_drawdown": max_drawdown,
            "win_rate": win_rate,
            "avg_daily_return": fmean(returns),
        }

