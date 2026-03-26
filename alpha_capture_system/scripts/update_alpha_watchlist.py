from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Update alpha watchlist snapshot from CoinGecko.")
    parser.add_argument("--symbol", type=str, default=None, help="Only update one symbol, e.g. HYPE")
    parser.add_argument(
        "--config",
        type=str,
        default=str(ROOT / "config" / "alpha_watchlist.json"),
        help="Watchlist config path.",
    )
    parser.add_argument(
        "--out-md",
        type=str,
        default=str(ROOT / "reports" / "alpha_watchlist_latest.md"),
        help="Output markdown path.",
    )
    parser.add_argument(
        "--out-json",
        type=str,
        default=str(ROOT / "reports" / "alpha_watchlist_snapshot.json"),
        help="Output JSON snapshot path.",
    )
    return parser.parse_args()


def http_get_json(base_url: str, params: Dict[str, Any], timeout: int = 12) -> Any:
    query = urlencode(params)
    url = f"{base_url}?{query}" if query else base_url
    retries = 4
    for attempt in range(retries):
        req = Request(
            url=url,
            headers={
                "Accept": "application/json",
                "User-Agent": "alpha-watchlist-updater/1.0",
            },
            method="GET",
        )
        try:
            with urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except HTTPError as exc:
            if exc.code in (429, 500, 502, 503, 504) and attempt < retries - 1:
                retry_after = exc.headers.get("Retry-After")
                sleep_sec = float(retry_after) if retry_after else (1.6 * (2**attempt))
                time.sleep(sleep_sec)
                continue
            raise
        except URLError:
            if attempt < retries - 1:
                time.sleep(1.2 * (2**attempt))
                continue
            raise
    raise RuntimeError(f"Request failed after retries: {url}")


def fetch_coingecko_metrics(coingecko_id: str) -> Dict[str, Any]:
    base = "https://api.coingecko.com/api/v3"
    coin = http_get_json(
        f"{base}/coins/{coingecko_id}",
        {
            "localization": "false",
            "tickers": "false",
            "market_data": "true",
            "community_data": "false",
            "developer_data": "false",
            "sparkline": "false",
        },
    )
    chart = http_get_json(
        f"{base}/coins/{coingecko_id}/market_chart",
        {
            "vs_currency": "usd",
            "days": "30",
            "interval": "daily",
        },
    )

    md = coin.get("market_data", {})
    current_price = (md.get("current_price") or {}).get("usd")
    market_cap = (md.get("market_cap") or {}).get("usd")
    fdv = (md.get("fully_diluted_valuation") or {}).get("usd")
    volume_24h = (md.get("total_volume") or {}).get("usd")
    circulating = md.get("circulating_supply")
    total_supply = md.get("total_supply")
    max_supply = md.get("max_supply")
    rank = coin.get("market_cap_rank")

    prices = chart.get("prices", [])
    ret_30d = None
    if len(prices) >= 2:
        start_price = float(prices[0][1])
        end_price = float(prices[-1][1])
        if start_price > 0:
            ret_30d = end_price / start_price - 1.0

    return {
        "coingecko_id": coingecko_id,
        "name": coin.get("name"),
        "symbol": str(coin.get("symbol", "")).upper(),
        "market_cap_rank": rank,
        "price_usd": current_price,
        "market_cap_usd": market_cap,
        "fdv_usd": fdv,
        "volume_24h_usd": volume_24h,
        "circulating_supply": circulating,
        "total_supply": total_supply,
        "max_supply": max_supply,
        "price_change_7d_pct": md.get("price_change_percentage_7d"),
        "price_change_30d_pct": md.get("price_change_percentage_30d"),
        "return_30d_from_chart": ret_30d,
        "ath_change_pct": md.get("ath_change_percentage", {}).get("usd"),
        "last_updated": coin.get("last_updated"),
    }


def as_money(v: float | None) -> str:
    if v is None:
        return "N/A"
    if v >= 1_000_000_000:
        return f"${v / 1_000_000_000:.2f}B"
    if v >= 1_000_000:
        return f"${v / 1_000_000:.2f}M"
    return f"${v:,.0f}"


def as_price(v: float | None) -> str:
    if v is None:
        return "N/A"
    return f"${v:,.4f}" if v < 1 else f"${v:,.2f}"


def as_pct(v: float | None) -> str:
    if v is None:
        return "N/A"
    return f"{v * 100:.2f}%"


def as_pct_from_percent(v: float | None) -> str:
    if v is None:
        return "N/A"
    return f"{v:.2f}%"


def as_ratio(v: float | None) -> str:
    if v is None:
        return "N/A"
    return f"{v:.2f}"


def valuation_label(fdv_to_mcap: float | None, warn: float, rich: float) -> str:
    if fdv_to_mcap is None:
        return "N/A"
    if fdv_to_mcap >= rich:
        return "RICH"
    if fdv_to_mcap >= warn:
        return "WARN"
    return "OK"


def liquidity_label(vol_to_mcap: float | None, low: float, high: float) -> str:
    if vol_to_mcap is None:
        return "N/A"
    if vol_to_mcap < low:
        return "LOW"
    if vol_to_mcap > high:
        return "HOT"
    return "NORMAL"


def main() -> None:
    args = parse_args()
    config_path = Path(args.config)
    out_md = Path(args.out_md)
    out_json = Path(args.out_json)

    with config_path.open("r", encoding="utf-8") as f:
        watchlist = json.load(f)["projects"]
    if args.symbol:
        symbol = args.symbol.upper()
        watchlist = [p for p in watchlist if p["symbol"].upper() == symbol]
        if not watchlist:
            raise ValueError(f"Symbol {symbol} not found in watchlist config.")

    snapshot_items: List[Dict[str, Any]] = []
    md_sections: List[str] = []
    run_ts = datetime.now(timezone.utc).isoformat()

    for project in watchlist:
        metrics = fetch_coingecko_metrics(project["coingecko_id"])
        market_cap = metrics.get("market_cap_usd")
        fdv = metrics.get("fdv_usd")
        vol_24h = metrics.get("volume_24h_usd")
        fdv_to_mcap = (fdv / market_cap) if market_cap and fdv else None
        vol_to_mcap = (vol_24h / market_cap) if market_cap and vol_24h else None
        circulating = metrics.get("circulating_supply")
        max_supply = metrics.get("max_supply")
        circ_ratio = (circulating / max_supply) if circulating and max_supply else None

        threshold = project["kpi_thresholds"]
        v_label = valuation_label(
            fdv_to_mcap,
            warn=float(threshold["fdv_to_mcap_warn"]),
            rich=float(threshold["fdv_to_mcap_rich"]),
        )
        l_label = liquidity_label(
            vol_to_mcap,
            low=float(threshold["volume_to_mcap_low"]),
            high=float(threshold["volume_to_mcap_high"]),
        )

        snapshot = {
            "run_ts_utc": run_ts,
            "project": project,
            "metrics": metrics,
            "derived": {
                "fdv_to_mcap": fdv_to_mcap,
                "volume_to_mcap": vol_to_mcap,
                "circulating_ratio_to_max": circ_ratio,
                "valuation_label": v_label,
                "liquidity_label": l_label,
            },
        }
        snapshot_items.append(snapshot)

        thesis_lines = "\n".join(f"- {t}" for t in project["thesis"])
        risk_lines = "\n".join(f"- {r}" for r in project["risk_flags"])
        md_sections.append(
            f"""## {project['name']} ({project['symbol']})

- Sector: {project['sector']}
- CoinGecko ID: {project['coingecko_id']}
- Price: {as_price(metrics.get('price_usd'))}
- Market Cap: {as_money(market_cap)}
- FDV: {as_money(fdv)}
- FDV/MCAP: {as_ratio(fdv_to_mcap)} ({v_label})""" + f"""
- 24h Volume: {as_money(vol_24h)}
- 24h Volume/MCAP: {as_pct(vol_to_mcap)} ({l_label})
- 7d Price Change: {as_pct_from_percent(metrics.get('price_change_7d_pct'))}
- 30d Price Change: {as_pct_from_percent(metrics.get('price_change_30d_pct'))}
- Circulating / Max Supply: {as_pct(circ_ratio)}
- CoinGecko Market Cap Rank: {metrics.get('market_cap_rank', 'N/A')}

### Alpha Thesis
{thesis_lines}

### Risk Flags
{risk_lines}
"""
        )

    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)

    md_content = (
        "# Alpha Watchlist Snapshot\n\n"
        f"- Generated at (UTC): {run_ts}\n\n"
        + "\n".join(md_sections)
    )
    with out_md.open("w", encoding="utf-8") as f:
        f.write(md_content)
    with out_json.open("w", encoding="utf-8") as f:
        json.dump({"generated_at_utc": run_ts, "items": snapshot_items}, f, ensure_ascii=False, indent=2)

    print("Alpha watchlist updated.")
    print(f"Markdown: {out_md}")
    print(f"Snapshot JSON: {out_json}")


if __name__ == "__main__":
    main()
