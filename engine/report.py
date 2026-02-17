from __future__ import annotations
from typing import Any, Dict, List, Tuple
import json

def render_top3_report(asof_date: str, run_id: str, top3: List[Tuple[str,int]], patch: Dict[str, Any]) -> str:
    lines = []
    lines.append(f"# Evidence Capsule Post-Mortem Report")
    lines.append(f"- asof_date: {asof_date}")
    lines.append(f"- run_id: {run_id}")
    lines.append("")
    lines.append("## TOP-3 error_type")
    for et, cnt in top3:
        lines.append(f"- {et}: {cnt}")
    lines.append("")
    lines.append("## Proposed vNext Patch (DRAFT, approval required)")
    lines.append("```json")
    lines.append(json.dumps(patch, ensure_ascii=False, indent=2))
    lines.append("```")
    return "\n".join(lines)
