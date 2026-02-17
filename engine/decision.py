from __future__ import annotations
from typing import Any, Dict, List
from engine.types import TickerSnapshot

def make_decision(s: TickerSnapshot, decision_cfg: Dict[str, Any], now_kst: str) -> Dict[str, Any]:
    contra: List[str] = []

    if s.gate_status == "BLOCK" or s.nice_score is None:
        return {
            "ticker": s.ticker,
            "action": "REJECT",
            "reason": " | ".join(s.gate_failed_reasons) if s.gate_failed_reasons else "BLOCKED",
            "contra_evidence": s.gate_failed_reasons,
            "expected_ret_5d_pct": None,
            "expected_ret_10d_pct": None,
            "created_at_kst": now_kst
        }

    if s.short_ratio_pct is not None and s.short_ratio_pct > 10:
        contra.append("ELEVATED_SHORT_RATIO")
    if s.foreign_net_buy_krw is not None and s.foreign_net_buy_krw < 0:
        contra.append("FOREIGN_NET_SELL")
    if s.inst_net_buy_krw is not None and s.inst_net_buy_krw < 0:
        contra.append("INST_NET_SELL")

    score = float(s.nice_score or 0.0)
    if score >= decision_cfg["buy_score"]:
        action = "BUY"
        reason = f"Score>=BUY({score:.1f}) with foreign_z={s.foreign_z:.2f} inst_z={s.inst_z:.2f}"
    elif score >= decision_cfg["watch_score"]:
        action = "WATCH"
        reason = f"Score>=WATCH({score:.1f})"
    else:
        action = "REJECT"
        reason = f"Score<{decision_cfg['watch_score']}({score:.1f})"

    return {
        "ticker": s.ticker,
        "action": action,
        "reason": reason,
        "contra_evidence": contra,
        "expected_ret_5d_pct": None,   # optional: add model-implied expected return later
        "expected_ret_10d_pct": None,
        "created_at_kst": now_kst
    }
