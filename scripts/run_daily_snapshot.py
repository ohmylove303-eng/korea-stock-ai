from __future__ import annotations
import argparse
import json
import math
import sys
import os
from typing import Dict, List, Tuple, Optional
import numpy as np
import pandas as pd
from pykrx import stock
import FinanceDataReader as fdr

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.calendar_krx import KRXCalendar, now_kst_iso, date_to_yyyymmdd
from engine.db_sqlite import SQLiteStore
from engine.types import RunContext, TickerSnapshot

SHORT_CUTOVER_DATE = "2025-03-31"

def safe_float(x) -> Optional[float]:
    try:
        if x is None:
            return None
        if isinstance(x, (float, int, np.floating, np.integer)):
            if math.isnan(float(x)):
                return None
        return float(x)
    except Exception:
        return None

# ---------- Indicators ----------
def rsi(series: pd.Series, period: int = 14) -> Optional[float]:
    if series is None or len(series) < period + 1:
        return None
    delta = series.diff()
    up = delta.clip(lower=0).rolling(period).mean()
    down = (-delta.clip(upper=0)).rolling(period).mean()
    rs = up / down.replace(0, np.nan)
    val = 100 - (100 / (1 + rs))
    return safe_float(val.iloc[-1])

def macd_hist(series: pd.Series, fast=12, slow=26, signal=9) -> Optional[float]:
    if series is None or len(series) < slow + signal + 5:
        return None
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line
    return safe_float(hist.iloc[-1])

def vcp_placeholder(series: pd.Series, vol: pd.Series) -> Optional[float]:
    if series is None or len(series) < 60:
        return None
    try:
        s1 = series.pct_change().rolling(20).std().iloc[-1]
        s2 = series.pct_change().rolling(60).std().iloc[-1]
        if safe_float(s1) is None or safe_float(s2) is None or s2 == 0:
            return None
        return safe_float(max(0.0, min(100.0, (1 - (s1 / s2)) * 100)))
    except Exception:
        return None

def atr(high: pd.Series, low: pd.Series, close: pd.Series, n: int = 14) -> Optional[float]:
    if len(close) < n + 1:
        return None
    try:
        prev_close = close.shift(1)
        tr1 = high - low
        tr2 = (high - prev_close).abs()
        tr3 = (low - prev_close).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        val = tr.rolling(n).mean().iloc[-1]
        return safe_float(val)
    except Exception as e:
        print(f"ATR Calculation Error: {e}")
        return None

# ---------- Collectors ----------
def get_top_by_trading_value_fallback(asof_date: str, market: str, top_n: int) -> List[str]:
    ymd = date_to_yyyymmdd(asof_date)
    try:
        # Use Market Cap API which is more stable for Trading Value
        df = stock.get_market_cap_by_ticker(ymd, market=market)
        # df columns: 시가총액, 거래량, 거래대금, 상장주식수
        if "거래대금" not in df.columns:
            df["거래대금"] = df["거래량"] # fallback
        top = df.sort_values("거래대금", ascending=False).head(top_n)
        return list(top.index.astype(str))
    except Exception as e:
        print(f"[WARN] Universe fetch failed {market}: {e}")
        return []

def build_universe(asof_date: str, live_n: int, bt_n: int) -> Tuple[List[str], List[str]]:
    kospi = get_top_by_trading_value_fallback(asof_date, "KOSPI", 300)
    kosdaq = get_top_by_trading_value_fallback(asof_date, "KOSDAQ", 300)
    if not kospi and not kosdaq:
        return (["005930", "000660", "373220"], ["005930", "000660", "373220"])
    merged = kospi + [t for t in kosdaq if t not in kospi]
    return merged[:live_n], merged[:bt_n]

def get_usdkrw_close(asof_date: str) -> Optional[float]:
    try:
        df = fdr.DataReader("USD/KRW", asof_date, asof_date)
        if df is None or df.empty:
            return None
        return safe_float(df.iloc[-1][0])
    except Exception:
        return None

# ---------- Logic ----------
def zscore(x: float, mean: float, std: float) -> Optional[float]:
    if std is None or std == 0 or x is None:
        return None
    return (x - mean) / std

def decision_gate(snapshot: Dict) -> Tuple[str, List[str], List[Dict]]:
    failed = []
    contra = []
    flags = snapshot.get("integrity_flags") or []
    if flags:
        contra.append({"type": "INTEGRITY_FLAGS", "flags": flags})
    if snapshot.get("kospi_regime") == "bear":
        failed.append("REGIME_BEAR")
    usdkrw = snapshot.get("usdkrw")
    if usdkrw is None:
        failed.append("MISSING_USDKRW")
    elif usdkrw >= 1450:
        contra.append({"type": "FX_RISK", "usdkrw": usdkrw})
    tv = snapshot.get("trading_value_krw")
    if tv is None:
        failed.append("MISSING_TRADING_VALUE")
    elif tv < 10_000_000_000:
        failed.append("LOW_LIQUIDITY")
    if "REGIME_BEAR" in failed:
        return "BLOCK", failed, contra
    if failed:
        return "CAUTION", failed, contra
    return "PASS", [], contra

def compute_nice_score(snapshot: Dict) -> Tuple[Optional[int], Optional[int]]:
    parts = []
    fz = snapshot.get("foreign_z")
    iz = snapshot.get("inst_z")
    if fz is not None:
        parts.append(max(-3, min(3, fz)) / 3 * 30 + 30)
    else:
        parts.append(30)
    if iz is not None:
        parts.append(max(-3, min(3, iz)) / 3 * 15 + 15)
    else:
        parts.append(15)
    r = snapshot.get("rsi_14")
    mh = snapshot.get("macd_hist")
    tech = 0.0
    if r is not None:
        tech += max(0, min(100, r)) / 100 * 20
    if mh is not None:
        tech += (1 if mh > 0 else 0) * 20
    base = sum(parts) + tech
    score = int(max(0, min(100, round(base))))
    return score, score

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--db", default="db.sqlite3")
    p.add_argument("--asof", required=True)
    p.add_argument("--live_n", type=int, default=150)
    p.add_argument("--bt_n", type=int, default=300)
    p.add_argument("--window_days", type=int, default=40)
    p.add_argument("--horizons", default="5,10")
    p.add_argument("--rule_version", default="v1.1")
    p.add_argument("--calendar_start", default="2018-01-01")
    p.add_argument("--calendar_end", default="2030-12-31")
    args = p.parse_args()

    cal = KRXCalendar.from_exchange_calendars(args.calendar_start, args.calendar_end)
    asof = args.asof
    window_end = asof
    window_start = cal.shift(asof, -args.window_days + 1)
    horizons = [int(h) for h in args.horizons.split(",")]
    run_id = f"KR|EOD|{asof}|live{args.live_n}+bt{args.bt_n}|h={args.horizons}|rule={args.rule_version}"
    
    store = SQLiteStore(args.db)
    conn = store.connect()
    
    try:
        conn.execute("BEGIN IMMEDIATE;")
        usdkrw = get_usdkrw_close(asof)
        
        s_date_20 = cal.shift(asof, -20)
        ymd_s = date_to_yyyymmdd(s_date_20)
        ymd_e = date_to_yyyymmdd(asof)
        try:
            k_df = stock.get_index_ohlcv_by_date(ymd_s, ymd_e, "1001")
            ret20 = (k_df["종가"].iloc[-1]/k_df["종가"].iloc[0] - 1)*100
        except:
            ret20 = None
        k_regime = "neutral"
        if ret20 is not None:
             if ret20 > 3: k_regime = "bull"
             elif ret20 < -3: k_regime = "bear"
             
        run_ctx = RunContext(
            run_id=run_id, market="KR", run_type="EOD", asof_date=asof, asof_ts_kst=now_kst_iso(),
            universe_live_n=args.live_n, universe_bt_n=args.bt_n, horizons_csv=args.horizons,
            model_rule_version=args.rule_version, short_cutover_date=SHORT_CUTOVER_DATE,
            notes=None, created_at_kst=now_kst_iso()
        )
        store.upsert_run(conn, run_ctx)
        
        live_u, bt_u = build_universe(asof, args.live_n, args.bt_n)
        all_sets = [("live150", live_u), ("bt300", bt_u)]
        snapshots_by_uni = {"live150": [], "bt300": []}
        
        for uni_name, uni in all_sets:
            for t in uni:
                ymd_ws = date_to_yyyymmdd(window_start)
                ymd_we = date_to_yyyymmdd(window_end)
                try:
                    df = stock.get_market_ohlcv_by_date(ymd_ws, ymd_we, t)
                    if df is None or df.empty:
                        raise ValueError("Empty OHLCV")
                    print(f"[{t}] DF Len: {len(df)} (Range: {ymd_ws}~{ymd_we})")
                    close = float(df["종가"].iloc[-1])
                    vol = float(df["거래량"].iloc[-1])
                    tv = float(df["거래대금"].iloc[-1]) if "거래대금" in df.columns else (close*vol)
                    
                    r14 = rsi(df["종가"], 14)
                    mh = macd_hist(df["종가"])
                    vcp = vcp_placeholder(df["종가"], df["거래량"])
                    atr14 = atr(df["고가"], df["저가"], df["종가"], 14) 
                except Exception as e:
                    print(f"[{t}] Error calculating stats: {e}")
                    close=vol=tv=r14=mh=vcp=atr14=None
                
                try:
                    fdf = stock.get_market_trading_value_by_date(ymd_ws, ymd_we, t)
                    f_net = float(fdf["외국인"].sum()) if "외국인" in fdf.columns else None
                    i_net = float(fdf["기관합계"].sum()) if "기관합계" in fdf.columns else None
                except:
                    f_net = i_net = None
                
                integrity = []
                if close is None: integrity.append("MISSING_OHLCV")
                if f_net is None: integrity.append("MISSING_FLOW")
                
                f_pct = (f_net/tv*100) if (f_net is not None and tv) else None
                i_pct = (i_net/tv*100) if (i_net is not None and tv) else None
                
                ts = TickerSnapshot(
                    run_id=run_id, ticker=t, market_segment=None, universe_type=uni_name,
                    asof_date=asof, asof_ts_kst=now_kst_iso(), window_days=args.window_days,
                    window_start_date=window_start, window_end_date=window_end,
                    close_px=close, volume=vol, trading_value_krw=tv,
                    rsi_14=r14, macd_hist=mh, vcp_score=vcp, atr_14=atr14,
                    foreign_net_buy_krw=f_net, inst_net_buy_krw=i_net,
                    foreign_flow_pct=f_pct, inst_flow_pct=i_pct,
                    short_balance_ratio=None, short_regime_tag=("POST" if asof >= SHORT_CUTOVER_DATE else "PRE"),
                    usdkrw=usdkrw, kospi_ret_20d=ret20, kospi_regime=k_regime,
                    regime_reason={"rule": "20d_ret", "val": ret20},
                    source_tags=["PYKRX"], integrity_flags=integrity, created_at_kst=now_kst_iso()
                )
                snapshots_by_uni[uni_name].append(ts)
                
            valid_f = [s.foreign_flow_pct for s in snapshots_by_uni[uni_name] if s.foreign_flow_pct is not None]
            valid_i = [s.inst_flow_pct for s in snapshots_by_uni[uni_name] if s.inst_flow_pct is not None]
            
            def calc_ms(v):
                if not v: return 0.0, 0.0
                a = np.array(v)
                return float(a.mean()), float(a.std(ddof=0))
            
            fm, fs = calc_ms(valid_f)
            im, i_std = calc_ms(valid_i)
            
            store.upsert_universe_stats(
                conn, asof, uni_name, args.window_days, fm, fs, im, i_std, 0.0, 0.0, now_kst_iso()
            )
            
            for s in snapshots_by_uni[uni_name]:
                s.foreign_z = zscore(s.foreign_flow_pct, fm, fs)
                s.inst_z = zscore(s.inst_flow_pct, im, i_std)
                gate, failed, contra = decision_gate(s.__dict__)
                nice, conf = compute_nice_score(s.__dict__)
                store.upsert_ticker_snapshots(conn, [s])
                for h in horizons:
                    action = "BUY" if (gate == "PASS" and nice >= 70) else "WATCH"
                    if gate == "BLOCK": action = "REJECT"
                    store.upsert_decision(
                        conn, run_id, s.ticker, uni_name, h,
                        gate, action, nice, conf, failed, contra,
                        None, args.rule_version, None, now_kst_iso()
                    )
        conn.commit()
        print(f"OK: run {run_id} complete.")
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

if __name__ == "__main__":
    main()
