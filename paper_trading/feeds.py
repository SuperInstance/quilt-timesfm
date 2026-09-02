"""Real-world price data feeds for the paper trader.

Three real sources, in order of complexity:

  - CSVPriceFeed: read prices from a CSV file (e.g. AAPL.csv from
    Yahoo Finance, Kaggle, or any market-data export). No network
    needed; this is the simplest "real" data path.
  - YahooFinanceFeed: download prices from Yahoo Finance on the fly
    using only the standard library (no `yfinance` dependency).
    Works for daily, weekly, and monthly intervals.
  - RandomWalkFeed: a deterministic-but-noisy stream for unit tests.
    Same shape as a real feed (timestamp + price) but the data is
    freshly generated.

All feeds yield (timestamp_ms, price) tuples with the same
contract as `synthetic_price_stream`. The PaperTrader doesn't
care which feed it's reading from.

Why CSV is the most useful "real" data path:
  - Yahoo Finance CSV exports are available for free
  - Kaggle has thousands of historical price datasets
  - CRSP, Compustat, and other academic datasets ship as CSV
  - A user can drop a CSV into the repo, point PaperTrader at it,
    and replay real history
"""
from __future__ import annotations
import csv
import os
import time
import urllib.request
import urllib.parse
import datetime
import numpy as np
from typing import Iterator, Tuple, Optional, List


# ─── CSV ───────────────────────────────────────────────────────────

class CSVPriceFeed:
    """Read a price series from a CSV file.

    Expected columns: `date,close` (case-insensitive). The first
    non-header row's close price becomes the starting point.

    Parameters
    ----------
    path : str
        Path to the CSV file.
    date_col : str
        Name of the date column. Default "date".
    price_col : str
        Name of the price column. Default "close".
    """

    def __init__(
        self,
        path: str,
        date_col: str = "date",
        price_col: str = "close",
    ):
        if not os.path.exists(path):
            raise FileNotFoundError(f"CSV file not found: {path}")
        self.path = path
        self.date_col = date_col.lower()
        self.price_col = price_col.lower()
        # Pre-read to count rows and validate
        with open(path, "r", newline="") as f:
            reader = csv.reader(f)
            header = next(reader)
            self._header_idx = {h.lower(): i for i, h in enumerate(header)}
            if self.date_col not in self._header_idx:
                raise ValueError(
                    f"date column {self.date_col!r} not found in {path}; "
                    f"columns are {list(self._header_idx.keys())}"
                )
            if self.price_col not in self._header_idx:
                raise ValueError(
                    f"price column {self.price_col!r} not found in {path}; "
                    f"columns are {list(self._header_idx.keys())}"
                )
            # Cache the prices to avoid repeated file reads
            self._prices: List[Tuple[int, float]] = []
            for row in reader:
                if not row:
                    continue
                date_str = row[self._header_idx[self.date_col]].strip()
                price_str = row[self._header_idx[self.price_col]].strip()
                if not price_str:
                    continue
                try:
                    price = float(price_str)
                except ValueError:
                    continue
                # Parse the date
                ts = self._parse_date(date_str)
                self._prices.append((ts, price))

    @staticmethod
    def _parse_date(s: str) -> int:
        """Parse a date string into a millisecond timestamp."""
        # Try ISO format first
        for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%Y/%m/%d", "%d-%b-%Y"):
            try:
                d = datetime.datetime.strptime(s, fmt)
                return int(d.timestamp() * 1000)
            except ValueError:
                continue
        # Last resort: use the row number as a fake timestamp
        return 0

    def stream(self) -> Iterator[Tuple[int, float]]:
        """Yield (timestamp_ms, price) for each row in the CSV."""
        for ts, price in self._prices:
            yield (ts, price)

    def __len__(self) -> int:
        return len(self._prices)

    @property
    def first_price(self) -> float:
        return self._prices[0][1] if self._prices else 0.0

    @property
    def last_price(self) -> float:
        return self._prices[-1][1] if self._prices else 0.0

    @property
    def total_return(self) -> float:
        if not self._prices:
            return 0.0
        return self._prices[-1][1] / self._prices[0][1] - 1.0


# ─── Yahoo Finance ─────────────────────────────────────────────────

class YahooFinanceFeed:
    """Download prices from Yahoo Finance.

    Uses the v8 chart API (public, no auth needed for daily data).
    The `requests` and `pandas` libraries are NOT required — only
    the standard library.

    Parameters
    ----------
    ticker : str
        e.g. "AAPL", "MSFT", "^GSPC" (S&P 500).
    start : str
        ISO date, e.g. "2020-01-01".
    end : str
        ISO date, e.g. "2024-12-31".
    interval : str
        "1d", "1wk", "1mo", "1h" (1h requires recent data only).
    """

    BASE_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"

    def __init__(
        self,
        ticker: str,
        start: str = "2020-01-01",
        end: str = "2024-12-31",
        interval: str = "1d",
    ):
        self.ticker = ticker
        self.start = start
        self.end = end
        self.interval = interval
        self._prices: Optional[List[Tuple[int, float]]] = None

    def _fetch(self) -> List[Tuple[int, float]]:
        """Hit Yahoo Finance and parse the response."""
        period1 = int(datetime.datetime.fromisoformat(self.start).timestamp())
        period2 = int(datetime.datetime.fromisoformat(self.end).timestamp())
        url = (
            f"{self.BASE_URL.format(ticker=self.ticker)}"
            f"?period1={period1}&period2={period2}&interval={self.interval}"
        )
        req = urllib.request.Request(
            url, headers={"User-Agent": "Mozilla/5.0 quilt-timesfm/1.0"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read()
        # Parse JSON without external libs
        import json
        data = json.loads(raw)
        result = data["chart"]["result"][0]
        timestamps = result["timestamp"]
        closes = result["indicators"]["quote"][0]["close"]
        prices = []
        for ts, close in zip(timestamps, closes):
            if close is None:
                continue
            prices.append((ts * 1000, float(close)))
        return prices

    def stream(self) -> Iterator[Tuple[int, float]]:
        """Yield (timestamp_ms, price) for the requested range."""
        if self._prices is None:
            self._prices = self._fetch()
        for ts, price in self._prices:
            yield (ts, price)

    def __len__(self) -> int:
        if self._prices is None:
            self._prices = self._fetch()
        return len(self._prices)


# ─── Random walk (for deterministic tests) ────────────────────────

class RandomWalkFeed:
    """A deterministic random-walk feed for repeatable tests.

    Uses a fixed RNG seed so the same call always produces the
    same sequence. Cheaper than a network call.
    """

    def __init__(self, n_steps: int = 1000, start_price: float = 100.0,
                 step_std: float = 0.02, seed: int = 42):
        self.n_steps = n_steps
        self.start_price = start_price
        self.step_std = step_std
        self.seed = seed

    def stream(self) -> Iterator[Tuple[int, float]]:
        rng = np.random.default_rng(self.seed)
        price = self.start_price
        for t in range(self.n_steps):
            price *= float(np.exp(rng.normal(0, self.step_std)))
            yield (t, price)
