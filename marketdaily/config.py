"""Central configuration: paths, instruments, site settings. Secrets come only from env vars."""
from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# key, display name, Upstox instrument key, yfinance ticker
INDICES = [
    ("nifty50", "NIFTY 50", "NSE_INDEX|Nifty 50", "^NSEI"),
    ("sensex", "SENSEX", "BSE_INDEX|SENSEX", "^BSESN"),
    ("banknifty", "BANK NIFTY", "NSE_INDEX|Nifty Bank", "^NSEBANK"),
    ("niftyit", "NIFTY IT", "NSE_INDEX|Nifty IT", "^CNXIT"),
]

# Always via yfinance (the Upstox account does not cover these).
COMMODITIES = [
    ("gold", "Gold (USD/oz)", "GC=F"),
    ("silver", "Silver (USD/oz)", "SI=F"),
    ("crude", "Crude oil WTI (USD/bbl)", "CL=F"),
    ("usdinr", "USD/INR", "USDINR=X"),
]

# NIFTY 50 constituents. The index changes twice a year: refresh data/nifty50.json
# (a JSON list of NSE trading symbols) and it overrides this default list.
NIFTY50_DEFAULT = [
    "ADANIENT", "ADANIPORTS", "APOLLOHOSP", "ASIANPAINT", "AXISBANK", "BAJAJ-AUTO",
    "BAJFINANCE", "BAJAJFINSV", "BEL", "BHARTIARTL", "CIPLA", "COALINDIA", "DRREDDY",
    "EICHERMOT", "ETERNAL", "GRASIM", "HCLTECH", "HDFCBANK", "HDFCLIFE", "HINDALCO",
    "HINDUNILVR", "ICICIBANK", "INDIGO", "INFY", "ITC", "JIOFIN", "JSWSTEEL",
    "KOTAKBANK", "LT", "M&M", "MARUTI", "MAXHEALTH", "NESTLEIND", "NTPC", "ONGC",
    "POWERGRID", "RELIANCE", "SBILIFE", "SBIN", "SHRIRAMFIN", "SUNPHARMA", "TATACONSUM",
    "TATASTEEL", "TCS", "TECHM", "TITAN", "TRENT", "ULTRACEMCO", "WIPRO", "TMPV",
]

LANGS = ("en", "hi")
CANDLE_KEEP_DAYS = 900  # calendar days of daily candles kept on disk


@dataclass
class Settings:
    root: Path = ROOT
    site_url: str = ""          # https://example.com  (no trailing slash)
    base_path: str = ""         # "" for a custom domain, "/repo" for github.io/repo
    site_name: str = "Market Daily"
    author: str = "Market Daily"
    contact_email: str = "contact@example.com"
    anthropic_model: str = "claude-sonnet-5-5"
    enable_video: bool = False

    @classmethod
    def from_env(cls, root: Path | None = None) -> "Settings":
        e = os.environ.get
        return cls(
            root=Path(root) if root else ROOT,
            site_url=(e("SITE_URL") or "").rstrip("/"),
            base_path=("/" + e("SITE_BASE_PATH", "").strip("/")) if e("SITE_BASE_PATH", "").strip("/") else "",
            site_name=e("SITE_NAME") or "Market Daily",
            author=e("SITE_AUTHOR") or "Market Daily",
            contact_email=e("CONTACT_EMAIL") or "contact@example.com",
            anthropic_model=e("ANTHROPIC_MODEL") or "claude-sonnet-5-5",
            enable_video=(e("ENABLE_VIDEO", "0") == "1"),
        )

    # ---- paths ----
    @property
    def data_dir(self) -> Path: return self.root / "data"
    @property
    def history_dir(self) -> Path: return self.data_dir / "history"
    @property
    def candles_dir(self) -> Path: return self.data_dir / "candles"
    @property
    def posts_dir(self) -> Path: return self.data_dir / "posts"
    @property
    def news_dir(self) -> Path: return self.data_dir / "news"
    @property
    def cache_dir(self) -> Path: return self.data_dir / "cache"
    @property
    def public_dir(self) -> Path: return self.root / "public"
    @property
    def data_json(self) -> Path: return self.root / "data.json"
    @property
    def holidays_file(self) -> Path: return self.data_dir / "holidays.json"

    def nifty50_symbols(self) -> list[str]:
        f = self.data_dir / "nifty50.json"
        if f.exists():
            try:
                syms = json.loads(f.read_text(encoding="utf-8"))
                if isinstance(syms, list) and syms:
                    return [str(s) for s in syms]
            except (OSError, ValueError):
                pass
        return list(NIFTY50_DEFAULT)


def write_json(path: Path, obj) -> None:
    """Atomic JSON write (never leaves a half-written file)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=1)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def read_json(path: Path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default
