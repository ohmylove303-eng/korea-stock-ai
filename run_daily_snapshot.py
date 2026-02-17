#!/usr/bin/env python3
# run_daily_snapshot.py
# Requirements:
#   pip install pykrx pandas numpy
# Optional (if you want accurate business-day calendar):
#   pip install exchange-calendars
#
# Usage example:
#   python run_daily_snapshot.py --db ./kstock.db --asof 20260205 --universe live150,bt300 --horizon 10,5
#
# Cron (KST 18:10):
#   10 18 * * 1-5 /usr/bin/python3 /path/run_daily_snapshot.py --db /path/kstock.db --universe live150,bt300 --horizon 10,5

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import json
import os
import sqlite3
import sys
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from pykrx import stock

KST = dt.timezone(dt.timedelta(hours=9))


# -----------------------------
# Config / Policy (v1.1 fixed)
# -----------------------------
@dataclass(frozen=True)
class EngineConfig:
    model_rule_version: str = "v1.1"
    regime_rules_version: str = "v1.1"

    window_days_bd: int = 5
    lookback_days_bd_for_tech: int = 120  # for RSI/MACD

    # Universe splits (default)
    live150_kospi: int = 100
    live150_kosdaq: int = 50
    bt300_kospi: int = 200
    bt300_kosdaq: int = 100

    # Gate thresholds
    min_notional_20d_krw: float = 10_000_000_000  # 100억
    foreign_z_min: float = 1.0
    inst_z_min: float = 0.5
    short_ratio_max: float = 15.0  # percent

    # Regime thresholds
    kospi_bear_th: float = -3.0
    kospi_bull_th: float = 3.0

    # Score weights
    w_foreign: float = 0.40
    w_inst: float = 0.30
    w_tech: float = 0.20
    w_regime: float = 0.10

    # Short regime cutover (store in DB snapshot)
    short_cutover_date: str = os.getenv("SHORT_CUTOVER_DATE", "20250101")  # YYYYMMDD


def now_kst_iso() -> str:
    return dt.datetime.now(tz=KST).isoformat(timespec="seconds")


def safe_json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def latest_business_day_yyyymmdd() -> str:
    """
    Best effort: if exchange-calendars is available, use XKRX.
    Otherwise fallback to "today or previous weekday" (flagged later).
    """
    today = dt.datetime.now(tz=KST).date()
    try:
        import exchange_calendars as xc  # type: ignore
        cal = xc.get_calendar("XKRX")
        sessions = cal.sessions_in_range(pd.Timestamp(today - dt.timedelta(days=10)),
                                         pd.Timestamp(today))
        if len(sessions) == 0:
            return today.strftime("%Y%m%d")
        return sessions[-1].strftime("%Y%m%d")
    except Exception:
        # fallback (not holiday-aware)
        d = today
        while d.weekday() >= 5:  # Sat/Sun
            d -= dt.timedelta(days=1)
        return d.strftime("%Y%m%d")


def business_day_shift(asof: str, n_bd: int) -> str:
    """
    Shift by business days using exchange-calendars if possible.
    If not, fallback to weekday-only shifting (flag with integrity later).
    """
    d0 = dt.datetime.strptime(asof, "%Y%m%d").date()
    try:
        import exchange_calendars as xc  # type: ignore
        cal = xc.get_calendar("XKRX")
        # find session index
        sessions = cal.sessions_in_range(pd.Timestamp(d0 - dt.timedelta(days=365)),
                                         pd.Timestamp(d0 + dt.timedelta(days=365)))
        s = pd.Timestamp(d0)
        idx = sessions.get_loc(s)
        shifted = sessions[idx + n_bd]
        return shifted.strftime("%Y%m%d")
    except Exception:
        # fallback weekday-only
        step = 1 if n_bd >= 0 else -1
        remain = abs(n_bd)
        d = d0
        while remain > 0:
            d += dt.timedelta(days=step)
            if d.weekday() < 5:
                remain -= 1
        return d.strftime("%Y%m%d")


# -----------------------------
# Indicators (minimal, reproducible)
# -----------------------------
def rsi(series: pd.Series, period: int = 14) -> float:
    if len(series) < period + 1:
        return float("nan")
    delta = series.diff()
    up = delta.clip(lower=0).ewm(alpha=1/period, adjust=False).mean()
    down = (-delta.clip(upper=0)).ewm(alpha=1/period, adjust=False).mean()
    rs = up / (down + 1e-12)
    val = 100 - (100 / (1 + rs))
    return float(val.iloc[-1])


def macd_hist(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> float:
    if len(series) < slow + signal + 5:
        return float("nan")
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line
    return float(hist.iloc[-1])


def vcp_proxy_score(close: pd.Series) -> float:
    """
    Very light proxy (NOT a full Minervini VCP).
    We keep it as a bounded feature, and if insufficient data -> NaN.
    """
    if len(close) < 30:
        return float("nan")
    ret = close.pct_change().dropna()
    vol5 = float(ret.tail(5).std())
    vol20 = float(ret.tail(20).std())
    if vol20 <= 1e-12:
        return float("nan")
    # contraction -> higher score
    ratio = vol5 / vol20
    score = 100 * (1 - min(max(ratio, 0.0), 2.0) / 2.0)
    return float(np.clip(score, 0, 100))


# -----------------------------
# Data collectors (pykrx)
# -----------------------------
def get_ohlcv_by_date(start: str, end: str, ticker: str) -> Tuple[pd.DataFrame, List[str]]:
    flags = []
    try:
        df = stock.get_market_ohlcv_by_date(start, end, ticker)
        if df is None or len(df) == 0:
            flags.append("OHLCV_EMPTY")
            return pd.DataFrame(), flags
        return df.copy(), flags
    except Exception:
        flags.append("OHLCV_ERROR")
        return pd.DataFrame(), flags


def get_trading_value_by_date(start: str, end: str, ticker: str) -> Tuple[pd.DataFrame, List[str]]:
    flags = []
    try:
        df = stock.get_market_trading_value_by_date(start, end, ticker)
        if df is None or len(df) == 0:
            flags.append("FLOW_EMPTY")
            return pd.DataFrame(), flags
        return df.copy(), flags
    except Exception:
        flags.append("FLOW_ERROR")
        return pd.DataFrame(), flags


def get_short_balance_by_date(start: str, end: str, ticker: str) -> Tuple[pd.DataFrame, List[str]]:
    flags = []
    try:
        df = stock.get_shorting_balance_by_date(start, end, ticker)
        if df is None or len(df) == 0:
            flags.append("SHORT_EMPTY")
            return pd.DataFrame(), flags
        return df.copy(), flags
    except Exception:
        flags.append("SHORT_ERROR")
        return pd.DataFrame(), flags


def get_index_kospi_ohlcv(start: str, end: str) -> Tuple[pd.DataFrame, List[str]]:
    flags = []
    try:
        # pykrx supports index OHLCV by "KOSPI" code in some APIs;
        # safer: use "1001" (KOSPI) if needed, but environments differ.
        # We'll attempt two methods.
        try:
            df = stock.get_index_ohlcv_by_date(start, end, "1001")  # KOSPI
        except Exception:
            df = stock.get_index_ohlcv_by_date(start, end, "KOSPI")
        if df is None or len(df) == 0:
            flags.append("KOSPI_IDX_EMPTY")
            return pd.DataFrame(), flags
        return df.copy(), flags
    except Exception:
        flags.append("KOSPI_IDX_ERROR")
        return pd.DataFrame(), flags


def estimate_notional(df_ohlcv: pd.DataFrame) -> Tuple[Optional[float], List[str]]:
    flags = []
    if df_ohlcv is None or len(df_ohlcv) == 0:
        return None, ["NOTIONAL_NO_OHLCV"]
    if "거래대금" in df_ohlcv.columns:
        return float(df_ohlcv["거래대금"].sum()), flags
    # fallback: close * volume
    if "종가" in df_ohlcv.columns and "거래량" in df_ohlcv.columns:
        flags.append("NOTIONAL_APPROX_CLOSE_X_VOL")
        return float((df_ohlcv["종가"] * df_ohlcv["거래량"]).sum()), flags
    return None, ["NOTIONAL_MISSING_COLS"]


# -----------------------------
# Regime (USD/KRW is best-effort; missing -> CAUTION/BLOCK)
# -----------------------------
def get_usdkrw_close_best_effort(asof: str) -> Tuple[Optional[float], List[str], Dict[str, str]]:
    """
    Prefer ECOS if user wired it; otherwise try FinanceDataReader.
    If neither works -> None known; degrade later.
    """
    flags = []
    tags = {}

    # 1) ECOS (BOK) - requires env ECOS_API_KEY + series codes (user-specific).
    ecos_key = os.getenv("ECOS_API_KEY")
    if ecos_key:
        # We do NOT guess series codes here. If you wire your own,
        # set USDKRW_MANUAL in env as a fallback.
        tags["usdkrw"] = "ECOS_BOK"
        manual = os.getenv("USDKRW_MANUAL")
        if manual:
            try:
                return float(manual), flags + ["USDKRW_FROM_MANUAL_ENV"], tags
            except Exception:
                flags.append("USDKRW_MANUAL_PARSE_FAIL")

    # 2) FinanceDataReader
    try:
        import FinanceDataReader as fdr  # type: ignore
        tags["usdkrw"] = "FDR"
        d = dt.datetime.strptime(asof, "%Y%m%d").date()
        df = fdr.DataReader("USD/KRW", d - dt.timedelta(days=40), d)
        if df is None or len(df) == 0:
            flags.append("USDKRW_EMPTY")
            return None, flags, tags
        # assume "Close" exists
        close = float(df["Close"].iloc[-1])
        return close, flags, tags
    except Exception:
        flags.append("USDKRW_UNAVAILABLE")
        return None, flags, tags


def compute_regime(cfg: EngineConfig, asof: str) -> Tuple[Dict[str, Any], List[str]]:
    flags: List[str] = []

    # KOSPI 20D trend
    start20 = business_day_shift(asof, -20)
    kospi_df, kospi_flags = get_index_kospi_ohlcv(start20, asof)
    flags += kospi_flags
    kospi_close = None
    kospi_trend_20d = None
    kospi_regime = None
    if len(kospi_df) > 0 and "종가" in kospi_df.columns:
        kospi_close = float(kospi_df["종가"].iloc[-1])
        first = float(kospi_df["종가"].iloc[0])
        if first != 0:
            kospi_trend_20d = 100 * (kospi_close / first - 1)
            if kospi_trend_20d <= cfg.kospi_bear_th:
                kospi_regime = "bear"
            elif kospi_trend_20d >= cfg.kospi_bull_th:
                kospi_regime = "bull"
            else:
                kospi_regime = "neutral"
    else:
        flags.append("KOSPI_TREND_MISSING")

    # USDKRW
    usdkrw_close, usd_flags, usd_tags = get_usdkrw_close_best_effort(asof)
    flags += usd_flags
    usdkrw_ma20 = None
    usdkrw_regime = None
    if usdkrw_close is not None:
        # best-effort MA20 using last 20 calendar days via FDR (if available)
        try:
            import FinanceDataReader as fdr  # type: ignore
            d = dt.datetime.strptime(asof, "%Y%m%d").date()
            df = fdr.DataReader("USD/KRW", d - dt.timedelta(days=60), d)
            if df is not None and len(df) >= 20:
                usdkrw_ma20 = float(df["Close"].tail(20).mean())
                usdkrw_regime = "weak_krw" if usdkrw_close > usdkrw_ma20 else "strong_krw"
        except Exception:
            flags.append("USDKRW_MA20_UNAVAILABLE")

    # Short regime tag
    short_regime_tag = "POST" if asof >= cfg.short_cutover_date else "PRE"

    regime_reason = []
    if kospi_regime:
        regime_reason.append(f"kospi_regime={kospi_regime}")
    if usdkrw_regime:
        regime_reason.append(f"usdkrw_regime={usdkrw_regime}")
    regime_reason.append(f"short_regime_tag={short_regime_tag}")

    return {
        "usdkrw_close": usdkrw_close,
        "usdkrw_ma20": usdkrw_ma20,
        "kospi_close": kospi_close,
        "kospi_trend_20d_pct": kospi_trend_20d,
        "kospi_regime": kospi_regime,
        "usdkrw_regime": usdkrw_regime,
        "short_regime_tag": short_regime_tag,
        "regime_reason": ";".join(regime_reason),
        "source_tags": {"kospi": "KRX_PYKRX", **usd_tags, "short_regime": "CONFIG"},
    }, flags


# -----------------------------
# Universe selection (by notional on asof)
# -----------------------------
def get_daily_market_notional_df(asof: str) -> Tuple[pd.DataFrame, List[str]]:
    flags = []
    try:
        df = stock.get_market_ohlcv_by_ticker(asof)
        if df is None or len(df) == 0:
            return pd.DataFrame(), ["MKT_OHLCV_EMPTY"]
        out = df.copy()
        # Ensure notional column exists
        if "거래대금" not in out.columns:
            if {"종가", "거래량"}.issubset(set(out.columns)):
                out["거래대금"] = out["종가"] * out["거래량"]
                flags.append("MKT_NOTIONAL_APPROX")
            else:
                flags.append("MKT_NOTIONAL_MISSING")
        return out, flags
    except Exception:
        return pd.DataFrame(), ["MKT_OHLCV_ERROR"]


def get_ticker_list(asof: str, market: str) -> Tuple[List[str], List[str]]:
    flags = []
    try:
        tickers = stock.get_market_ticker_list(asof, market=market)
        return list(tickers), flags
    except Exception:
        flags.append(f"TICKER_LIST_FAIL_{market}")
        return [], flags


def build_universe(cfg: EngineConfig, asof: str, universe_type: str) -> Tuple[List[Tuple[str, str, int, float]], List[str]]:
    """
    Returns list of (ticker, market, rank, notional_krw) for the universe.
    """
    flags: List[str] = []
    df_all, f0 = get_daily_market_notional_df(asof)
    flags += f0

    kospi_list, f1 = get_ticker_list(asof, "KOSPI")
    kosdaq_list, f2 = get_ticker_list(asof, "KOSDAQ")
    flags += f1 + f2

    if df_all is None or len(df_all) == 0:
        return [], flags + ["UNIVERSE_EMPTY_NO_MARKET_DF"]

    def top(df: pd.DataFrame, tickers: List[str], k: int) -> pd.DataFrame:
        if len(tickers) == 0:
            # fallback: cannot market-split; take global top-k
            return df.sort_values("거래대금", ascending=False).head(k)
        subset = df.loc[df.index.intersection(tickers)].copy()
        return subset.sort_values("거래대금", ascending=False).head(k)

    if universe_type == "live150":
        k1, k2 = cfg.live150_kospi, cfg.live150_kosdaq
    else:
        k1, k2 = cfg.bt300_kospi, cfg.bt300_kosdaq

    top_kospi = top(df_all, kospi_list, k1)
    top_kosdaq = top(df_all, kosdaq_list, k2)

    rows: List[Tuple[str, str, int, float]] = []
    r = 1
    for ticker, row in top_kospi.iterrows():
        rows.append((str(ticker), "KOSPI", r, float(row["거래대금"]) if "거래대금" in row else float("nan")))
        r += 1
    for ticker, row in top_kosdaq.iterrows():
        rows.append((str(ticker), "KOSDAQ", r, float(row["거래대금"]) if "거래대금" in row else float("nan")))
        r += 1

    return rows, flags


# -----------------------------
# Decision logic (Gate -> Score)
# -----------------------------
def zscore(x: float, mean: float, std: float) -> float:
    if std is None or std <= 1e-12:
        return float("nan")
    return (x - mean) / std


def make_fractal_signature(ret5: Optional[float], ret20: Optional[float], vol_ratio: Optional[float],
                          fz: Optional[float], sz: Optional[float]) -> str:
    def b(v: Optional[float], scale: float, clip: float) -> int:
        if v is None or np.isnan(v):
            return 9999
        vv = float(np.clip(v, -clip, clip))
        return int(round(vv * scale))
    return f"r5:{b(ret5,1,50)}|r20:{b(ret20,1,80)}|vr:{b(vol_ratio,100,5)}|fz:{b(fz,10,5)}|sz:{b(sz,10,100)}"


def decide_one(cfg: EngineConfig, regime: Dict[str, Any], snap: Dict[str, Any],
               foreign_z: Optional[float], inst_z: Optional[float]) -> Dict[str, Any]:
    gates = {}
    failed = []
    contra = []

    # Regime gate (Palantir)
    kospi_regime = regime.get("kospi_regime")
    usdkrw_close = regime.get("usdkrw_close")
    if kospi_regime is None:
        gates["regime_kospi"] = False
        failed.append("REGIME_KOSPI_MISSING")
    else:
        gates["regime_kospi"] = kospi_regime in ("bull", "neutral")
        if not gates["regime_kospi"]:
            failed.append(f"REGIME_KOSPI_{kospi_regime.upper()}")

    if usdkrw_close is None:
        gates["regime_usdkrw"] = False
        failed.append("REGIME_USDKRW_MISSING")
    else:
        gates["regime_usdkrw"] = True  # we don't hard-block solely by USDKRW here; you can tighten later

    # Liquidity gate
    notional_20d = snap.get("notional_20d_krw")
    gates["liquidity"] = (notional_20d is not None and not np.isnan(notional_20d) and notional_20d >= cfg.min_notional_20d_krw)
    if not gates["liquidity"]:
        failed.append("LIQUIDITY_FAIL")

    # Short crowded gate
    short_ratio = snap.get("short_ratio")
    if short_ratio is None or np.isnan(short_ratio):
        gates["not_crowded"] = False
        failed.append("SHORT_RATIO_MISSING")
    else:
        gates["not_crowded"] = float(short_ratio) < cfg.short_ratio_max
        if not gates["not_crowded"]:
            failed.append("CROWDED_SHORT")

    # Flow gates (need zscores)
    if foreign_z is None or np.isnan(foreign_z):
        gates["foreign_z"] = False
        failed.append("FOREIGN_Z_MISSING")
    else:
        gates["foreign_z"] = float(foreign_z) >= cfg.foreign_z_min
        if not gates["foreign_z"]:
            contra.append("FOREIGN_FLOW_WEAK")

    if inst_z is None or np.isnan(inst_z):
        gates["inst_z"] = False
        failed.append("INST_Z_MISSING")
    else:
        gates["inst_z"] = float(inst_z) >= cfg.inst_z_min
        if not gates["inst_z"]:
            contra.append("INST_FLOW_WEAK")

    # Technical signals (optional; missing reduces confidence)
    rsi14 = snap.get("rsi_14")
    mh = snap.get("macd_hist")
    tech_ok = True
    tech_strength = 0.0
    tech_missing = False
    if rsi14 is None or np.isnan(rsi14) or mh is None or np.isnan(mh):
        tech_missing = True
        contra.append("TECH_MISSING")
    else:
        # Minimal interpretation
        tech_strength = float(np.clip((rsi14 - 50) / 20, -1, 1))  # -1..1
        tech_ok = (rsi14 >= 50) and (mh >= 0)

    gates["tech_ok"] = tech_ok if not tech_missing else False

    # Integrity grade influences action
    integrity_grade = snap.get("integrity_grade", "CAUTION")

    hard_pass = all([
        gates.get("regime_kospi", False),
        gates.get("liquidity", False),
        gates.get("not_crowded", False),
        gates.get("foreign_z", False),
    ])

    # Score (NICE)
    reg_bonus = 1.0 if kospi_regime in ("bull", "neutral") else 0.0
    fz = float(foreign_z) if foreign_z is not None and not np.isnan(foreign_z) else 0.0
    iz = float(inst_z) if inst_z is not None and not np.isnan(inst_z) else 0.0
    tech_component = tech_strength if not tech_missing else 0.0

    score = 100 * (
        cfg.w_foreign * np.tanh(fz / 2.0) +
        cfg.w_inst * np.tanh(iz / 2.0) +
        cfg.w_tech * tech_component +
        cfg.w_regime * reg_bonus
    )
    score = float(np.clip(score, 0, 100))

    # Confidence penalization
    confidence = score
    if integrity_grade == "BLOCK":
        confidence = min(confidence, 20)
    if tech_missing:
        confidence -= 10
    if usdkrw_close is None:
        confidence -= 10
    confidence = float(np.clip(confidence, 0, 100))

    if integrity_grade == "BLOCK":
        action = "REJECT"
    elif hard_pass and score >= 70:
        action = "BUY"
    elif score >= 55 and integrity_grade != "BLOCK":
        action = "WATCH"
    else:
        action = "REJECT"

    return {
        "action": action,
        "nice_score": score,
        "confidence": confidence,
        "gates": gates,
        "failed_reasons": failed,
        "contra_evidence": contra,
    }


# -----------------------------
# DB helpers (SQLite UPSERT)
# -----------------------------
@contextlib.contextmanager
def sqlite_tx(db_path: str):
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA foreign_keys=ON;")
        conn.execute("BEGIN;")
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def upsert(conn: sqlite3.Connection, sql: str, params: Tuple[Any, ...]) -> None:
    conn.execute(sql, params)


def ensure_schema(conn: sqlite3.Connection, schema_sql_path: Optional[str]) -> None:
    if not schema_sql_path:
        return
    with open(schema_sql_path, "r", encoding="utf-8") as f:
        conn.executescript(f.read())


# -----------------------------
# Main pipeline
# -----------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", required=True, help="SQLite DB path, e.g., ./kstock.db")
    parser.add_argument("--schema", default=None, help="Optional: path to schema_v1_1_sqlite.sql")
    parser.add_argument("--asof", default=None, help="YYYYMMDD, default=latest business day")
    parser.add_argument("--universe", default="live150,bt300", help="CSV: live150,bt300")
    parser.add_argument("--horizon", default="10,5", help="CSV business-day horizons, e.g., 10,5")
    args = parser.parse_args()

    cfg = EngineConfig()
    asof = args.asof or latest_business_day_yyyymmdd()
    universe_list = [u.strip() for u in args.universe.split(",") if u.strip()]
    horizons = [int(x.strip()) for x in args.horizon.split(",") if x.strip()]

    run_id = str(uuid.uuid4())
    asof_ts = now_kst_iso()

    integrity_flags_run: List[str] = []
    calendar_fallback = False
    try:
        import exchange_calendars as _  # noqa
    except Exception:
        calendar_fallback = True
        integrity_flags_run.append("CALENDAR_FALLBACK_WEEKDAY_ONLY")

    regime, regime_flags = compute_regime(cfg, asof)
    integrity_flags_run += regime_flags

    # Build universes
    universes: Dict[str, List[Tuple[str, str, int, float]]] = {}
    for u in universe_list:
        rows, uflags = build_universe(cfg, asof, u)
        universes[u] = rows
        integrity_flags_run += uflags
        if len(rows) == 0:
            integrity_flags_run.append(f"UNIVERSE_EMPTY_{u}")

    # Collect per-ticker snapshots (raw first)
    snapshots: Dict[str, Dict[str, Dict[str, Any]]] = {u: {} for u in universe_list}
    raw_source_tags = {
        "ohlcv": "KRX_PYKRX",
        "flow": "KRX_PYKRX",
        "short": "KRX_PYKRX",
        "regime": regime.get("source_tags", {}),
    }

    # We compute raw fields first, then compute universe stats, then z/decisions.
    for u in universe_list:
        for (ticker, market, rank, notional_krw) in universes[u]:
            flags: List[str] = []

            window_end = asof
            window_start = business_day_shift(asof, -cfg.window_days_bd + 1)  # inclusive window length
            tech_start = business_day_shift(asof, -cfg.lookback_days_bd_for_tech + 1)

            # OHLCV for returns and notional
            ohlcv_w, f_ohlcv = get_ohlcv_by_date(window_start, window_end, ticker)
            flags += f_ohlcv

            notional_5d, f_notional = estimate_notional(ohlcv_w)
            flags += f_notional

            # 20d notional for liquidity gate (use 20bd window)
            start20 = business_day_shift(asof, -20 + 1)
            ohlcv_20, f_ohlcv20 = get_ohlcv_by_date(start20, asof, ticker)
            flags += f_ohlcv20
            notional_20d, f_notional20 = estimate_notional(ohlcv_20)
            flags += f_notional20

            price_close = float("nan")
            ret5 = float("nan")
            if len(ohlcv_w) > 0 and "종가" in ohlcv_w.columns:
                price_close = float(ohlcv_w["종가"].iloc[-1])
                first = float(ohlcv_w["종가"].iloc[0])
                if first != 0:
                    ret5 = 100 * (price_close / first - 1)
            else:
                flags.append("PRICE_CLOSE_MISSING")

            ret20 = float("nan")
            if len(ohlcv_20) > 0 and "종가" in ohlcv_20.columns:
                p0 = float(ohlcv_20["종가"].iloc[0])
                p1 = float(ohlcv_20["종가"].iloc[-1])
                if p0 != 0:
                    ret20 = 100 * (p1 / p0 - 1)

            # Flow (investor net trading value)
            flow_df, f_flow = get_trading_value_by_date(window_start, window_end, ticker)
            flags += f_flow
            foreign_net = float("nan")
            inst_net = float("nan")
            if len(flow_df) > 0:
                # Columns vary; use best-effort keys
                if "외국인" in flow_df.columns:
                    foreign_net = float(flow_df["외국인"].sum())
                else:
                    flags.append("FLOW_FOREIGN_COL_MISSING")
                if "기관합계" in flow_df.columns:
                    inst_net = float(flow_df["기관합계"].sum())
                elif "기관" in flow_df.columns:
                    inst_net = float(flow_df["기관"].sum())
                else:
                    flags.append("FLOW_INST_COL_MISSING")
            else:
                flags.append("FLOW_DF_EMPTY")

            foreign_flow_pct = float("nan")
            inst_flow_pct = float("nan")
            if notional_5d is None or notional_5d == 0 or np.isnan(notional_5d):
                flags.append("FLOW_PCT_NO_NOTIONAL")
            else:
                if not np.isnan(foreign_net):
                    foreign_flow_pct = 100 * (foreign_net / float(notional_5d))
                else:
                    flags.append("FOREIGN_NET_MISSING")
                if not np.isnan(inst_net):
                    inst_flow_pct = 100 * (inst_net / float(notional_5d))
                else:
                    flags.append("INST_NET_MISSING")

            # Short balance
            short_df, f_short = get_short_balance_by_date(window_start, window_end, ticker)
            flags += f_short
            short_ratio = float("nan")
            short_chg = float("nan")
            if len(short_df) > 0:
                # "비중" is present in official example. :contentReference[oaicite:2]{index=2} (in narrative)
                if "비중" in short_df.columns:
                    short_ratio = float(short_df["비중"].iloc[-1])
                    if len(short_df) >= cfg.window_days_bd:
                        short_chg = float(short_df["비중"].iloc[-1] - short_df["비중"].iloc[0])
                else:
                    flags.append("SHORT_RATIO_COL_MISSING")
            else:
                flags.append("SHORT_DF_EMPTY")

            # Technical indicators (lookback)
            tech_df, f_tech = get_ohlcv_by_date(tech_start, asof, ticker)
            flags += f_tech
            rsi14 = float("nan")
            mh = float("nan")
            vcp = float("nan")
            if len(tech_df) > 0 and "종가" in tech_df.columns:
                close = tech_df["종가"].astype(float)
                rsi14 = rsi(close, 14)
                mh = macd_hist(close)
                vcp = vcp_proxy_score(close)
            else:
                flags.append("TECH_CLOSE_MISSING")

            # Integrity grade (hard)
            critical_missing = any(x in flags for x in ["OHLCV_ERROR", "FLOW_ERROR", "FLOW_EMPTY", "OHLCV_EMPTY"])
            if critical_missing:
                grade = "BLOCK"
            elif any(x.endswith("_MISSING") or x.endswith("_EMPTY") for x in flags):
                grade = "CAUTION"
            else:
                grade = "PASS"

            # Save raw snapshot (zscore later)
            snapshots[u][ticker] = {
                "ticker": ticker,
                "market": market,
                "rank": rank,
                "notional_asof_krw": notional_krw,

                "window_days_bd": cfg.window_days_bd,
                "window_start_date": window_start,
                "window_end_date": window_end,

                "price_close": None if np.isnan(price_close) else price_close,
                "ret_5d_pct": None if np.isnan(ret5) else ret5,
                "ret_20d_pct": None if np.isnan(ret20) else ret20,

                "notional_5d_krw": notional_5d,
                "notional_20d_krw": notional_20d,

                "foreign_net_buy_krw": None if np.isnan(foreign_net) else foreign_net,
                "inst_net_buy_krw": None if np.isnan(inst_net) else inst_net,

                "foreign_flow_pct": None if np.isnan(foreign_flow_pct) else foreign_flow_pct,
                "inst_flow_pct": None if np.isnan(inst_flow_pct) else inst_flow_pct,

                "short_ratio": None if np.isnan(short_ratio) else short_ratio,
                "short_ratio_chg_5d": None if np.isnan(short_chg) else short_chg,

                "rsi_14": None if np.isnan(rsi14) else rsi14,
                "macd_hist": None if np.isnan(mh) else mh,
                "vcp_score": None if np.isnan(vcp) else vcp,

                "integrity_grade": grade,
                "integrity_flags": sorted(list(set(flags))),
                "raw_source_tags": raw_source_tags,
                "derived_meta": {},
            }

    # Compute universe stats (mean/std) for flow_pct
    universe_stats: Dict[str, Dict[str, float]] = {}
    for u in universe_list:
        vals_f = [snap["foreign_flow_pct"] for snap in snapshots[u].values() if snap.get("foreign_flow_pct") is not None]
        vals_i = [snap["inst_flow_pct"] for snap in snapshots[u].values() if snap.get("inst_flow_pct") is not None]
        f_mean = float(np.mean(vals_f)) if len(vals_f) > 3 else float("nan")
        f_std = float(np.std(vals_f, ddof=1)) if len(vals_f) > 3 else float("nan")
        i_mean = float(np.mean(vals_i)) if len(vals_i) > 3 else float("nan")
        i_std = float(np.std(vals_i, ddof=1)) if len(vals_i) > 3 else float("nan")
        universe_stats[u] = {
            "foreign_flow_mean": None if np.isnan(f_mean) else f_mean,
            "foreign_flow_std": None if np.isnan(f_std) else f_std,
            "inst_flow_mean": None if np.isnan(i_mean) else i_mean,
            "inst_flow_std": None if np.isnan(i_std) else i_std,
        }
        if np.isnan(f_mean) or np.isnan(f_std):
            integrity_flags_run.append(f"UNIVERSE_STATS_WEAK_FOREIGN_{u}")
        if np.isnan(i_mean) or np.isnan(i_std):
            integrity_flags_run.append(f"UNIVERSE_STATS_WEAK_INST_{u}")

    # Finalize zscores + decisions + fractal signature
    decisions_rows: List[Dict[str, Any]] = []
    for u in universe_list:
        f_mean = universe_stats[u]["foreign_flow_mean"]
        f_std = universe_stats[u]["foreign_flow_std"]
        i_mean = universe_stats[u]["inst_flow_mean"]
        i_std = universe_stats[u]["inst_flow_mean"]

        for ticker, snap in snapshots[u].items():
            ff = snap.get("foreign_flow_pct")
            ii = snap.get("inst_flow_pct")
            fz = None
            iz = None
            if ff is not None and f_mean is not None and f_std is not None:
                fz_val = zscore(float(ff), float(f_mean), float(f_std)) if (f_std and f_std > 1e-12) else float("nan")
                fz = None if np.isnan(fz_val) else float(fz_val)
            if ii is not None and i_mean is not None and i_std is not None:
                iz_val = zscore(float(ii), float(i_mean), float(i_std)) if (i_std and i_std > 1e-12) else float("nan")
                iz = None if np.isnan(iz_val) else float(iz_val)

            snap["derived_meta"]["foreign_z"] = fz
            snap["derived_meta"]["inst_z"] = iz

            # Fractal signature (matching is handled later via fractal_cases)
            vol_ratio = None
            if snap.get("notional_20d_krw") and snap.get("notional_5d_krw"):
                try:
                    vol_ratio = float(snap["notional_5d_krw"]) / (float(snap["notional_20d_krw"]) / 4.0)
                except Exception:
                    vol_ratio = None
            signature = make_fractal_signature(snap.get("ret_5d_pct"), snap.get("ret_20d_pct"),
                                               vol_ratio, fz, snap.get("short_ratio"))
            snap["fractal_signature"] = signature
            snap["fractal_match_count"] = None
            snap["fractal_expected_ret_5d"] = None
            snap["fractal_expected_ret_10d"] = None
            snap["integrity_flags"].append("FRACTAL_MATCH_DEFERRED_TO_SCORER")

            # Decision per horizon
            d0 = decide_one(cfg, regime, {**snap, **snap.get("derived_meta", {}), "integrity_grade": snap["integrity_grade"]},
                            foreign_z=fz, inst_z=iz)

            for h in horizons:
                decisions_rows.append({
                    "run_id": run_id,
                    "universe_type": u,
                    "ticker": ticker,
                    "horizon_bd": h,
                    "model_rule_version": cfg.model_rule_version,
                    "action": d0["action"],
                    "nice_score": d0["nice_score"],
                    "confidence": d0["confidence"],
                    "expected_ret_pct": None,  # optional: fill later when you add a calibrated expected-return model
                    "gates": d0["gates"],
                    "failed_reasons": d0["failed_reasons"],
                    "contra_evidence": d0["contra_evidence"],
                    "decided_at_kst": asof_ts,
                })

    # Write DB (transaction + UPSERT)
    integrity_summary = {
        "run_flags": sorted(list(set(integrity_flags_run))),
        "universe_counts": {u: len(universes[u]) for u in universe_list},
        "regime": regime,
    }

    with sqlite_tx(args.db) as conn:
        ensure_schema(conn, args.schema)

        # runs UPSERT
        upsert(conn, """
        INSERT INTO runs (run_id, asof_date, asof_ts_kst, status, universe_csv, horizon_csv, window_days_bd, code_version, args_json, integrity_summary_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(run_id) DO UPDATE SET
          status=excluded.status,
          integrity_summary_json=excluded.integrity_summary_json;
        """, (
            run_id, asof, asof_ts, "OK",
            ",".join(universe_list),
            ",".join([str(h) for h in horizons]),
            cfg.window_days_bd,
            os.getenv("GIT_SHA"),
            safe_json(vars(args)),
            safe_json(integrity_summary),
        ))

        # config snapshot
        upsert(conn, """
        INSERT INTO config_snapshots (run_id, short_cutover_date, regime_rules_version, config_json)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(run_id) DO UPDATE SET
          config_json=excluded.config_json;
        """, (
            run_id, cfg.short_cutover_date, cfg.regime_rules_version, safe_json(cfg.__dict__)
        ))

        # regime snapshot
        upsert(conn, """
        INSERT INTO regime_snapshots
        (run_id, usdkrw_close, usdkrw_ma20, kospi_close, kospi_trend_20d_pct, kospi_regime, usdkrw_regime, short_regime_tag,
         regime_reason, source_tags_json, integrity_flags_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(run_id) DO UPDATE SET
          usdkrw_close=excluded.usdkrw_close,
          kospi_trend_20d_pct=excluded.kospi_trend_20d_pct,
          integrity_flags_json=excluded.integrity_flags_json;
        """, (
            run_id,
            regime.get("usdkrw_close"), regime.get("usdkrw_ma20"),
            regime.get("kospi_close"), regime.get("kospi_trend_20d_pct"),
            regime.get("kospi_regime"), regime.get("usdkrw_regime"),
            regime.get("short_regime_tag"),
            regime.get("regime_reason"),
            safe_json(regime.get("source_tags", {})),
            safe_json(regime_flags),
        ))

        # universe_members
        for u in universe_list:
            for (ticker, market, rank, notional_krw) in universes[u]:
                upsert(conn, """
                INSERT INTO universe_members (run_id, universe_type, ticker, market, rank, notional_krw)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(run_id, universe_type, ticker) DO UPDATE SET
                  rank=excluded.rank,
                  notional_krw=excluded.notional_krw;
                """, (run_id, u, ticker, market, rank, notional_krw))

        # ticker_snapshots
        for u in universe_list:
            for ticker, snap in snapshots[u].items():
                upsert(conn, """
                INSERT INTO ticker_snapshots
                (run_id, universe_type, ticker, window_days_bd, window_start_date, window_end_date,
                 price_close, ret_5d_pct, ret_20d_pct,
                 notional_5d_krw, notional_20d_krw,
                 foreign_net_buy_krw, inst_net_buy_krw,
                 foreign_flow_pct, inst_flow_pct,
                 short_ratio, short_ratio_chg_5d,
                 rsi_14, macd_hist, vcp_score,
                 fractal_signature, fractal_match_count, fractal_expected_ret_5d, fractal_expected_ret_10d,
                 integrity_grade, integrity_flags_json, raw_source_tags_json, derived_meta_json)
                VALUES (?, ?, ?, ?, ?, ?,
                        ?, ?, ?,
                        ?, ?,
                        ?, ?,
                        ?, ?,
                        ?, ?,
                        ?, ?, ?,
                        ?, ?, ?, ?,
                        ?, ?, ?, ?)
                ON CONFLICT(run_id, universe_type, ticker, window_days_bd) DO UPDATE SET
                  price_close=excluded.price_close,
                  foreign_net_buy_krw=excluded.foreign_net_buy_krw,
                  foreign_flow_pct=excluded.foreign_flow_pct,
                  integrity_grade=excluded.integrity_grade,
                  integrity_flags_json=excluded.integrity_flags_json,
                  derived_meta_json=excluded.derived_meta_json;
                """, (
                    run_id, u, ticker, snap["window_days_bd"], snap["window_start_date"], snap["window_end_date"],
                    snap.get("price_close"), snap.get("ret_5d_pct"), snap.get("ret_20d_pct"),
                    snap.get("notional_5d_krw"), snap.get("notional_20d_krw"),
                    snap.get("foreign_net_buy_krw"), snap.get("inst_net_buy_krw"),
                    snap.get("foreign_flow_pct"), snap.get("inst_flow_pct"),
                    snap.get("short_ratio"), snap.get("short_ratio_chg_5d"),
                    snap.get("rsi_14"), snap.get("macd_hist"), snap.get("vcp_score"),
                    snap.get("fractal_signature"), snap.get("fractal_match_count"),
                    snap.get("fractal_expected_ret_5d"), snap.get("fractal_expected_ret_10d"),
                    snap.get("integrity_grade"),
                    safe_json(snap.get("integrity_flags", [])),
                    safe_json(snap.get("raw_source_tags", {})),
                    safe_json(snap.get("derived_meta", {})),
                ))

        # universe_stats
        for u in universe_list:
            st = universe_stats[u]
            upsert(conn, """
            INSERT INTO universe_stats
            (run_id, universe_type, window_days_bd, foreign_flow_mean, foreign_flow_std, inst_flow_mean, inst_flow_std, computed_at_kst)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(run_id, universe_type, window_days_bd) DO UPDATE SET
              foreign_flow_mean=excluded.foreign_flow_mean,
              foreign_flow_std=excluded.foreign_flow_std,
              inst_flow_mean=excluded.inst_flow_mean,
              inst_flow_std=excluded.inst_flow_std;
            """, (
                run_id, u, cfg.window_days_bd,
                st.get("foreign_flow_mean"), st.get("foreign_flow_std"),
                st.get("inst_flow_mean"), st.get("inst_flow_std"),
                asof_ts
            ))

        # decisions
        for row in decisions_rows:
            upsert(conn, """
            INSERT INTO decisions
            (run_id, universe_type, ticker, horizon_bd, model_rule_version,
             action, nice_score, confidence, expected_ret_pct,
             gates_json, failed_reasons_json, contra_evidence_json, decided_at_kst)
            VALUES (?, ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?)
            ON CONFLICT(run_id, universe_type, ticker, horizon_bd, model_rule_version) DO UPDATE SET
              action=excluded.action,
              nice_score=excluded.nice_score,
              confidence=excluded.confidence,
              gates_json=excluded.gates_json,
              failed_reasons_json=excluded.failed_reasons_json,
              contra_evidence_json=excluded.contra_evidence_json;
            """, (
                row["run_id"], row["universe_type"], row["ticker"], row["horizon_bd"], row["model_rule_version"],
                row["action"], row["nice_score"], row["confidence"], row["expected_ret_pct"],
                safe_json(row["gates"]),
                safe_json(row["failed_reasons"]),
                safe_json(row["contra_evidence"]),
                row["decided_at_kst"],
            ))

    # Human-readable summary (stdout)
    buy_cnt = sum(1 for r in decisions_rows if r["horizon_bd"] == horizons[0] and r["action"] == "BUY")
    print(f"[OK] run_id={run_id} asof={asof} universes={universe_list} horizons={horizons} BUY_count(h={horizons[0]})={buy_cnt}")
    print(f"[INFO] regime={regime.get('regime_reason')} flags={sorted(list(set(integrity_flags_run)))[:12]} ...")


if __name__ == "__main__":
    main()
