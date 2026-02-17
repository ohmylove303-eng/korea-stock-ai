#!/usr/bin/env python3
# score_outcomes.py
# Requirements:
#   pip install pykrx pandas numpy
# Optional:
#   pip install exchange-calendars
#
# Usage:
#   python score_outcomes.py --db ./kstock.db --asof 20260205 --horizon 5,10
#
# Cron (KST 18:25):
#   25 18 * * 1-5 /usr/bin/python3 /path/score_outcomes.py --db /path/kstock.db --horizon 5,10

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import json
import sqlite3
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from pykrx import stock

KST = dt.timezone(dt.timedelta(hours=9))


def now_kst_iso() -> str:
    return dt.datetime.now(tz=KST).isoformat(timespec="seconds")


def safe_json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def business_day_shift(asof: str, n_bd: int) -> str:
    d0 = dt.datetime.strptime(asof, "%Y%m%d").date()
    try:
        import exchange_calendars as xc  # type: ignore
        cal = xc.get_calendar("XKRX")
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


def fetch_one_close(ticker: str, date: str) -> Tuple[Optional[float], List[str]]:
    flags = []
    try:
        df = stock.get_market_ohlcv_by_date(date, date, ticker)
        if df is None or len(df) == 0 or "종가" not in df.columns:
            return None, ["CLOSE_EMPTY"]
        return float(df["종가"].iloc[-1]), flags
    except Exception:
        return None, ["CLOSE_ERROR"]


def fetch_kospi_close(date: str) -> Tuple[Optional[float], List[str]]:
    flags = []
    try:
        try:
            df = stock.get_index_ohlcv_by_date(date, date, "1001")
        except Exception:
            df = stock.get_index_ohlcv_by_date(date, date, "KOSPI")
        if df is None or len(df) == 0 or "종가" not in df.columns:
            return None, ["KOSPI_CLOSE_EMPTY"]
        return float(df["종가"].iloc[-1]), flags
    except Exception:
        return None, ["KOSPI_CLOSE_ERROR"]


def classify_error(action: str, realized_ret: float,
                   meta: Dict[str, Any],
                   asof: str, end: str) -> Tuple[Optional[str], Dict[str, Any]]:
    """
    Deterministic, evidence-based classification.
    No story-telling; only use stored fields or re-queried objective series.
    """
    detail: Dict[str, Any] = {"asof": asof, "end": end, "rules": "v1.1"}

    if action != "BUY":
        # For REJECT/WATCH, you may also score "missed gains" later. Keep minimal now.
        return None, detail

    if realized_ret >= 0:
        return None, detail

    # 1) data fault
    flags = meta.get("integrity_flags", [])
    if any(x.endswith("_ERROR") for x in flags) or "FLOW_ERROR" in flags:
        return "DATA_FAULT", {**detail, "flags": flags}

    # 2) regime shift: compare KOSPI return
    kos0, f0 = fetch_kospi_close(asof)
    kos1, f1 = fetch_kospi_close(end)
    if kos0 is not None and kos1 is not None and kos0 != 0:
        kos_ret = 100 * (kos1 / kos0 - 1)
        detail["kospi_ret_pct"] = kos_ret
        # If KOSPI crashed, treat as regime shift first
        if kos_ret <= -3.0:
            return "REGIME_SHIFT", detail

    # 3) crowded unwind: short_ratio too high or increased
    sr = meta.get("short_ratio")
    sr_chg = meta.get("short_ratio_chg_5d")
    if sr is not None and sr >= 15:
        return "CROWDED_UNWIND", {**detail, "short_ratio": sr}
    if sr_chg is not None and sr_chg >= 3:
        return "CROWDED_UNWIND", {**detail, "short_ratio_chg_5d": sr_chg}

    # 4) flow reversal (best-effort): re-check net flow from asof+1..end
    try:
        start = business_day_shift(asof, 1)
        df = stock.get_market_trading_value_by_date(start, end, meta["ticker"])
        if df is not None and len(df) > 0 and "외국인" in df.columns:
            post_foreign = float(df["외국인"].sum())
            pre_foreign = meta.get("foreign_net_buy_krw")
            detail["post_foreign_net"] = post_foreign
            detail["pre_foreign_net"] = pre_foreign
            if pre_foreign is not None and post_foreign < 0:
                return "FLOW_REVERSAL", detail
    except Exception:
        detail["flow_reversal_check"] = "unavailable"

    # 5) fallback
    return "UNKNOWN", detail


def generate_upgrade_proposal(top_errors: List[Tuple[str, int, float]]) -> Tuple[str, Dict[str, Any]]:
    """
    Turn error distribution into incremental changes (no deletion).
    Returns markdown + proposed_changes_json
    """
    changes: Dict[str, Any] = {"version_from": "v1.1", "version_to": "v1.2_proposed", "overrides": []}

    md = []
    md.append("# v1.1 → v1.2 (Proposed) Upgrade Memo")
    md.append("")
    md.append("## TOP-3 error_type (count, avg_alpha_loss)")
    for et, cnt, loss in top_errors:
        md.append(f"- **{et}**: {cnt}건, 평균 알파 손실 {loss:.2f}%p")

    md.append("")
    md.append("## Proposed incremental overrides (no deletion)")
    for et, _, _ in top_errors:
        if et == "REGIME_SHIFT":
            md.append("- REGIME_SHIFT: Palantir Gate 강화 (지수/환율 결측 시 BUY 차단)")
            changes["overrides"].append({
                "path": "gates.regime",
                "change": "If USDKRW missing OR kospi_regime=bear -> force REJECT",
                "why": "Regime invalidates flow signal",
            })
        elif et == "FLOW_REVERSAL":
            md.append("- FLOW_REVERSAL: Flow persistence 확인 게이트 추가 (3일 연속/추세 확인)")
            changes["overrides"].append({
                "path": "gates.flow_persistence",
                "change": "Require foreign_flow_pct window split positive (last 3bd >= 0)",
                "why": "Avoid one-off spike",
            })
        elif et == "CROWDED_UNWIND":
            md.append("- CROWDED_UNWIND: short_ratio 상한을 레짐별로 더 보수적으로(예: 12%)")
            changes["overrides"].append({
                "path": "gates.short",
                "change": "short_ratio_max 15 -> 12 in neutral/bear; add short_ratio_chg gate",
                "why": "Crowded unwind risk",
            })
        elif et == "DATA_FAULT":
            md.append("- DATA_FAULT: integrity_grade=CAUTION도 BUY 금지로 격상")
            changes["overrides"].append({
                "path": "integrity.policy",
                "change": "Only PASS can BUY",
                "why": "Reduce silent data corruption",
            })
        else:
            md.append(f"- {et}: UNKNOWN bucket → 필요한 신규 필드(이벤트/공시 등) 후보로 올림")
            changes["overrides"].append({
                "path": "features.todo",
                "change": f"Add feature candidates for {et}",
                "why": "Need more evidence fields",
            })

    md.append("")
    md.append("## Safety note")
    md.append("- 이 제안서는 **기존 룰 삭제 없이** override로만 적용합니다.")
    md.append("- 다음 2주간 v1.1/v1.2를 동시에 저장(dual-write) 후 비교 가능합니다.")

    return "\n".join(md), changes


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", required=True, help="SQLite DB path, e.g., ./kstock.db")
    parser.add_argument("--asof", default=None, help="YYYYMMDD, default=today (scorer uses DB pending rows anyway)")
    parser.add_argument("--horizon", default="5,10", help="CSV business-day horizons")
    args = parser.parse_args()

    horizons = [int(x.strip()) for x in args.horizon.split(",") if x.strip()]
    scored_at = now_kst_iso()

    with sqlite_tx(args.db) as conn:
        # 1) Find decisions that do not have outcomes yet (by asof_date from runs + run_id join)
        # We'll use ticker_snapshots.window_end_date as asof_date and decisions.model_rule_version.
        q = """
        SELECT
          r.asof_date,
          d.run_id,
          d.universe_type,
          d.ticker,
          d.horizon_bd,
          d.model_rule_version,
          d.action,
          ts.price_close AS entry_close,
          ts.foreign_net_buy_krw,
          ts.short_ratio,
          ts.short_ratio_chg_5d,
          ts.integrity_flags_json
        FROM decisions d
        JOIN runs r ON r.run_id = d.run_id
        JOIN ticker_snapshots ts
          ON ts.run_id = d.run_id AND ts.universe_type = d.universe_type AND ts.ticker = d.ticker AND ts.window_days_bd = r.window_days_bd
        LEFT JOIN outcomes o
          ON o.asof_date = r.asof_date AND o.universe_type = d.universe_type AND o.ticker = d.ticker
         AND o.horizon_bd = d.horizon_bd AND o.model_rule_version = d.model_rule_version
        WHERE o.asof_date IS NULL
          AND d.horizon_bd IN ({})
        """.format(",".join(["?"] * len(horizons)))
        rows = conn.execute(q, tuple(horizons)).fetchall()

        if not rows:
            print("[OK] No pending outcomes to score.")
            return

        # 2) Score each row if exit date (asof + horizon_bd) is in the past.
        # We compute end_date as business_day_shift(asof_date, horizon_bd)
        # If end_date > today_bd, skip.
        today = dt.datetime.now(tz=KST).strftime("%Y%m%d")

        scored = 0
        errors: Dict[str, List[float]] = {}  # error_type -> alpha loss list (negative is bad)
        for (asof_date, run_id, universe_type, ticker, horizon_bd, ver, action, entry_close,
             foreign_net_buy_krw, short_ratio, short_ratio_chg_5d, integrity_flags_json) in rows:

            end_date = business_day_shift(asof_date, int(horizon_bd))
            if end_date > today:
                continue

            exit_close, f_exit = fetch_one_close(ticker, end_date)
            if entry_close is None or exit_close is None or entry_close == 0:
                # record as DATA_FAULT
                realized = None
                alpha = None
                kos_ret = None
                error_type = "DATA_FAULT"
                error_detail = {"flags_exit": f_exit, "entry_close": entry_close, "exit_close": exit_close}
            else:
                realized = 100 * (float(exit_close) / float(entry_close) - 1)

                kos0, _ = fetch_kospi_close(asof_date)
                kos1, _ = fetch_kospi_close(end_date)
                kos_ret = None
                if kos0 is not None and kos1 is not None and kos0 != 0:
                    kos_ret = 100 * (float(kos1) / float(kos0) - 1)
                alpha = realized - kos_ret if kos_ret is not None else None

                meta = {
                    "ticker": ticker,
                    "foreign_net_buy_krw": foreign_net_buy_krw,
                    "short_ratio": short_ratio,
                    "short_ratio_chg_5d": short_ratio_chg_5d,
                    "integrity_flags": json.loads(integrity_flags_json or "[]"),
                }
                error_type, error_detail = classify_error(action, realized, meta, asof_date, end_date)

            label = None
            if realized is not None:
                if realized > 0:
                    label = "WIN"
                elif realized < 0:
                    label = "LOSS"
                else:
                    label = "FLAT"

            # UPSERT into outcomes
            conn.execute("""
            INSERT INTO outcomes
            (asof_date, universe_type, ticker, horizon_bd, model_rule_version,
             entry_close, exit_close, realized_ret_pct, kospi_ret_pct, alpha_vs_kospi_pct,
             label, error_type, error_detail_json, scored_at_kst, source_tags_json, integrity_flags_json)
            VALUES (?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?)
            ON CONFLICT(asof_date, universe_type, ticker, horizon_bd, model_rule_version) DO UPDATE SET
              exit_close=excluded.exit_close,
              realized_ret_pct=excluded.realized_ret_pct,
              alpha_vs_kospi_pct=excluded.alpha_vs_kospi_pct,
              error_type=excluded.error_type,
              error_detail_json=excluded.error_detail_json,
              scored_at_kst=excluded.scored_at_kst;
            """, (
                asof_date, universe_type, ticker, int(horizon_bd), ver,
                entry_close, exit_close, realized, kos_ret, alpha,
                label, error_type, safe_json(error_detail), scored_at,
                safe_json({"prices": "KRX_PYKRX", "kospi": "KRX_PYKRX"}),
                safe_json(f_exit),
            ))
            scored += 1

            if error_type and alpha is not None:
                errors.setdefault(error_type, []).append(float(alpha))

            # Update fractal_cases (library grows only when outcome known)
            # Need signature from ticker_snapshots
            sig_row = conn.execute("""
              SELECT fractal_signature FROM ticker_snapshots
              WHERE run_id=? AND universe_type=? AND ticker=? LIMIT 1
            """, (run_id, universe_type, ticker)).fetchone()
            if sig_row and sig_row[0]:
                conn.execute("""
                INSERT OR IGNORE INTO fractal_cases
                (asof_date, ticker, fractal_signature, horizon_bd, realized_ret_pct, alpha_vs_kospi_pct)
                VALUES (?, ?, ?, ?, ?, ?)
                """, (asof_date, ticker, sig_row[0], int(horizon_bd), realized, alpha))

        # 3) error_type TOP-3 report
        top = []
        for et, alphas in errors.items():
            if not alphas:
                continue
            # Use avg negative alpha as "impact". If alpha is negative, loss is -alpha.
            avg_loss = float(np.mean([-a for a in alphas if a is not None])) if len(alphas) > 0 else 0.0
            top.append((et, len(alphas), avg_loss))
        top.sort(key=lambda x: (x[1] * x[2]), reverse=True)
        top3 = top[:3]

        print(f"[OK] scored={scored} pending={len(rows)} top3={top3}")

        # 4) v1.1 upgrade proposal auto-generate (stored per latest run_id that had scoring)
        if top3:
            md, changes = generate_upgrade_proposal(top3)
            # pick a run_id to attach: use the max run_id lexicographically is meaningless; use last processed run_id from loop if available.
            # We'll attach to the most recent run in DB.
            last_run = conn.execute("SELECT run_id FROM runs ORDER BY asof_ts_kst DESC LIMIT 1").fetchone()
            attach_run_id = last_run[0] if last_run else "unknown"

            conn.execute("""
            INSERT INTO upgrade_proposals (run_id, generated_at_kst, top_errors_json, proposal_md, proposed_changes_json)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET
              generated_at_kst=excluded.generated_at_kst,
              top_errors_json=excluded.top_errors_json,
              proposal_md=excluded.proposal_md,
              proposed_changes_json=excluded.proposed_changes_json;
            """, (
                attach_run_id, scored_at, safe_json(top3), md, safe_json(changes)
            ))

            # Also write a local file for humans
            fn = f"upgrade_proposal_{dt.datetime.now(tz=KST).strftime('%Y%m%d_%H%M')}.md"
            with open(fn, "w", encoding="utf-8") as f:
                f.write(md)
            print(f"[REPORT] wrote {fn}")


if __name__ == "__main__":
    main()
