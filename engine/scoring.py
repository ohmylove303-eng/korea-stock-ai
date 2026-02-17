from __future__ import annotations
from typing import Dict, List, Tuple, Optional

from engine.types import TickerSnapshot

def gate_and_score(s: TickerSnapshot, gates: Dict, weights: Dict) -> None:
    reasons: List[str] = []
    status = "PASS"

    # 결측 강등: 핵심 수급이 없으면 BLOCK
    if s.foreign_z is None:
        status = "BLOCK"
        reasons.append("MISSING_FOREIGN_Z")
    if s.trading_value_krw is None or s.trading_value_krw < gates["min_trading_value_krw"]:
        status = "BLOCK"
        reasons.append("LOW_LIQUIDITY_TRADING_VALUE")

    # 공매도 과열 차단(있을 때만)
    if s.short_ratio_pct is not None and s.short_ratio_pct > gates["max_short_ratio_pct"]:
        status = "BLOCK"
        reasons.append("SHORT_RATIO_TOO_HIGH")

    # FX 필수 옵션: 없으면 CAUTION/BLOCK
    if gates.get("require_fx", True) and s.usdkrw is None:
        status = "CAUTION" if status != "BLOCK" else status
        reasons.append("MISSING_USDKRW")

    # KOSPI 추세가 너무 나쁘면 BLOCK(옵션)
    if s.kospi_trend_20d_pct is not None and s.kospi_trend_20d_pct <= gates["kospi_trend_block_pct"]:
        status = "BLOCK"
        reasons.append("KOSPI_REGIME_BEAR_BLOCK")

    s.gate_status = status
    s.gate_failed_reasons = reasons

    # Score: gate PASS/CAUTION만 산출, BLOCK이면 None
    if status == "BLOCK":
        s.nice_score = None
        s.confidence = 0.0
        return

    # 기술점수(legacy) - 없으면 0
    tech = 0.0
    if s.rsi_14 is not None:
        tech += min(max((s.rsi_14 - 50.0) / 50.0, 0.0), 1.0) * 100.0
    if s.macd_hist_12_26_9 is not None:
        tech += 50.0  # placeholder: sign-based scaling can be added
    tech = min(tech, 100.0)

    regime_bonus = 0.0
    if s.kospi_trend_20d_pct is not None:
        regime_bonus = min(max((s.kospi_trend_20d_pct + 5.0) / 10.0, 0.0), 1.0) * 100.0

    score = 0.0
    score += (s.foreign_z or 0.0) * weights["w_foreign_z"]
    score += (s.inst_z or 0.0) * weights["w_inst_z"]
    score += (tech / 100.0) * weights["w_tech"]
    score += (regime_bonus / 100.0) * weights["w_regime"]

    # 안정화: 0~100 클램프
    score = max(0.0, min(100.0, score))
    s.nice_score = score

    # confidence: 결측/CAUTION이면 감점
    conf = score
    if "MISSING_USDKRW" in reasons:
        conf *= 0.8
    s.confidence = max(0.0, min(100.0, conf))
