from __future__ import annotations

import csv
import json
import random
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, Iterable, List, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .models import MarketBar
from .models import UniverseAsset


class DataSourceError(RuntimeError):
    pass


def _daterange(start: date, end: date) -> Iterable[date]:
    cur = start
    while cur <= end:
        yield cur
        cur += timedelta(days=1)


class MarketDataFeed:
    BINANCE_SPOT_BASE = "https://api.binance.com/api/v3"
    BINANCE_FUTURES_BASE = "https://fapi.binance.com/fapi/v1"
    BINANCE_FUTURES_DATA_BASE = "https://fapi.binance.com/futures/data"
    COINGECKO_BASE = "https://api.coingecko.com/api/v3"

    def __init__(self, csv_path: Path | None = None, request_timeout_sec: int = 12) -> None:
        self.csv_path = csv_path
        self.request_timeout_sec = request_timeout_sec
        self._last_coingecko_call_ts = 0.0

    def load(
        self,
        symbols: List[str],
        start: date,
        end: date,
        source: str = "auto",
        universe: Dict[str, UniverseAsset] | None = None,
        allow_fallback_to_synthetic: bool = True,
    ) -> Dict[str, List[MarketBar]]:
        if source == "auto":
            if self.csv_path and self.csv_path.exists():
                return self._load_csv(symbols, start, end)
            return self._generate_synthetic(symbols, start, end)

        if source == "csv":
            data = self._load_csv(symbols, start, end)
            if not any(data[s] for s in symbols):
                raise DataSourceError("CSV data source is empty for selected symbols/date range.")
            return data

        if source == "synthetic":
            return self._generate_synthetic(symbols, start, end)

        if source == "binance_coingecko":
            if universe is None:
                raise ValueError("universe is required for source='binance_coingecko'.")
            try:
                live = self._load_binance_coingecko(universe, start, end)
                if not any(live[s] for s in symbols):
                    raise DataSourceError("Live data fetched but empty after alignment.")
                return live
            except Exception as exc:
                if allow_fallback_to_synthetic:
                    return self._generate_synthetic(symbols, start, end)
                raise DataSourceError(f"Live data fetch failed: {exc}") from exc

        raise ValueError(f"Unsupported source: {source}")

    def _load_csv(
        self,
        symbols: List[str],
        start: date,
        end: date,
    ) -> Dict[str, List[MarketBar]]:
        records: Dict[str, List[MarketBar]] = {s: [] for s in symbols}
        with self.csv_path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                symbol = row["symbol"].upper()
                if symbol not in records:
                    continue
                dt = datetime.strptime(row["date"], "%Y-%m-%d").date()
                if dt < start or dt > end:
                    continue
                records[symbol].append(
                    MarketBar(
                        dt=dt,
                        symbol=symbol,
                        close=float(row["close"]),
                        volume=float(row["volume"]),
                        open_interest=float(row.get("open_interest", 0.0) or 0.0),
                    )
                )
        for symbol in records:
            records[symbol].sort(key=lambda x: x.dt)
        return records

    def _generate_synthetic(
        self,
        symbols: List[str],
        start: date,
        end: date,
    ) -> Dict[str, List[MarketBar]]:
        base_prices = {
            "BTC": 40000.0,
            "ETH": 2200.0,
            "SOL": 80.0,
            "BASE": 1.5,
            "DRIV": 2.2,
            "AIA": 1.0,
        }
        drift_map = {
            "BTC": 0.0006,
            "ETH": 0.0008,
            "SOL": 0.0010,
            "BASE": 0.0011,
            "DRIV": 0.0009,
            "AIA": 0.0012,
        }
        vol_map = {
            "BTC": 0.025,
            "ETH": 0.03,
            "SOL": 0.045,
            "BASE": 0.055,
            "DRIV": 0.05,
            "AIA": 0.06,
        }
        records: Dict[str, List[MarketBar]] = {s: [] for s in symbols}
        for symbol in symbols:
            stable_seed = sum(ord(ch) for ch in symbol) + 1024
            rng = random.Random(stable_seed)
            price = base_prices.get(symbol, 10.0)
            volume = 1_000_000.0 * (1.0 + rng.random())
            oi = 250_000.0 * (1.0 + rng.random())
            for dt in _daterange(start, end):
                cyclical = 0.003 * (1 if dt.day % 14 < 7 else -1)
                daily_ret = rng.gauss(drift_map.get(symbol, 0.0008) + cyclical, vol_map.get(symbol, 0.04))
                price = max(0.05, price * (1.0 + daily_ret))
                volume = max(10_000.0, volume * (1.0 + rng.gauss(0.0005, 0.09)))
                oi = max(10_000.0, oi * (1.0 + rng.gauss(0.0003, 0.06)))
                records[symbol].append(
                    MarketBar(
                        dt=dt,
                        symbol=symbol,
                        close=price,
                        volume=volume,
                        open_interest=oi,
                    )
                )
        return records

    def _load_binance_coingecko(
        self,
        universe: Dict[str, UniverseAsset],
        start: date,
        end: date,
    ) -> Dict[str, List[MarketBar]]:
        symbols = list(universe.keys())
        records: Dict[str, List[MarketBar]] = {s: [] for s in symbols}
        dt_index = list(_daterange(start, end))

        for symbol in symbols:
            asset = universe[symbol]

            cg_price, cg_volume, cg_mcap = ({}, {}, {})
            if asset.coingecko_id:
                try:
                    cg_price, cg_volume, cg_mcap = self._fetch_coingecko_daily(asset.coingecko_id, start, end)
                except Exception:
                    cg_price, cg_volume, cg_mcap = ({}, {}, {})

            bn_close, bn_volume = ({}, {})
            if asset.binance_spot_symbol:
                try:
                    bn_close, bn_volume = self._fetch_binance_klines_daily(asset.binance_spot_symbol, start, end)
                except Exception:
                    bn_close, bn_volume = ({}, {})

            oi_map: Dict[date, float] = {}
            if asset.binance_perp_symbol:
                try:
                    oi_map = self._fetch_binance_open_interest_daily(asset.binance_perp_symbol, start, end)
                except Exception:
                    oi_map = {}

            last_close = None
            last_volume = None
            last_oi = None
            for dt in dt_index:
                close = bn_close.get(dt, cg_price.get(dt))
                volume = bn_volume.get(dt, cg_volume.get(dt))
                open_interest = oi_map.get(dt)

                if close is None:
                    close = last_close if last_close is not None else 1.0
                if volume is None:
                    volume = last_volume if last_volume is not None else max(10_000.0, close * 2000.0)
                if open_interest is None:
                    if dt in cg_mcap:
                        open_interest = max(10_000.0, cg_mcap[dt] * 0.02)
                    elif last_oi is not None:
                        open_interest = last_oi
                    else:
                        open_interest = max(10_000.0, volume * 0.15)

                records[symbol].append(
                    MarketBar(
                        dt=dt,
                        symbol=symbol,
                        close=float(close),
                        volume=float(volume),
                        open_interest=float(open_interest),
                    )
                )
                last_close = float(close)
                last_volume = float(volume)
                last_oi = float(open_interest)
        return records

    def _fetch_json(self, base_url: str, params: Dict[str, str | int | float]) -> dict | list:
        if "api.coingecko.com" in base_url:
            min_interval = 1.3
            elapsed = time.time() - self._last_coingecko_call_ts
            if elapsed < min_interval:
                time.sleep(min_interval - elapsed)

        query = urlencode(params)
        url = f"{base_url}?{query}" if query else base_url
        retries = 4
        for attempt in range(retries):
            req = Request(
                url=url,
                headers={
                    "Accept": "application/json",
                    "User-Agent": "alpha-capture-system/1.0",
                },
                method="GET",
            )
            try:
                with urlopen(req, timeout=self.request_timeout_sec) as resp:
                    raw = resp.read().decode("utf-8")
                if "api.coingecko.com" in base_url:
                    self._last_coingecko_call_ts = time.time()
                return json.loads(raw)
            except HTTPError as exc:
                if exc.code in (429, 500, 502, 503, 504) and attempt < retries - 1:
                    retry_after = exc.headers.get("Retry-After")
                    sleep_sec = float(retry_after) if retry_after else (1.5 * (2**attempt))
                    time.sleep(sleep_sec)
                    continue
                raise
            except URLError:
                if attempt < retries - 1:
                    time.sleep(1.2 * (2**attempt))
                    continue
                raise
        raise DataSourceError(f"Request failed after retries: {url}")

    def _fetch_binance_klines_daily(
        self,
        binance_symbol: str,
        start: date,
        end: date,
    ) -> Tuple[Dict[date, float], Dict[date, float]]:
        close_map: Dict[date, float] = {}
        volume_map: Dict[date, float] = {}

        start_ms = int(datetime.combine(start, datetime.min.time()).timestamp() * 1000)
        end_ms = int(datetime.combine(end + timedelta(days=1), datetime.min.time()).timestamp() * 1000) - 1
        cur_ms = start_ms
        one_day_ms = 24 * 60 * 60 * 1000

        while cur_ms <= end_ms:
            data = self._fetch_json(
                f"{self.BINANCE_SPOT_BASE}/klines",
                {
                    "symbol": binance_symbol,
                    "interval": "1d",
                    "startTime": cur_ms,
                    "endTime": end_ms,
                    "limit": 1000,
                },
            )
            if not isinstance(data, list) or not data:
                break
            last_open_time = None
            for row in data:
                open_time = int(row[0])
                dt = datetime.utcfromtimestamp(open_time / 1000).date()
                close_map[dt] = float(row[4])
                volume_map[dt] = float(row[5])
                last_open_time = open_time
            if last_open_time is None:
                break
            next_ms = last_open_time + one_day_ms
            if next_ms <= cur_ms:
                break
            cur_ms = next_ms
        return close_map, volume_map

    def _fetch_binance_open_interest_daily(
        self,
        perp_symbol: str,
        start: date,
        end: date,
    ) -> Dict[date, float]:
        oi_map: Dict[date, float] = {}
        start_ms = int(datetime.combine(start, datetime.min.time()).timestamp() * 1000)
        end_ms = int(datetime.combine(end + timedelta(days=1), datetime.min.time()).timestamp() * 1000) - 1
        cur_ms = start_ms
        one_day_ms = 24 * 60 * 60 * 1000

        while cur_ms <= end_ms:
            data = self._fetch_json(
                f"{self.BINANCE_FUTURES_DATA_BASE}/openInterestHist",
                {
                    "symbol": perp_symbol,
                    "period": "1d",
                    "startTime": cur_ms,
                    "endTime": end_ms,
                    "limit": 500,
                },
            )
            if not isinstance(data, list) or not data:
                break
            last_ts = None
            for row in data:
                ts = int(row["timestamp"])
                dt = datetime.utcfromtimestamp(ts / 1000).date()
                oi_map[dt] = float(row["sumOpenInterest"])
                last_ts = ts
            if last_ts is None:
                break
            next_ms = last_ts + one_day_ms
            if next_ms <= cur_ms:
                break
            cur_ms = next_ms
        return oi_map

    def _fetch_coingecko_daily(
        self,
        coingecko_id: str,
        start: date,
        end: date,
    ) -> Tuple[Dict[date, float], Dict[date, float], Dict[date, float]]:
        from_ts = int(datetime.combine(start, datetime.min.time()).timestamp())
        to_ts = int(datetime.combine(end + timedelta(days=1), datetime.min.time()).timestamp()) - 1
        data = self._fetch_json(
            f"{self.COINGECKO_BASE}/coins/{coingecko_id}/market_chart/range",
            {
                "vs_currency": "usd",
                "from": from_ts,
                "to": to_ts,
            },
        )
        if not isinstance(data, dict):
            raise DataSourceError(f"Unexpected CoinGecko response for {coingecko_id}")

        prices = data.get("prices", [])
        total_volumes = data.get("total_volumes", [])
        market_caps = data.get("market_caps", [])

        price_map = self._fold_timeseries_daily(prices)
        volume_map = self._fold_timeseries_daily(total_volumes)
        mcap_map = self._fold_timeseries_daily(market_caps)
        return price_map, volume_map, mcap_map

    def _fold_timeseries_daily(self, rows: List[List[float]]) -> Dict[date, float]:
        out: Dict[date, float] = {}
        for row in rows:
            if not isinstance(row, list) or len(row) < 2:
                continue
            ts = float(row[0]) / 1000.0
            dt = datetime.utcfromtimestamp(ts).date()
            out[dt] = float(row[1])
        return out
