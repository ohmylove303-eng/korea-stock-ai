from __future__ import annotations
from typing import Any, Dict, List, Tuple
import json
from collections import Counter

ERROR_TYPES = [
    "REGIME_SHIFT",
    "FLOW_REVERSAL",
    "CROWDED_UNWIND",
    "DATA_FAULT",
    "FALSE_BREAKOUT",
    "MEAN_REVERSION_TRAP",
    "GAP_RISK",
    "SHORT_SQUEEZE_MISS",
    "OTHER"
]

def classify_error(action: str, realized_ret_pct: float, alpha_pct: float, snapshot: Dict[str, Any]) -> str:
    # Rule-based baseline (upgradeable)
    if snapshot.get("kospi_trend_20d_pct") is not None and snapshot["kospi_trend_20d_pct"] < -3:
        return "REGIME_SHIFT"
    if snapshot.get("foreign_net_buy_krw") is not None and snapshot["foreign_net_buy_krw"] < 0 and action == "BUY":
        return "FLOW_REVERSAL"
    if snapshot.get("short_ratio_pct") is not None and snapshot["short_ratio_pct"] > 15 and realized_ret_pct < 0:
        return "CROWDED_UNWIND"
    return "OTHER"

def top_k_errors(rows: List[Dict[str, Any]], k: int = 3) -> List[Tuple[str, int]]:
    c = Counter([r["error_type"] for r in rows])
    return c.most_common(k)

def propose_upgrade_patch(top_errors: List[Tuple[str,int]], current_cfg: Dict[str, Any]) -> Dict[str, Any]:
    """
    Return JSON patch-style proposal (do not auto-apply).
    """
    patch: Dict[str, Any] = {"gates": {}, "scoring": {}, "notes": []}
    for et, cnt in top_errors:
        if et == "REGIME_SHIFT":
            patch["gates"]["kospi_trend_block_pct"] = max(current_cfg["gates"]["kospi_trend_block_pct"], -2.0)
            patch["notes"].append("REGIME_SHIFT↑ → tighten kospi regime block threshold")
        if et == "CROWDED_UNWIND":
            patch["gates"]["max_short_ratio_pct"] = min(current_cfg["gates"]["max_short_ratio_pct"], 12.0)
            patch["notes"].append("CROWDED_UNWIND↑ → lower max_short_ratio_pct")
        if et == "FLOW_REVERSAL":
            patch["notes"].append("FLOW_REVERSAL↑ → add 'foreign_3day_consecutive' gate in next version")
    return patch
