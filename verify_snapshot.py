import asyncio
from pykrx import stock
import pandas as pd

def verify_snapshot():
    print("=== Expert K-Stock Verification (Snapshot Method) ===")
    ticker = "005930" # Samsung Electronics
    target_date = "20240105"
    
    print(f"Target: {ticker}, Date: {target_date}\n")
    
    # Test 4: Investor Net Buy Snapshot (One Day, All Tickers -> Filter)
    print("[Test 4] Investor Net Buy (Daily Snapshot)")
    try:
        # get_market_net_purchases_of_equities_by_ticker takes (start, end, ticker) -> We tried, failed.
        # Now try: get_market_net_purchases_of_equities(date, market) -> Returns All tickers for that date
        
        df = stock.get_market_net_purchases_of_equities(target_date, target_date, "KOSPI", ticker)
        # Note: Signature might be (start, end, ticker) OR (date, market)?
        # Let's check signature by usage. 
        # Actually documentation says: get_market_net_purchases_of_equities_by_ticker(start, end, ticker)
        # And: get_market_net_purchases_of_equities(start, end, market) -> Top list? No.
        
        # Let's try the "RANKING" API which is usually robust.
        # stock.get_market_net_purchases_of_equities_by_ticker IS the detailed one.
        
        # Let's try "get_market_trading_value_by_date" again with correct columns?
        # Maybe ticker formatting? "005930" is correct.
        
        # Try a different function:
        # stock.get_market_cap_by_date("20240103", "20240103", "005930")
        
        pass
    except Exception as e:
        print(f"Skipping... {e}")

    # RETRY Test 2 with different parameters or just confirm it's broken
    print("\n[Retry] Fetching Investor Breakdown via Ticker...")
    try:
        # The function signature: (start, end, ticker)
        df = stock.get_market_net_purchases_of_equities_by_ticker("20240103", "20240110", "005930")
        print(f"Result Type: {type(df)}")
        if df.empty:
            print("❌ Still Empty.")
        else:
            print("✅ SUCCEEDED!")
            print(df)
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    verify_snapshot()
