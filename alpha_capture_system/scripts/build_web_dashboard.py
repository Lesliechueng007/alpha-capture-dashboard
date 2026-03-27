from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]


def _to_pct(v: float | None) -> float | None:
    if v is None:
        return None
    return v * 100.0


def _to_item(raw: Dict[str, Any]) -> Dict[str, Any]:
    project = raw.get("project", {})
    metrics = raw.get("metrics", {})
    derived = raw.get("derived", {})
    return {
        "symbol": project.get("symbol"),
        "name": project.get("name"),
        "sector": project.get("sector"),
        "coingecko_id": project.get("coingecko_id"),
        "thesis": project.get("thesis", []),
        "risk_flags": project.get("risk_flags", []),
        "price_usd": metrics.get("price_usd"),
        "market_cap_usd": metrics.get("market_cap_usd"),
        "fdv_usd": metrics.get("fdv_usd"),
        "volume_24h_usd": metrics.get("volume_24h_usd"),
        "market_cap_rank": metrics.get("market_cap_rank"),
        "price_change_7d_pct": metrics.get("price_change_7d_pct"),
        "price_change_30d_pct": metrics.get("price_change_30d_pct"),
        "circulating_supply": metrics.get("circulating_supply"),
        "max_supply": metrics.get("max_supply"),
        "fdv_to_mcap": derived.get("fdv_to_mcap"),
        "volume_to_mcap_pct": _to_pct(derived.get("volume_to_mcap")),
        "circulating_ratio_pct": _to_pct(derived.get("circulating_ratio_to_max")),
        "valuation_label": derived.get("valuation_label"),
        "liquidity_label": derived.get("liquidity_label"),
        "valuation_note": derived.get("valuation_note"),
        "valuation_proxy": metrics.get("valuation_proxy"),
        "last_updated": metrics.get("last_updated"),
    }


def _safe_float(v: Any) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _calc_trade_return_pct(direction: str, entry: float | None, exit_or_mark: float | None) -> float | None:
    if entry is None or exit_or_mark is None or entry == 0:
        return None
    gross = (exit_or_mark / entry) - 1.0
    if direction.lower() == "short":
        gross = -gross
    return gross * 100.0


def _calc_review(
    journal: Dict[str, Any],
    market_by_symbol: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    entries = journal.get("entries", [])
    trades: List[Dict[str, Any]] = []

    for e in entries:
        symbol = str(e.get("symbol", "")).upper()
        benchmark_symbol = str(e.get("benchmark_symbol") or "BTC").upper()
        direction = str(e.get("direction") or "long").lower()
        thesis_tag = str(e.get("thesis_tag") or "unlabeled")

        symbol_mkt = market_by_symbol.get(symbol, {})
        bench_mkt = market_by_symbol.get(benchmark_symbol, {})

        entry_price = _safe_float(e.get("entry_price_usd"))
        exit_price = _safe_float(e.get("exit_price_usd"))
        mark_price = _safe_float(symbol_mkt.get("price_usd"))
        ref_price = exit_price if exit_price is not None else mark_price

        return_pct = _calc_trade_return_pct(direction, entry_price, ref_price)
        beta_pct = _safe_float(bench_mkt.get("price_change_30d_pct"))
        if beta_pct is None:
            beta_pct = _safe_float(symbol_mkt.get("price_change_30d_pct"))
        alpha_pct = (return_pct - beta_pct) if (return_pct is not None and beta_pct is not None) else None
        size_usd = _safe_float(e.get("size_usd"))
        pnl_usd = (size_usd * return_pct / 100.0) if (size_usd is not None and return_pct is not None) else None

        is_closed = exit_price is not None
        trades.append(
            {
                "id": e.get("id"),
                "symbol": symbol,
                "direction": direction,
                "thesis_tag": thesis_tag,
                "status": "closed" if is_closed else "open",
                "entry_date_utc": e.get("entry_date_utc"),
                "exit_date_utc": e.get("exit_date_utc"),
                "entry_price_usd": entry_price,
                "exit_price_usd": exit_price,
                "mark_price_usd": mark_price if not is_closed else None,
                "benchmark_symbol": benchmark_symbol,
                "beta_30d_pct": beta_pct,
                "return_pct": return_pct,
                "alpha_pct": alpha_pct,
                "size_usd": size_usd,
                "pnl_usd": pnl_usd,
                "notes": e.get("notes"),
            }
        )

    trades.sort(key=lambda x: (x.get("entry_date_utc") is None, x.get("entry_date_utc")), reverse=True)
    closed = [x for x in trades if x.get("status") == "closed" and x.get("return_pct") is not None]
    open_trades = [x for x in trades if x.get("status") == "open"]
    wins = [x for x in closed if (x.get("return_pct") or 0) > 0]

    def avg(items: List[Dict[str, Any]], key: str) -> float | None:
        vals = [float(x[key]) for x in items if x.get(key) is not None]
        if not vals:
            return None
        return sum(vals) / len(vals)

    tag_map: Dict[str, List[Dict[str, Any]]] = {}
    for x in closed:
        tag_map.setdefault(str(x.get("thesis_tag") or "unlabeled"), []).append(x)

    by_tag = []
    for tag, arr in sorted(tag_map.items(), key=lambda kv: len(kv[1]), reverse=True):
        tag_wins = [x for x in arr if (x.get("return_pct") or 0) > 0]
        by_tag.append(
            {
                "thesis_tag": tag,
                "count": len(arr),
                "win_rate_pct": (len(tag_wins) / len(arr) * 100.0) if arr else None,
                "avg_return_pct": avg(arr, "return_pct"),
                "avg_alpha_pct": avg(arr, "alpha_pct"),
            }
        )

    total_pnl = sum(float(x.get("pnl_usd") or 0.0) for x in trades)
    summary = {
        "total_trades": len(trades),
        "closed_trades": len(closed),
        "open_trades": len(open_trades),
        "win_rate_closed_pct": (len(wins) / len(closed) * 100.0) if closed else None,
        "avg_return_closed_pct": avg(closed, "return_pct"),
        "avg_alpha_closed_pct": avg(closed, "alpha_pct"),
        "total_pnl_usd": total_pnl,
        "beta_definition": "优先 benchmark_symbol 对应标的最近30d涨跌幅；缺失时回退为该交易标的最近30d涨跌幅",
        "alpha_definition": "trade_return_pct - beta_30d_pct（粗归因）",
    }

    return {
        "journal_updated_at_utc": journal.get("updated_at_utc"),
        "summary": summary,
        "by_tag": by_tag,
        "trades": trades[:50],
    }


def main() -> None:
    src = ROOT / "reports" / "alpha_watchlist_snapshot.json"
    journal_src = ROOT / "config" / "trade_journal.json"
    dst = ROOT / "web" / "data" / "watchlist.json"
    dst.parent.mkdir(parents=True, exist_ok=True)
    if not src.exists():
        raise FileNotFoundError(f"Missing snapshot: {src}")

    with src.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    items_raw: List[Dict[str, Any]] = payload.get("items", [])
    items = [_to_item(x) for x in items_raw]
    items.sort(key=lambda x: (x.get("market_cap_rank") is None, x.get("market_cap_rank") or 10**9))
    market_by_symbol = {
        str(x.get("symbol") or "").upper(): x
        for x in items
        if x.get("symbol")
    }

    journal: Dict[str, Any] = {"entries": []}
    if journal_src.exists():
        with journal_src.open("r", encoding="utf-8") as f:
            journal = json.load(f)
    review = _calc_review(journal, market_by_symbol)

    out = {
        "generated_at_utc": payload.get("generated_at_utc"),
        "built_at_utc": datetime.now(timezone.utc).isoformat(),
        "project_count": len(items),
        "items": items,
        "trade_review": review,
    }
    with dst.open("w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"Web data built: {dst}")


if __name__ == "__main__":
    main()
