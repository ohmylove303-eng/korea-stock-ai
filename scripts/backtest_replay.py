from __future__ import annotations
import argparse
from typing import List
import sys
import os
import subprocess

# Ensure engine is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.calendar_krx import KRXCalendar

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--db", default="db.sqlite3")
    p.add_argument("--start", required=True, help="YYYY-MM-DD")
    p.add_argument("--end", required=True, help="YYYY-MM-DD")
    p.add_argument("--universe", default="bt300", choices=["live150","bt300"])
    p.add_argument("--config", default="config/config_v1_1.json")
    p.add_argument("--calendar_start", default="2018-01-01")
    p.add_argument("--calendar_end", default="2030-12-31")
    p.add_argument("--step", type=int, default=1, help="session step (1=every day, 5=faster)")
    args = p.parse_args()

    cal = KRXCalendar.from_exchange_calendars(args.calendar_start, args.calendar_end)
    sessions = [d for d in cal.sessions if args.start <= d <= args.end]

    if not sessions:
        print(f"No sessions found between {args.start} and {args.end}")
        return

    print(f"Starting replay from {args.start} to {args.end} ({len(sessions)} sessions)...")

    # 1) generate snapshots day by day
    for i, d in enumerate(sessions[::args.step]):
        print(f"\n[{i+1}/{len(sessions)}] Snapshot: {d}")
        cmd = [
            sys.executable, "scripts/run_daily_snapshot.py",
            "--db", args.db,
            "--asof", d,
            "--live_n", "150",  # hardcoded for verify
            "--bt_n", "300",
            "--window_days", "40",
            "--calendar_start", args.calendar_start,
            "--calendar_end", args.calendar_end
        ]
        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError:
            print(f"Error executing snapshot for {d}")

    # 2) score outcomes for days where T+10 exists
    print("\nStarting scoring...")
    for d in sessions[::args.step]:
        # Reconstruct run_id exactly as run_daily_snapshot does
        # Defaults matching run_daily_snapshot: live150, bt300, h=5,10, rule=v1.1
        run_id = f"KR|EOD|{d}|live150+bt300|h=5,10|rule=v1.1"
        
        cmd = [
            sys.executable, "scripts/score_outcomes.py",
            "--db", args.db,
            "--run_id", run_id,
            "--calendar_start", args.calendar_start,
            "--calendar_end", args.calendar_end
        ]
        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError:
            print(f"Error scoring for {d} (run_id={run_id})")
        except Exception as e:
            print(f"Error executing scoring: {e}")

    print("DONE: backtest replay finished (snapshots + scoring).")

if __name__ == "__main__":
    main()
