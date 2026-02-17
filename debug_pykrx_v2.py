from pykrx import stock
date = "20240105"

print("--- Test 1: get_market_ohlcv (all tickers) ---")
try:
    # Alternative signature
    df = stock.get_market_ohlcv(date, market="KOSPI")
    print("Success 1")
    print(df.head())
except Exception as e:
    print(f"Fail 1: {e}")

print("\n--- Test 2: get_market_ohlcv_by_ticker (deprecated alias?) ---")
try:
    df = stock.get_market_ohlcv_by_ticker(date, market="KOSPI")
    print("Success 2")
    print(df.head())
except Exception as e:
    print(f"Fail 2: {e}")

print("\n--- Test 3: Single Ticker (Samsung Elec) ---")
try:
    df = stock.get_market_ohlcv("20240104", "20240105", "005930")
    print("Success 3")
    print(df.head())
except Exception as e:
    print(f"Fail 3: {e}")
