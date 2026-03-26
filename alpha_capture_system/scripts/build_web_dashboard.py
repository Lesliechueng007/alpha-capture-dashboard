from __future__ import annotations

import json
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
        "last_updated": metrics.get("last_updated"),
    }


def main() -> None:
    src = ROOT / "reports" / "alpha_watchlist_snapshot.json"
    dst = ROOT / "web" / "data" / "watchlist.json"
    dst.parent.mkdir(parents=True, exist_ok=True)
    if not src.exists():
        raise FileNotFoundError(f"Missing snapshot: {src}")

    with src.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    items_raw: List[Dict[str, Any]] = payload.get("items", [])
    items = [_to_item(x) for x in items_raw]
    items.sort(key=lambda x: (x.get("market_cap_rank") is None, x.get("market_cap_rank") or 10**9))

    out = {
        "generated_at_utc": payload.get("generated_at_utc"),
        "project_count": len(items),
        "items": items,
    }
    with dst.open("w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"Web data built: {dst}")


if __name__ == "__main__":
    main()

