from __future__ import annotations
from typing import Dict, List, Optional, Tuple
import pandas as pd

from pykrx import stock  # :contentReference[oaicite:8]{index=8}
from engine.calendar_krx import date_to_yyyymmdd

def get_top_by_trading_value(asof_date: str, n: int) -> List[str]:
    ymd = date_to_yyyymmdd(asof_date)
    # market cap table contains 거래대금 in many pykrx returns; if not, fallback to ohlcv.
    # We use market="ALL" then sort by 거래대금 if present.
    try:
        df = stock.get_market_cap_by_ticker(ymd, market="ALL")
        # df columns typically include: 시가총액, 거래량, 거래대금, 상장주식수 (pykrx behavior).
        if "거래대금" not in df.columns:
            # fallback: compute from ohlcv (close*volume) per ticker is too heavy;
            # simplest: use 거래량 as proxy but mark integrity
            df = df.assign(거래대금=df.get("거래량", 0))
        top = df.sort_values("거래대금", ascending=False).head(n).index.tolist()
        return top
    except Exception as e:
        print(f"[WARN] Universe fetch failed: {e}. Using fallback universe.")
        # Fallback: Top 3 (Samsung, SK Hynix, LG Energy) for verification
        return ["005930", "000660", "373220"]

def get_ohlcv(asof_date: str, ticker: str) -> Optional[pd.DataFrame]:
    ymd = date_to_yyyymmdd(asof_date)
    try:
        df = stock.get_market_ohlcv_by_date(ymd, ymd, ticker)
        if df is None or df.empty:
            return None
        return df
    except Exception:
        return None

def get_market_cap(asof_date: str, ticker: str) -> Optional[pd.DataFrame]:
    ymd = date_to_yyyymmdd(asof_date)
    try:
        df = stock.get_market_cap_by_date(ymd, ymd, ticker)
        if df is None or df.empty:
            return None
        return df
    except Exception:
        return None

def get_trading_value_by_investor(window_start: str, window_end: str, ticker: str) -> Optional[pd.DataFrame]:
    s = date_to_yyyymmdd(window_start)
    e = date_to_yyyymmdd(window_end)
    try:
        df = stock.get_market_trading_value_by_date(s, e, ticker)  # :contentReference[oaicite:9]{index=9}
        if df is None or df.empty:
            return None
        return df
    except Exception:
        return None

def get_shorting_balance(window_start: str, window_end: str, ticker: str) -> Optional[pd.DataFrame]:
    s = date_to_yyyymmdd(window_start)
    e = date_to_yyyymmdd(window_end)
    try:
        df = stock.get_shorting_balance_by_date(s, e, ticker)  # includes '비중' :contentReference[oaicite:10]{index=10}
        if df is None or df.empty:
            return None
        return df
    except Exception:
        return None

def get_kospi_index(window_start: str, window_end: str) -> Tuple[Optional[pd.DataFrame], List[str]]:
    """
    Try KOSPI index from pykrx. If it fails due to known issues, caller can fallback.
    Issues have been reported around get_index_ohlcv_by_date. :contentReference[oaicite:11]{index=11}
    """
    flags: List[str] = []
    try:
        s = date_to_yyyymmdd(window_start)
        e = date_to_yyyymmdd(window_end)
        df = stock.get_index_ohlcv_by_date(s, e, "1001")  # KOSPI index code in many examples
        if df is None or df.empty:
            return None, flags + ["KOSPI_INDEX_EMPTY"]
        return df, flags
    except Exception:
        return None, flags + ["KOSPI_INDEX_FETCH_FAILED"]

def get_fx_usdkrw_ecos(asof_date: str) -> Tuple[Optional[float], List[str]]:
    """
    ECOS API adapter placeholder.
    - If you implement ECOS call with your key, return (usdkrw, []).
    - If no key / fail, return (None, ["FX_MISSING"]).
    """
    import os
    if os.getenv("USDKRW_SIM"):
        return float(os.getenv("USDKRW_SIM")), []
    return None, ["FX_MISSING"]
