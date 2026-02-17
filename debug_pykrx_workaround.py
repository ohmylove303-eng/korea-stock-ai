from pykrx import stock
from datetime import date
import pandas as pd

today = "20260206"
print(f"Fetching data for explicitly set date: {today}...")

try:
    df = stock.get_market_ohlcv(today, market="KOSPI")
    print(f"Original Columns: {df.columns}")
    
    # Force rename by index assuming standard OHLCV order
    # Typically: 시가, 고가, 저가, 종가, 거래량
    if len(df.columns) >= 5:
        df.columns = ['open', 'high', 'low', 'close', 'volume', 'trading_value', 'change_pct'][:len(df.columns)]
        print(f"Renamed Columns: {df.columns}")
        print(df.head(1))
    else:
        print("Unexpected column count")

except Exception as e:
    print(f"Error fetching KOSPI: {e}")
