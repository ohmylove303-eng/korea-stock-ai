from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

JSONDict = Dict[str, Any]

@dataclass
class RunContext:
    run_id: str
    market: str
    run_type: str
    asof_date: str
    asof_ts_kst: str
    universe_live_n: int
    universe_bt_n: int
    horizons_csv: str
    model_rule_version: str
    short_cutover_date: str
    notes: Optional[str]
    created_at_kst: str

@dataclass
class TickerSnapshot:
    run_id: str
    ticker: str
    market_segment: Optional[str]
    universe_type: str
    asof_date: str
    asof_ts_kst: str

    window_days: int
    window_start_date: str
    window_end_date: str

    close_px: Optional[float] = None
    volume: Optional[float] = None
    trading_value_krw: Optional[float] = None

    rsi_14: Optional[float] = None
    macd_hist: Optional[float] = None
    vcp_score: Optional[float] = None
    atr_14: Optional[float] = None

    foreign_net_buy_krw: Optional[float] = None
    inst_net_buy_krw: Optional[float] = None

    foreign_flow_pct: Optional[float] = None
    inst_flow_pct: Optional[float] = None
    foreign_z: Optional[float] = None
    inst_z: Optional[float] = None

    short_balance_ratio: Optional[float] = None
    short_regime_tag: Optional[str] = None

    usdkrw: Optional[float] = None
    kospi_ret_20d: Optional[float] = None
    kospi_regime: Optional[str] = None
    regime_reason: Optional[Dict] = None

    source_tags: Optional[List[str]] = None
    integrity_flags: Optional[List[str]] = None
    created_at_kst: str = ""

    def __post_init__(self):
        if self.integrity_flags is None:
            self.integrity_flags = []
