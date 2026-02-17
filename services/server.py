from flask import Flask, jsonify, request
from flask_cors import CORS
import sqlite3
import json
import os
import sys

# Path hack to reach engine code
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

app = Flask(__name__)
CORS(app)

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "db.sqlite3")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/api/status', methods=['GET'])
def get_status():
    """
    Palantir Layer: Market Regime
    """
    conn = get_db_connection()
    # Get latest run
    run = conn.execute("SELECT * FROM runs ORDER BY created_at_kst DESC LIMIT 1").fetchone()
    if not run:
        conn.close()
        return jsonify({"error": "No data run found"}), 404
    
    run_id = run["run_id"]
    
    # Get Market Stats from a representative ticker (e.g. 069500 KODEX 200 or first in list)
    # Ideally should store market-level stats separately, but we can grab from any snapshot
    # that has kospi_regime populated.
    market_snapshot = conn.execute("""
        SELECT usdkrw, kospi_ret_20d, kospi_regime 
        FROM ticker_snapshots 
        WHERE run_id = ? AND ticker = '069500' 
        LIMIT 1
    """, (run_id,)).fetchone()
    
    if not market_snapshot:
        # Fallback to any ticker
        market_snapshot = conn.execute("""
            SELECT usdkrw, kospi_ret_20d, kospi_regime 
            FROM ticker_snapshots 
            WHERE run_id = ? 
            LIMIT 1
        """, (run_id,)).fetchone()

    status = {
        "asof_date": run["asof_date"],
        "run_id": run_id,
        "kospi_regime": market_snapshot["kospi_regime"] if market_snapshot else "unknown",
        "usdkrw": market_snapshot["usdkrw"] if market_snapshot else 0,
        "market_action": "DEFENSIVE" if (market_snapshot and market_snapshot["kospi_regime"] == "bear") else "NEUTRAL"
    }
    conn.close()
    return jsonify(status)

@app.route('/api/candidates', methods=['GET'])
def get_candidates():
    """
    NICE Layer: Top Scored Tickers
    """
    conn = get_db_connection()
    # Get latest run
    run = conn.execute("SELECT run_id FROM runs ORDER BY created_at_kst DESC LIMIT 1").fetchone()
    if not run: return jsonify([])
    
    # Get Decision + Snapshot joined
    rows = conn.execute("""
        SELECT d.ticker, d.gate_action, d.decision_action, d.nice_score, 
               s.close_px, s.atr_14, s.trading_value_krw
        FROM decisions d
        JOIN ticker_snapshots s ON d.run_id = s.run_id AND d.ticker = s.ticker
        WHERE d.run_id = ? AND d.decision_action != 'REJECT'
        ORDER BY d.nice_score DESC, s.trading_value_krw DESC
        LIMIT 20
    """, (run["run_id"],)).fetchall()
    
    results = [dict(row) for row in rows]
    conn.close()
    return jsonify(results)

@app.route('/api/analysis/<ticker>', methods=['GET'])
def get_analysis_detail(ticker):
    """
    Mini Layer: Execution Strategy (ATR Based)
    """
    conn = get_db_connection()
    run = conn.execute("SELECT run_id, asof_date FROM runs ORDER BY created_at_kst DESC LIMIT 1").fetchone()
    if not run: return jsonify({"error": "No data"}), 404
    
    row = conn.execute("""
        SELECT s.*, d.gate_action, d.decision_action, d.nice_score, d.confidence
        FROM ticker_snapshots s
        JOIN decisions d ON s.run_id = d.run_id AND s.ticker = d.ticker
        WHERE s.run_id = ? AND s.ticker = ?
    """, (run["run_id"], ticker)).fetchone()
    
    if not row:
        conn.close()
        return jsonify({"error": "Ticker not found in latest run"}), 404
    
    data = dict(row)
    
    # --- DYNAMIC STRATEGY ENGINE ---
    # Logic: 
    #   Entry = Close (Confirmation) or Close * 0.98 (Pullback) - Simplified for API: "Close"
    #   Risk_Unit = ATR * 1.0 (Strict) or ATR * 1.5 (Loose)
    #   SL = Close - Risk_Unit
    #   TP1 = Close + Risk_Unit (1R)
    #   TP2 = Close + 2*Risk_Unit (2R)
    
    close = data["close_px"]
    atr = data["atr_14"]
    
    strategy = None
    if close and atr and atr > 0:
        # Strategy A: Reclaim/Breakout (Trend Following)
        risk_unit = atr * 1.0 # 1 ATR Stop
        entry_price = close # Assuming entry at close/next open
        sl_price = entry_price - risk_unit
        tp1_price = entry_price + risk_unit
        tp2_price = entry_price + (risk_unit * 2.5) # 2.5R for strong trend
        
        rr_ratio = (tp2_price - entry_price) / (entry_price - sl_price)
        
        strategy = {
            "type": "Trend Reclaim (ATR Based)",
            "setup": "ATR Volatility Breakout",
            "entry_price": round(entry_price),
            "stop_loss": round(sl_price),
            "tp1": round(tp1_price),
            "tp2": round(tp2_price),
            "risk_reward_ratio": round(rr_ratio, 2),
            "risk_per_share": round(entry_price - sl_price),
            "atr_used": round(atr)
        }
        
    response = {
        "meta": {
            "ticker": data["ticker"],
            "asof": data["asof_date"],
            "run_id": data["run_id"]
        },
        "evidence": {
            "price": close,
            "volume_krw": data["trading_value_krw"],
            "foreign_net": data["foreign_net_buy_krw"],
            "inst_net": data["inst_net_buy_krw"],
            "indicators": {
                "rsi": data["rsi_14"],
                "macd": data["macd_hist"],
                "vcp": data["vcp_score"],
                "atr": data["atr_14"]
            }
        },
        "score_layer": {
            "nice_score": data["nice_score"],
            "gate": data["gate_action"],
            "decision": data["decision_action"],
            "confidence": data["confidence"]
        },
        "execution_strategy": strategy
    }
    
    conn.close()
    return jsonify(response)

if __name__ == '__main__':
    print("Starting Institution-Grade Analysis Server on port 5001...")
    app.run(host='0.0.0.0', port=5001, debug=True)
