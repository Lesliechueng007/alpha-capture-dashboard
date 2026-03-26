from __future__ import annotations

import math
from statistics import pstdev
from typing import Dict, List, Tuple

from .models import StrategyConfig


class RiskManager:
    def __init__(self, cfg: StrategyConfig) -> None:
        self.cfg = cfg

    def apply(
        self,
        proposed_weights: Dict[str, float],
        recent_portfolio_returns: List[float],
    ) -> Tuple[Dict[str, float], float, str]:
        out = dict(proposed_weights)
        note_parts: List[str] = []
        realized_vol = 0.0

        lookback = self.cfg.risk_lookback_days
        window = recent_portfolio_returns[-lookback:] if lookback > 0 else recent_portfolio_returns
        if len(window) >= 2:
            daily_vol = pstdev(window)
            realized_vol = daily_vol * math.sqrt(365.0)
            if realized_vol > 0 and realized_vol > self.cfg.target_annual_vol:
                scale = self.cfg.target_annual_vol / realized_vol
                out = {s: w * scale for s, w in out.items()}
                note_parts.append(f"vol_target_scale={scale:.2f}")

        if recent_portfolio_returns:
            last_ret = recent_portfolio_returns[-1]
            if last_ret <= -self.cfg.max_daily_loss:
                ratio = self.cfg.emergency_deleverage_ratio
                out = {s: w * ratio for s, w in out.items()}
                note_parts.append(f"emergency_deleverage={ratio:.2f}")

        note = ",".join(note_parts) if note_parts else "normal"
        return out, realized_vol, note

