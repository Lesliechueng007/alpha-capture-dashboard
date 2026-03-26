from __future__ import annotations

from typing import Dict, List, Tuple

from .factors import FactorEngine
from .models import MarketBar, StrategyConfig, UniverseAsset


def _allocate_proportional(candidates: List[Tuple[str, float]], budget: float, cap: float) -> Dict[str, float]:
    weights: Dict[str, float] = {}
    if not candidates or budget <= 0:
        return weights

    total_score = sum(abs(score) for _, score in candidates)
    if total_score <= 0:
        return {symbol: 0.0 for symbol, _ in candidates}

    for symbol, score in candidates:
        raw = budget * (abs(score) / total_score)
        weights[symbol] = min(cap, raw)

    allocated = sum(weights.values())
    if allocated <= 0:
        return weights

    # 二次归一化，确保预算分配完整且不超预算。
    scale = budget / allocated
    for symbol in list(weights):
        weights[symbol] = min(cap, weights[symbol] * scale)
    return weights


class AlphaStrategy:
    def __init__(self, cfg: StrategyConfig, universe: Dict[str, UniverseAsset]) -> None:
        self.cfg = cfg
        self.factor_engine = FactorEngine(cfg, universe)

    def generate_target_weights(
        self,
        index: int,
        history_by_symbol: Dict[str, List[MarketBar]],
    ) -> Tuple[Dict[str, float], Dict[str, str]]:
        scored = self.factor_engine.score(index, history_by_symbol)
        ranking = sorted(scored.items(), key=lambda kv: kv[1][0], reverse=True)
        symbols = list(history_by_symbol.keys())
        target = {s: 0.0 for s in symbols}
        reasons = {s: scored[s][1] for s in symbols}

        long_pool = [(s, v[0]) for s, v in ranking if v[0] >= self.cfg.long_threshold][: self.cfg.top_n_long]
        short_pool: List[Tuple[str, float]] = []
        if self.cfg.enable_short:
            short_pool = [
                (s, v[0]) for s, v in reversed(ranking) if v[0] <= -self.cfg.short_threshold
            ][: self.cfg.top_n_short]

        if self.cfg.enable_short and short_pool:
            long_budget = self.cfg.max_gross_exposure * 0.6
            short_budget = self.cfg.max_gross_exposure - long_budget
        else:
            long_budget = self.cfg.max_gross_exposure
            short_budget = 0.0

        long_alloc = _allocate_proportional(long_pool, long_budget, self.cfg.max_single_weight)
        short_alloc = _allocate_proportional(short_pool, short_budget, self.cfg.max_single_weight)

        for symbol, w in long_alloc.items():
            target[symbol] = w
        for symbol, w in short_alloc.items():
            target[symbol] = -w

        return target, reasons

