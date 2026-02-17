from pykrx import stock
from datetime import date

def debug_pykrx_structure():
    print("=== Debug PyKrx Columns ===")
    today = date.today().strftime("%Y%m%d")
    today = "20240105" # Use known past date
    
    # 1. Market Cap
    try:
        df_cap = stock.get_market_cap_by_date(today, today, "KOSPI")
        print("\n[Market Cap Columns]:")
        print(df_cap.columns.tolist())
        print(df_cap.head(1))
    except Exception as e:
        print(f"Cap Error: {e}")
        
    # 2. OHLCV
    try:
        df_ohlcv = stock.get_market_ohlcv(today, today, "005930")
        print("\n[OHLCV Columns]:")
        print(df_ohlcv.columns.tolist())
        print(df_ohlcv.head(1))
    except Exception as e:
        print(f"OHLCV Error: {e}")

if __name__ == "__main__":
    debug_pykrx_structure()
