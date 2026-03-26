from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from alpha_capture.backtest import Backtester
from alpha_capture.config import load_strategy, load_universe
from alpha_capture.data import MarketDataFeed
from alpha_capture.reflection import generate_reflection
from alpha_capture.reporting import write_decision_log, write_markdown_report, write_trade_log


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run crypto alpha capture backtest.")
    parser.add_argument("--start", type=str, default=None, help="Start date, format YYYY-MM-DD")
    parser.add_argument("--end", type=str, default=None, help="End date, format YYYY-MM-DD")
    parser.add_argument(
        "--days",
        type=int,
        default=365,
        help="If --start not provided, use last N days ending on --end or today.",
    )
    parser.add_argument(
        "--csv",
        type=str,
        default=str(ROOT / "data" / "market_daily.csv"),
        help="CSV path for --source csv or --source auto with existing file.",
    )
    parser.add_argument(
        "--source",
        type=str,
        default="auto",
        choices=["auto", "csv", "synthetic", "binance_coingecko"],
        help="Data source: auto/csv/synthetic/binance_coingecko.",
    )
    parser.add_argument(
        "--no-fallback",
        action="store_true",
        help="Disable fallback to synthetic data when live source fails.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    universe = load_universe(ROOT / "config" / "universe.json")
    cfg = load_strategy(ROOT / "config" / "strategy.json")
    symbols = list(universe.keys())

    end = date.fromisoformat(args.end) if args.end else date.today()
    if args.start:
        start = date.fromisoformat(args.start)
    else:
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

    backtester = Backtester(cfg, universe)
    result = backtester.run(history)
    reflections = generate_reflection(result.metrics, result.symbol_contribution, cfg)

    report_path = ROOT / "reports" / "backtest_report.md"
    trade_log_path = ROOT / "reports" / "trade_log.csv"
    decision_log_path = ROOT / "reports" / "decision_log.jsonl"

    write_trade_log(trade_log_path, result)
    write_decision_log(decision_log_path, result)
    write_markdown_report(
        report_path,
        result,
        reflections,
        {
            "start": start.isoformat(),
            "end": end.isoformat(),
            "universe": ",".join(symbols),
        },
    )

    m = result.metrics
    print("Backtest done.")
    print(f"Period: {start.isoformat()} -> {end.isoformat()}")
    print(f"Total Return: {m['total_return']:.2%}")
    print(f"Annualized Return: {m['annualized_return']:.2%}")
    print(f"Sharpe: {m['sharpe']:.2f}")
    print(f"Max Drawdown: {m['max_drawdown']:.2%}")
    print(f"Data Source: {args.source}")
    print(f"Report: {report_path}")


if __name__ == "__main__":
    main()
