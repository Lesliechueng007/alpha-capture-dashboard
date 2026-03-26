from __future__ import annotations

import math
from statistics import fmean, pstdev
from typing import Dict, List, Tuple

from .models import MarketBar, StrategyConfig, UniverseAsset


def _safe_pct_change(current: float, previous: float) -> float:
    if previous == 0:
        return 0.0
    return current / previous - 1.0


def _bounded_zscore(value: float, window: List[float]) -> float:
    if len(window) < 2:
        return 0.0
    mu = fmean(window)
    sigma = pstdev(window)
    if sigma == 0:
        return 0.0
    z = (value - mu) / sigma
    return max(-3.0, min(3.0, z))


class FactorEngine:
    def __init__(self, cfg: StrategyConfig, universe: Dict[str, UniverseAsset]) -> None:
        self.cfg = cfg
        self.universe = universe

    def score(
        self,
        index: int,
        history_by_symbol: Dict[str, List[MarketBar]],
    ) -> Dict[str, Tuple[float, str]]:
        out: Dict[str, Tuple[float, str]] = {}
        for symbol, series in history_by_symbol.items():
            if index <= 0 or index >= len(series):
                out[symbol] = (0.0, "insufficient_data")
                continue

            current = series[index]
            w = self.cfg.factor_weights

            mom_lb = min(self.cfg.lookback_momentum, index)
            momentum = _safe_pct_change(current.close, series[index - mom_lb].close)

            vol_lb = min(self.cfg.lookback_volume, index)
            vol_window = [b.volume for b in series[index - vol_lb : index]]
            volume_z = _bounded_zscore(current.volume, vol_window)

            oi_lb = min(self.cfg.lookback_open_interest, index)
            oi_change = _safe_pct_change(current.open_interest, series[index - oi_lb].open_interest)

            fundamental = self.universe[symbol].fundamental_score

            # 通过 tanh 做轻量归一化，避免单因子在极端值时压制其它维度。
            score = (
                w["fundamental"] * (2.0 * fundamental - 1.0)
                + w["momentum"] * math.tanh(momentum * 8.0)
                + w["volume"] * (volume_z / 3.0)
                + w["open_interest"] * math.tanh(oi_change * 5.0)
            )
            reason = (
                f"f={fundamental:.2f},mom={momentum:.3f},"
                f"vol_z={volume_z:.2f},oi={oi_change:.3f},score={score:.3f}"
            )
            out[symbol] = (score, reason)
        return out

