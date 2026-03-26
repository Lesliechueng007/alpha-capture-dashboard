from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Dict, List

from .models import BacktestResult


def write_trade_log(path: Path, result: BacktestResult) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "date",
                "symbol",
                "from_weight",
                "to_weight",
                "price",
                "turnover_weight",
                "fee_cost_rate",
                "slippage_cost_rate",
                "reason",
            ]
        )
        for tr in result.trade_records:
            writer.writerow(
                [
                    tr.dt.isoformat(),
                    tr.symbol,
                    f"{tr.from_weight:.6f}",
                    f"{tr.to_weight:.6f}",
                    f"{tr.price:.6f}",
                    f"{tr.turnover_weight:.6f}",
                    f"{tr.fee_cost_rate:.6f}",
                    f"{tr.slippage_cost_rate:.6f}",
                    tr.reason,
                ]
            )


def write_decision_log(path: Path, result: BacktestResult) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for dr in result.daily_records:
            payload = {
                "date": dr.dt.isoformat(),
                "equity": dr.equity,
                "gross_return": dr.gross_return,
                "cost_rate": dr.cost_rate,
                "net_return": dr.net_return,
                "turnover": dr.turnover,
                "realized_vol_annualized": dr.realized_vol_annualized,
                "risk_note": dr.risk_note,
                "weights": dr.weights,
                "decision_reason": dr.decision_reason,
            }
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def write_markdown_report(
    path: Path,
    result: BacktestResult,
    reflections: List[str],
    meta: Dict[str, str],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    m = result.metrics
    top = sorted(result.symbol_contribution.items(), key=lambda kv: kv[1], reverse=True)
    top_lines = [
        f"- {symbol}: {value:.4f}"
        for symbol, value in top
    ]
    content = f"""# Alpha Strategy Backtest Report

## Meta

- Start: {meta["start"]}
- End: {meta["end"]}
- Universe: {meta["universe"]}

## Metrics

- Total Return: {m["total_return"]:.2%}
- Annualized Return: {m["annualized_return"]:.2%}
- Annualized Vol: {m["annualized_vol"]:.2%}
- Sharpe: {m["sharpe"]:.2f}
- Max Drawdown: {m["max_drawdown"]:.2%}
- Win Rate: {m["win_rate"]:.2%}

## Symbol Contribution (Return-Rate Approx)

{chr(10).join(top_lines)}

## Reflection

{chr(10).join(f"- {line}" for line in reflections)}
"""
    with path.open("w", encoding="utf-8") as f:
        f.write(content)

