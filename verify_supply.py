import asyncio
import sys
import os
from datetime import date, datetime

sys.path.append(os.path.abspath("/Users/jungsunghoon/Desktop/Desktop/한국주식"))

# We mock the DataCollector to use a specific date for verification
# or we just use pykrx directly to prove the library works in this environment
from pykrx import stock

def verify_pykrx_direct():
    print("=== K-Stock Supply Data Verification (Direct PyKrx) ===")
    print(f"System Time: {datetime.now()}")
    
    # Try fetching data from a known past period (e.g., Jan 2024)
    # to avoid future-date issues if system clock is 2026
    start_date = "20240102"
    end_date = "20240110"
    ticker = "005930" # Samsung Electronics
    
    print(f"\n[1] Requesting Foreign/Institutional Net Buy")
    print(f"    Target: {ticker}")
    print(f"    Period: {start_date} ~ {end_date}")
    
    try:
        # get_market_net_purchases_of_equities returns DataFrame
        # Columns: 종목명, 매도거래량, 매수거래량, 순매수거래량, 매도거래대금, 매수거래대금, 순매수거래대금 (maybe)
        # Or simpler API: get_market_trading_value_by_date
        
        df = stock.get_market_trading_value_by_date(start_date, end_date, ticker)
        
        if df.empty:
            print("❌ DataFrame is empty.")
            return

        print(f"✅ Data Fetched Successfully! (Rows: {len(df)})")
        print("\n--- Sample Data (Head) ---")
        print(df.head())
        
        # Check specific columns
        if '외국인' in df.columns:
            foreign_sum = df['외국인'].sum()
            print(f"\n📊 Total Foreign Net Buy: {foreign_sum:,} KRW")
        else:
            print("\n⚠️ '외국인' column not found.")
            print(f"Columns: {df.columns}")

        if '기관합계' in df.columns:
            inst_sum = df['기관합계'].sum()
            print(f"📊 Total Institutional Net Buy: {inst_sum:,} KRW")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verify_pykrx_direct()
