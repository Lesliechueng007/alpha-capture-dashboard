from __future__ import annotations

from typing import Dict, List

from .models import StrategyConfig


def generate_reflection(
    metrics: Dict[str, float],
    symbol_contribution: Dict[str, float],
    cfg: StrategyConfig,
) -> List[str]:
    notes: List[str] = []
    sharpe = metrics.get("sharpe", 0.0)
    max_dd = metrics.get("max_drawdown", 0.0)
    annual_vol = metrics.get("annualized_vol", 0.0)
    win_rate = metrics.get("win_rate", 0.0)

    if sharpe < 0.8:
        notes.append(
            "Sharpe 偏低，建议先做 regime 分层（趋势/震荡）并在震荡阶段降低动量因子权重。"
        )
    else:
        notes.append("Sharpe 达到可用水平，可以继续做参数稳定性与跨区间检验。")

    if max_dd > 0.25:
        notes.append("最大回撤较高，建议收紧单资产权重上限并提高紧急去杠杆比例。")
    else:
        notes.append("回撤控制尚可，可在不突破风险预算前提下尝试提升收益效率。")

    if annual_vol > cfg.target_annual_vol * 1.1:
        notes.append("组合波动率高于目标，建议提高风控缩放强度或延长风险观察窗口。")
    if win_rate < 0.45:
        notes.append("胜率偏低，建议加入资金费率/基差过滤器减少逆势交易。")

    sorted_contrib = sorted(symbol_contribution.items(), key=lambda kv: kv[1], reverse=True)
    best = sorted_contrib[0] if sorted_contrib else ("N/A", 0.0)
    worst = sorted_contrib[-1] if sorted_contrib else ("N/A", 0.0)
    notes.append(
        f"本轮贡献最高资产: {best[0]} ({best[1]:.3f})；最低资产: {worst[0]} ({worst[1]:.3f})。"
    )
    notes.append("下一轮迭代建议：优先替换弱贡献资产的信号触发条件，再做全局再优化。")
    return notes

