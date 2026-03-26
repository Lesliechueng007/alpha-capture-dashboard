from __future__ import annotations

import csv
import json
import sys
import argparse
from dataclasses import replace
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, Iterable, List

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from alpha_capture.backtest import Backtester
from alpha_capture.config import load_strategy, load_universe
from alpha_capture.data import MarketDataFeed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Grid-search strategy parameters.")
    parser.add_argument(
        "--source",
        type=str,
        default="auto",
        choices=["auto", "csv", "synthetic", "binance_coingecko"],
        help="Data source used for optimization.",
    )
    parser.add_argument(
        "--csv",
        type=str,
        default=str(ROOT / "data" / "market_daily.csv"),
        help="CSV path for --source csv or auto mode.",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=365,
        help="Lookback days for optimization dataset.",
    )
    parser.add_argument(
        "--no-fallback",
        action="store_true",
        help="Disable fallback to synthetic data when live source fails.",
    )
    return parser.parse_args()


def _grid() -> Iterable[Dict[str, float]]:
    long_thresholds = [0.03, 0.04, 0.05]
    short_thresholds = [0.06, 0.07, 0.08]
    max_single_weights = [0.2, 0.25, 0.3]
    top_n_longs = [2, 3, 4]
    target_vols = [0.25, 0.3, 0.35]
    for lt in long_thresholds:
        for st in short_thresholds:
            for max_w in max_single_weights:
                for n_long in top_n_longs:
                    for tv in target_vols:
                        yield {
                            "long_threshold": lt,
                            "short_threshold": st,
                            "max_single_weight": max_w,
                            "top_n_long": n_long,
                            "target_annual_vol": tv,
                        }


def _objective(metrics: Dict[str, float]) -> float:
    sharpe = metrics.get("sharpe", 0.0)
    annual_return = metrics.get("annualized_return", 0.0)
    max_dd = metrics.get("max_drawdown", 1.0)
    dd_penalty = max(0.0, max_dd - 0.25) * 3.0
    return sharpe + 0.3 * annual_return - dd_penalty


def main() -> None:
    args = parse_args()
    universe = load_universe(ROOT / "config" / "universe.json")
    base_cfg = load_strategy(ROOT / "config" / "strategy.json")
    symbols = list(universe.keys())

    end = date.today()
    start = end - timedelta(days=max(30, args.days))
    feed = MarketDataFeed(csv_path=Path(args.csv))
    history = feed.load(
        symbols=symbols,
        start=start,
        end=end,
        source=args.source,
        universe=universe,
        allow_fallback_to_synthetic=not args.no_fallback,
    )

    rows: List[Dict[str, float]] = []
    best = None
    best_score = -10**9

    for params in _grid():
        cfg = replace(
            base_cfg,
            long_threshold=params["long_threshold"],
            short_threshold=params["short_threshold"],
            max_single_weight=params["max_single_weight"],
            top_n_long=int(params["top_n_long"]),
            target_annual_vol=params["target_annual_vol"],
        )
        result = Backtester(cfg, universe).run(history)
        obj = _objective(result.metrics)
        row = {
            **params,
            "objective": obj,
            "annualized_return": result.metrics["annualized_return"],
            "sharpe": result.metrics["sharpe"],
            "max_drawdown": result.metrics["max_drawdown"],
            "win_rate": result.metrics["win_rate"],
        }
        rows.append(row)
        if obj > best_score:
            best_score = obj
            best = row

    out_csv = ROOT / "reports" / "optimization_results.csv"
    out_json = ROOT / "reports" / "best_params.json"
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "long_threshold",
                "short_threshold",
                "max_single_weight",
                "top_n_long",
                "target_annual_vol",
                "objective",
                "annualized_return",
                "sharpe",
                "max_drawdown",
                "win_rate",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    with out_json.open("w", encoding="utf-8") as f:
        json.dump(best, f, ensure_ascii=False, indent=2)

    print(f"Optimization completed. Total trials: {len(rows)}")
    print(f"Best objective: {best_score:.4f}")
    print(f"Data source: {args.source}")
    print(f"Best params file: {out_json}")
    print(f"All trials file: {out_csv}")


if __name__ == "__main__":
    main()
