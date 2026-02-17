from __future__ import annotations
from typing import Dict, List, Tuple, Optional
import math
import numpy as np
import pandas as pd

from engine.types import TickerSnapshot

def safe_div(a: Optional[float], b: Optional[float]) -> Optional[float]:
    if a is None or b is None or b == 0:
        return None
    return a / b

def compute_flow_norm(s: TickerSnapshot) -> None:
    # market cap ratio (%)
    if s.foreign_net_buy_krw is not None and s.market_cap_krw:
        s.foreign_flow_mcap_pct = (s.foreign_net_buy_krw / s.market_cap_krw) * 100.0
    if s.inst_net_buy_krw is not None and s.market_cap_krw:
        s.inst_flow_mcap_pct = (s.inst_net_buy_krw / s.market_cap_krw) * 100.0

    # trading value ratio (%)
    if s.foreign_net_buy_krw is not None and s.trading_value_krw:
        s.foreign_flow_tval_pct = (s.foreign_net_buy_krw / s.trading_value_krw) * 100.0
    if s.inst_net_buy_krw is not None and s.trading_value_krw:
        s.inst_flow_tval_pct = (s.inst_net_buy_krw / s.trading_value_krw) * 100.0

def zscore(values: List[float]) -> Tuple[float, float]:
    arr = np.array(values, dtype=float)
    mean = float(arr.mean()) if len(arr) else 0.0
    std = float(arr.std(ddof=0)) if len(arr) else 0.0
    return mean, std

def apply_zscores(snapshots: List[TickerSnapshot]) -> Dict[str, Tuple[float, float, int]]:
    """
    Compute universe mean/std for primary normalization (mcap_pct) and
    store to DB for reproducibility. Then apply z.
    """
    fvals = [s.foreign_flow_mcap_pct for s in snapshots if s.foreign_flow_mcap_pct is not None]
    ivals = [s.inst_flow_mcap_pct for s in snapshots if s.inst_flow_mcap_pct is not None]

    f_mean, f_std = zscore([float(x) for x in fvals])
    i_mean, i_std = zscore([float(x) for x in ivals])

    for s in snapshots:
        if s.foreign_flow_mcap_pct is not None and f_std > 0:
            s.foreign_z = (float(s.foreign_flow_mcap_pct) - f_mean) / f_std
        if s.inst_flow_mcap_pct is not None and i_std > 0:
            s.inst_z = (float(s.inst_flow_mcap_pct) - i_mean) / i_std

    stats = {
        "foreign_flow_mcap_pct": (f_mean, f_std, len(fvals)),
        "inst_flow_mcap_pct": (i_mean, i_std, len(ivals))
    }
    return stats
