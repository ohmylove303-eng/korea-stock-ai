import sqlite3
import os
from datetime import datetime
from typing import Dict, Any, Optional

class DBManager:
    """
    Evidence Capsule Storage (SQLite)
    Stores every decision snapshot for post-mortem analysis.
    """
    
    DB_PATH = "evidence_capsule.db"
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or self.DB_PATH
        self._init_schema()
        
    def _get_conn(self):
        return sqlite3.connect(self.db_path)
        
    def _init_schema(self):
        """Initialize the decision_snapshots table protocol"""
        
        schema = """
        CREATE TABLE IF NOT EXISTS decision_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            asof_timestamp TIMESTAMP NOT NULL,
            ticker TEXT NOT NULL,
            window_days INTEGER DEFAULT 5,
            
            -- Price Data (Context)
            price_close REAL,
            price_trend_pct REAL,
            volatility_atr REAL,
            
            -- Supply Data (The Core Evidence)
            foreign_flow_pct REAL,
            foreign_zscore REAL,
            institution_flow_pct REAL,
            short_ratio REAL,
            
            -- Regime (Causality)
            kospi_regime TEXT,
            usdkrw REAL,
            
            -- Decision (Result)
            decision TEXT,
            score INTEGER,
            confidence INTEGER,
            reason TEXT,
            
            -- Verification (Future Feedback)
            expected_return_10d REAL,
            actual_return_10d REAL,
            error_type TEXT,
            
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE INDEX IF NOT EXISTS idx_ticker_ts ON decision_snapshots(ticker, asof_timestamp);
        """
        
        with self._get_conn() as conn:
            conn.executescript(schema)
            
    def save_snapshot(self, data: Dict[str, Any]) -> int:
        """
        Save a single decision snapshot.
        Returns the Inserted ID.
        """
        query = """
        INSERT INTO decision_snapshots (
            asof_timestamp, ticker, window_days,
            price_close, price_trend_pct, volatility_atr,
            foreign_flow_pct, foreign_zscore, institution_flow_pct, short_ratio,
            kospi_regime, usdkrw,
            decision, score, confidence, reason,
            expected_return_10d
        ) VALUES (
            :asof_timestamp, :ticker, :window_days,
            :price_close, :price_trend_pct, :volatility_atr,
            :foreign_flow_pct, :foreign_zscore, :institution_flow_pct, :short_ratio,
            :kospi_regime, :usdkrw,
            :decision, :score, :confidence, :reason,
            :expected_return_10d
        )
        """
        
        # Ensure timestamp is datetime object or ISO string
        if isinstance(data.get('asof_timestamp'), str):
            # Pass as is (sqlite handles ISO strings well)
            pass
        elif data.get('asof_timestamp') is None:
            data['asof_timestamp'] = datetime.now().isoformat()
            
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute(query, data)
            return cur.lastrowid
            
    def get_snapshot(self, snapshot_id: int) -> Optional[Dict[str, Any]]:
        query = "SELECT * FROM decision_snapshots WHERE id = ?"
        with self._get_conn() as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute(query, (snapshot_id,))
            row = cur.fetchone()
            return dict(row) if row else None
            
    def update_verification(self, snapshot_id: int, actual_return: float, error_type: str = None):
        """Update the snapshot with post-mortem results"""
        query = """
        UPDATE decision_snapshots 
        SET actual_return_10d = ?, error_type = ?
        WHERE id = ?
        """
        with self._get_conn() as conn:
            conn.execute(query, (actual_return, error_type, snapshot_id))

if __name__ == "__main__":
    # Smoke Test
    db = DBManager("test_capsule.db")
    import os
    print(f"DB Initialized: {os.path.exists('test_capsule.db')}")
    
    sid = db.save_snapshot({
        "asof_timestamp": datetime.now(),
        "ticker": "005930",
        "price_close": 70000,
        "foreign_flow_pct": 1.5,
        "decision": "BUY",
        "reason": "Test"
    })
    print(f"Snapshot Saved ID: {sid}")
    print(f"Retrieved: {db.get_snapshot(sid)}")
    
    # Clean up
    if os.path.exists("test_capsule.db"):
        os.remove("test_capsule.db")
