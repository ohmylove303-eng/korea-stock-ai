import asyncio
import sys
import os
from datetime import date, timedelta
import pandas as pd
from engine.collectors import DataCollector
from engine.decision import DecisionEngine

# Silence Warnings
import warnings
warnings.filterwarnings("ignore")

async def run_simulation(ticker: str, start_date_str: str, days: int = 20):
    print(f"=== 🕵️‍♀️ Phase 3: Verification (Time Travel) ===")
    print(f"[-] Target: {ticker} | Period: {days} trading days from {start_date_str}")
    
    collector = DataCollector()
    engine = DecisionEngine()
    
    # 1. Setup Date Loop
    from pykrx import stock
    # Get business days
    end_date = pd.to_datetime(start_date_str) + timedelta(days=days*2) # Buffer for holidays
    dates = stock.get_market_ohlcv(start_date_str, end_date.strftime("%Y%m%d"), ticker).index
    
    simulation_log = []
    
    print(f"[-] Simulating {len(dates[:days])} days...")
    
    for current_date in dates[:days]:
        d_str = current_date.strftime("%Y-%m-%d")
        
        # A. Mock Time Travel (Override engine cache if needed, but here we pass fresh data)
        # Note: 'get_regime' uses 'date.today()' in my logic. I need to PATCH it or mock it.
        # Actually my DecisionEngine.get_regime() uses date.today().
        # I MUST Allow passing date to get_regime.
        
        # B. Collect Historical Data
        # Flow (Window 5 days leading up to current_date)
        try:
            flow = await collector.normalize_flow(ticker, target_date=current_date.date(), window=5)
            
            # Chart (Leading up to current_date)
            # We need to fetch chart ending at current_date
            # Pykrx fetch... actually my get_chart_data uses date.today().
            # I need valid historical fetchers.
            # I will use direct stock.get_market_ohlcv for precise window.
            
            # Direct fetch for 'today' context
            df_today = stock.get_market_ohlcv(current_date.strftime("%Y%m%d"), current_date.strftime("%Y%m%d"), ticker)
            if df_today.empty: continue
            
            close = df_today['종가'].iloc[0]
            
            # Trend Check (Last 20 days relative to NOW)
            start_trend = current_date - timedelta(days=30)
            df_trend = stock.get_market_ohlcv(start_trend.strftime("%Y%m%d"), current_date.strftime("%Y%m%d"), ticker)
            trend_pct = 0
            volatility = 0
            if not df_trend.empty:
                prev_close = df_trend['종가'].iloc[-2] if len(df_trend) > 1 else close
                trend_pct = ((close - prev_close) / prev_close) * 100
                high = df_trend['고가'].iloc[-1]
                low = df_trend['저가'].iloc[-1]
                volatility = ((high - low) / close) * 100
                
            # C. Future Outcome (The Truth) - Look ahead 5 days
            future_date = current_date + timedelta(days=7) # Approx 5 trading days
            df_future = stock.get_market_ohlcv(future_date.strftime("%Y%m%d"), (future_date+timedelta(days=5)).strftime("%Y%m%d"), ticker)
            
            outcome_return = 0.0
            if not df_future.empty:
                future_close = df_future['종가'].iloc[0]
                outcome_return = ((future_close - close) / close) * 100
            
            # D. Construct Capsule
            # We assume Regime is NEUTRAL to test STOCK LOGIC primarily (Mocking regime is hard without historical macro data ready)
            # Or I can fetch historical USD/KRW via fdr easily.
            import FinanceDataReader as fdr
            usdkrw = fdr.DataReader('USD/KRW', current_date)[ 'Close'].iloc[-1]
            # Simple assumption for test
            regime_status = "BEAR" if usdkrw > 1400 else "NEUTRAL"
            
            regime = {
                "status": regime_status, 
                "usdkrw": usdkrw,
                "risk_reason": "Simulated"
            }
            
            capsule = {
                "foreign_flow_pct": flow['foreign_pct'],
                "institution_flow_pct": flow['inst_pct'],
                "volatility_atr": round(volatility, 2),
                "price_trend_pct": round(trend_pct, 2)
            }
            
            # E. Decision
            decision = engine.evaluate(capsule, regime)
            
            # F. Log Result
            sim_res = {
                "date": d_str,
                "decision": decision['decision'],
                "score": decision['score'],
                "flow_f": flow['foreign_pct'],
                "flow_i": flow['inst_pct'],
                "actual_return_5d": round(outcome_return, 2),
                "evaluation": "UNKNOWN"
            }
            
            # Validate
            if sim_res['decision'] == "BUY":
                if outcome_return > 0: sim_res['evaluation'] = "✅ WIN"
                else: sim_res['evaluation'] = "❌ LOSS"
            elif sim_res['decision'] == "REJECT":
                if outcome_return < 0: sim_res['evaluation'] = "🛡️ GOOD SAVE"
                else: sim_res['evaluation'] = "⚠️ MISSED"
            else: # WATCH
                sim_res['evaluation'] = "👀 WATCH"
                
            simulation_log.append(sim_res)
            print(f"[{d_str}] {sim_res['decision']} (Sc:{sim_res['score']}) -> 5d Rtn: {sim_res['actual_return_5d']}% | {sim_res['evaluation']}")
            print(f"    F: {sim_res['flow_f']:.2f}% | I: {sim_res['flow_i']:.2f}%")
            
        except Exception as e:
            print(f"Error on {d_str}: {e}")
            
    print("\n=== ✨ Verification Summary ===")
    df_res = pd.DataFrame(simulation_log)
    print(df_res[['date', 'decision', 'actual_return_5d', 'evaluation']].to_string())
    
    wins = len(df_res[df_res['evaluation'] == "✅ WIN"])
    losses = len(df_res[df_res['evaluation'] == "❌ LOSS"])
    saves = len(df_res[df_res['evaluation'] == "🛡️ GOOD SAVE"])
    missed = len(df_res[df_res['evaluation'] == "⚠️ MISSED"])
    
    print(f"\nStats:")
    print(f"- Wins (Prediction Hit): {wins}")
    print(f"- Losses (Prediction Fail): {losses}")
    print(f"- Defense (Crash Avoided): {saves}")
    print(f"- Missed Opportunities: {missed}")

if __name__ == "__main__":
    t_ticker = "005930" # Samsung
    t_start = "20240102"
    asyncio.run(run_simulation(t_ticker, t_start))
