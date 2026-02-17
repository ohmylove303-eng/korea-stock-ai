from pykrx import stock
from datetime import date
import pandas as pd

today = date.today().strftime("%Y%m%d")
print(f"Fetching data for {today}...")

try:
    df = stock.get_market_ohlcv(today, market="KOSPI")
    print("\n[KOSPI Columns]:")
    print(df.columns)
    print("\n[KOSPI Head]:")
    print(df.head(1))
except Exception as e:
    print(f"Error fetching KOSPI: {e}")

try:
    df_kosdaq = stock.get_market_ohlcv(today, market="KOSDAQ")
    print("\n[KOSDAQ Columns]:")
    print(df_kosdaq.columns)
except Exception as e:
    print(f"Error fetching KOSDAQ: {e}")
