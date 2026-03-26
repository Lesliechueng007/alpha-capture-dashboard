from __future__ import annotations

from typing import Dict, Tuple

from .models import StrategyConfig


class ExecutionModel:
    def __init__(self, cfg: StrategyConfig) -> None:
        self.cfg = cfg

    def turnover_and_cost(
        self,
        prev_weights: Dict[str, float],
        target_weights: Dict[str, float],
    ) -> Tuple[float, float, float]:
        turnover = 0.0
        for symbol in target_weights:
            turnover += abs(target_weights[symbol] - prev_weights.get(symbol, 0.0))
        fee_rate = turnover * self.cfg.fee_bps / 10000.0
        slippage_rate = turnover * self.cfg.slippage_bps / 10000.0
        return turnover, fee_rate, slippage_rate

