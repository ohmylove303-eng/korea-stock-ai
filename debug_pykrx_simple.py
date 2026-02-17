from pykrx import stock
import pandas as pd
date = "20240105"
print(f"Fetching market OHLCV for {date} (KOSPI)...")
try:
    df = stock.get_market_ohlcv_by_ticker(date, market="KOSPI")
    print(f"Result shape: {df.shape if df is not None else 'None'}")
    if df is not None:
        print("Columns:", df.columns.tolist())
        print(df.head())
except Exception as e:
    print(f"Error: {e}")
