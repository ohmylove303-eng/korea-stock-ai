import asyncio
from pykrx import stock
import pandas as pd
from datetime import datetime

def verify_robust():
    print("=== Robust K-Stock Verification ===")
    ticker = "005930" # Samsung Elec
    start_date = "20240103"
    end_date = "20240105"
    
    print(f"Target: {ticker}, Period: {start_date}~{end_date}\n")
    
    # Test 1: OHLCV (Basic Price)
    print("[Test 1] OHLCV (Price Data)")
    try:
        df = stock.get_market_ohlcv(start_date, end_date, ticker)
        if not df.empty:
            print("✅ OHLCV Fetched!")
            print(df.head())
        else:
            print("❌ OHLCV Empty")
    except Exception as e:
        print(f"❌ OHLCV Error: {e}")

    # Test 2: Investor Breakdown (The Core Requirement)
    print("\n[Test 2] Investor Trading Value (Supply/Demand)")
    try:
        # get_market_net_purchases_of_equities_by_ticker
        # This function returns net purchase by investor for a specific ticker
        df_inv = stock.get_market_net_purchases_of_equities_by_ticker(start_date, end_date, ticker)
        
        if not df_inv.empty:
            print("✅ Investor Data Fetched!")
            print(df_inv.head())
            print(f"Columns: {df_inv.columns}")
            
            # Check for Foreigner
            if '외국인' in df_inv.index:
                 # Row index is investor name usually? No, let's check structure
                 # Actually for 'by_ticker', the index is usually the investor type (e.g., 금융투자, 보험, 투신, 외국인...) 
                 # OR it returns daily breakdown?
                 # Let's inspect.
                 pass
        else:
            print("❌ Investor Data Empty")
            
    except Exception as e:
        print(f"❌ Investor Data Error: {e}")

    # Test 3: Daily Trading Volume by Investor (Alternative API)
    print("\n[Test 3] Alternative API (Daily Breakdown)")
    try:
        # get_market_trading_value_by_date
        # Returns daily trend of investor trading
        df_daily = stock.get_market_trading_value_by_date(start_date, end_date, ticker)
        if not df_daily.empty:
             print("✅ Daily Breakdown Fetched!")
             print(df_daily.head())
        else:
             print("❌ Daily Breakdown Empty")
    except Exception as e:
        print(f"❌ Daily Breakdown Error: {e}")

if __name__ == "__main__":
    verify_robust()
