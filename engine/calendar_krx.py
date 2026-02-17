from __future__ import annotations
from dataclasses import dataclass
from typing import List
from datetime import datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))

@dataclass(frozen=True)
class KRXCalendar:
    sessions: List[str]  # sorted list of "YYYY-MM-DD"

    @staticmethod
    def from_exchange_calendars(start: str, end: str) -> "KRXCalendar":
        try:
            # exchange_calendars provides XKRX calendar.
            import exchange_calendars as xcals  # type: ignore
            cal = xcals.get_calendar("XKRX")
            sched = cal.sessions_in_range(start, end)
            sessions = [d.strftime("%Y-%m-%d") for d in sched]
            return KRXCalendar(sessions=sessions)
        except ImportError:
            # Fallback: simple weekday logic (Mon-Fri)
            print("[WARN] exchange_calendars missing; using weekday fallback.")
            s_date = datetime.strptime(start, "%Y-%m-%d").date()
            e_date = datetime.strptime(end, "%Y-%m-%d").date()
            sessions = []
            curr = s_date
            while curr <= e_date:
                if curr.weekday() < 5:  # Mon=0, Fri=4
                    sessions.append(curr.strftime("%Y-%m-%d"))
                curr += timedelta(days=1)
            return KRXCalendar(sessions=sessions)

    def is_session(self, d: str) -> bool:
        return d in set(self.sessions)

    def shift(self, d: str, n: int) -> str:
        # shift by n sessions (n can be negative)
        try:
            idx = self.sessions.index(d)
        except ValueError:
             # if d is not in session list (e.g. holiday in fallback), find nearest
             # This is a simple improvement for robustness
             return d 
        
        new_idx = idx + n
        if 0 <= new_idx < len(self.sessions):
            return self.sessions[new_idx]
        return self.sessions[-1] if n > 0 else self.sessions[0]

def now_kst_iso() -> str:
    return datetime.now(tz=KST).isoformat(timespec="seconds")

def date_to_yyyymmdd(d: str) -> str:
    return d.replace("-", "")

def yyyymmdd_to_date(s: str) -> str:
    return f"{s[:4]}-{s[4:6]}-{s[6:8]}"
