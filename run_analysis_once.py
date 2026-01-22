import pandas as pd
import json
import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from kr_market import kr_ai_analyzer

def run():
    print("🧠 Starting AI Analysis on Real Signals...")
    
    csv_path = 'kr_market/data/signals_log.csv'
    if not os.path.exists(csv_path):
        print("❌ signals_log.csv not found")
        return

    df = pd.read_csv(csv_path)
    
    # Sort by Score desc
    if 'supply_demand_score' in df.columns:
        df = df.sort_values('supply_demand_score', ascending=False)
    
    # Convert to list of dicts
    signals = df.to_dict('records')
    
    # Rename keys to match what analyzer expects if diff
    # Analyzer expects: ticker, name, score, contraction_ratio, foreign_5d, inst_5d, entry_price...
    # CSV has: signal_date,ticker,name,market,sector,close,contraction_ratio,foreign_net_buy_5d,inst_net_buy_5d,supply_demand_score
    
    # Mapping
    mapped_signals = []
    for s in signals:
        mapped_signals.append({
            'ticker': str(s['ticker']).zfill(6),
            'name': s['name'],
            'market': s['market'],
            'score': s.get('supply_demand_score', 0),
            'contraction_ratio': s.get('contraction_ratio', 0),
            'foreign_5d': s.get('foreign_net_buy_5d', 0),
            'inst_5d': s.get('inst_net_buy_5d', 0),
            'entry_price': s.get('close', 0), # using close as entry
            'current_price': s.get('close', 0),
            'return_pct': 0,
            'signal_date': s.get('signal_date')
        })
    
    print(f"   Analyzing top 10 of {len(mapped_signals)} signals...")
    
    # Generate Analysis
    result = kr_ai_analyzer.generate_ai_recommendations(mapped_signals) 
    
    # Save
    json_path = 'kr_market/data/kr_ai_analysis.json'
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"✅ Generated {json_path}")

if __name__ == "__main__":
    run()
