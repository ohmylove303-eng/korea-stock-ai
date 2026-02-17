import asyncio
import sys
import os
from datetime import date
import random

sys.path.append(os.path.abspath(os.path.dirname(__file__) + "/.."))

from engine.collectors import DataCollector
from engine.db_manager import DBManager
from engine.decision import DecisionEngine

async def collect_evidence_daily():
    print("=== 🕵️‍♀️ K-Stock Evidence Collector (Daily) ===")
    print("=== Phase 2: Integrated Decision Engine ===")
    
    # 1. Initialize Components
    db = DBManager()
    collector = DataCollector()
    engine = DecisionEngine()
    
    # 2. Assess Market Regime (Palantir Layer)
    print("[-] Assessing Market Regime...")
    regime = await engine.get_regime()
    print(f"   [Regime] Status: {regime['status']} | USD/KRW: {regime['usdkrw']} | Reason: {regime.get('risk_reason')}")
    
    # 3. Define Universe
    print("[-] Selecting Universe (Top-300)...")
    universe = await collector.get_target_universe()
    if not universe:
        universe = ["005930", "000660", "035420", "005380"] 
        
    target_tickers = universe[:5] # Test Limit
    print(f"[-] Processing {len(target_tickers)} targets...")
    
    results = []
    
    for ticker in target_tickers:
        print(f"\n[Target: {ticker}]")
        try:
            # A. Collect Data
            flow = await collector.normalize_flow(ticker, window=5)
            chart = await collector.get_chart_data(ticker, days=20)
            
            if chart.empty:
                print("   [!] No chart data, skipping")
                continue
                
            close = float(chart.iloc[-1]['close'])
            prev_close = float(chart.iloc[-2]['close'])
            trend_pct = ((close - prev_close) / prev_close) * 100
            
            high = float(chart.iloc[-1]['high'])
            low = float(chart.iloc[-1]['low'])
            volatility = ((high - low) / close) * 100
            
            # B. Partial Capsule
            capsule_data = {
                "foreign_flow_pct": flow['foreign_pct'],
                "institution_flow_pct": flow['inst_pct'],
                "volatility_atr": round(volatility, 2),
                "price_trend_pct": round(trend_pct, 2)
            }
            
            # C. Decision Engine (NICE Layer)
            decision_result = engine.evaluate(capsule_data, regime)
            
            # D. Final Capsule Construction
            capsule = {
                "ticker": ticker,
                "window_days": 5,
                "price_close": close,
                "price_trend_pct": round(trend_pct, 2),
                "volatility_atr": round(volatility, 2),
                
                "foreign_flow_pct": flow['foreign_pct'],
                "foreign_zscore": 0.0, 
                "institution_flow_pct": flow['inst_pct'],
                "short_ratio": 0.0, 
                
                "kospi_regime": regime['status'],
                "usdkrw": regime['usdkrw'],
                
                "decision": decision_result['decision'],
                "score": decision_result['score'],
                "confidence": decision_result['confidence'],
                "expected_return_10d": 0.0, # Placeholder for Prediction Model
                "reason": decision_result['reason']
            }
            
            # E. Save
            snapshot_id = db.save_snapshot(capsule)
            print(f"   [+] Result: {capsule['decision']} (Score: {capsule['score']})")
            print(f"       Reason: {capsule['reason']}")
            print(f"       Foreign: {capsule['foreign_flow_pct']}% | Inst: {capsule['institution_flow_pct']}%")
            
            results.append(capsule)
            
        except Exception as e:
            print(f"   [!] Error processing {ticker}: {e}")
            
    print(f"\n=== ✅ Complete. Saved {len(results)} snapshots. ===")

if __name__ == "__main__":
    asyncio.run(collect_evidence_daily())
