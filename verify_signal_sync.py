import json
import requests

BASE_URL = "http://localhost:5000/api/kr"

def verify_sync():
    print("🔍 Verifying Signal Synchronization...")
    
    try:
        # 1. Fetch from Signals API
        signals_res = requests.get(f"{BASE_URL}/signals")
        signals_data = signals_res.json()
        
        # 2. Fetch from AI Analysis API
        ai_res = requests.get(f"{BASE_URL}/ai-analysis")
        ai_data = ai_res.json()
        
        sig_list = signals_data.get('signals', [])
        ai_list = ai_data.get('signals', [])
        
        print(f"✅ Signals Count: {len(sig_list)}")
        print(f"✅ AI Analysis Count: {len(ai_list)}")
        
        if len(sig_list) != len(ai_list):
            print("❌ DISCREPANCY: Signal list lengths do not match.")
        else:
            print("✅ Signal list lengths match.")
            
        # Check Top 3
        for i in range(min(3, len(sig_list))):
            s = sig_list[i]
            a = ai_list[i]
            if s['ticker'] == a['ticker']:
                print(f"✅ Match at Rank {i+1}: {s['name']} ({s['ticker']}) - Score: {s['nice_layers']['total']}")
            else:
                print(f"❌ DISCREPANCY at Rank {i+1}: {s['ticker']} vs {a['ticker']}")
                
        # Check Layers JSON structure
        first_sig = sig_list[0]
        layers = first_sig.get('nice_layers', {})
        expected_keys = ['L1_technical', 'L2_supply', 'L3_sentiment', 'L4_macro', 'L5_institutional', 'total', 'max_total']
        if all(k in layers for k in expected_keys) and layers['max_total'] == 100:
            print("✅ NICE Layers structure is correct (100-scale).")
        else:
            print(f"❌ DISCREPANCY: NICE Layers structure invalid or wrong scale: {layers}")

    except Exception as e:
        print(f"❌ Error during verification: {e}")

if __name__ == "__main__":
    verify_sync()
