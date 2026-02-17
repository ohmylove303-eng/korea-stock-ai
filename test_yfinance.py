import yfinance as yf
import pandas as pd

# Test specific tickers
tickers = [
    ("086790.KS", "Hana Financial (KOSPI)"), 
    ("298380.KQ", "ABL Bio (KOSDAQ)")
]

print(f"Testing YFinance for Korean Stocks...\n")

for ticker_symbol, name in tickers:
    print(f"=== {name} ({ticker_symbol}) ===")
    try:
        stock = yf.Ticker(ticker_symbol)
        
        # Get recent history
        hist = stock.history(period="5d")
        
        if hist.empty:
            print(f"❌ No data found for {ticker_symbol}")
            continue
            
        print(hist[['Open', 'High', 'Low', 'Close', 'Volume']].tail())
        
        latest = hist.iloc[-1]
        prev = hist.iloc[-2] if len(hist) > 1 else latest
        
        price = latest['Close']
        change_pct = ((price - prev['Close']) / prev['Close']) * 100
        
        print(f"\n✅ Latest Price: {price:,.0f} KRW")
        print(f"✅ Change: {change_pct:.2f}%")
        print(f"✅ Date: {latest.name.strftime('%Y-%m-%d')}\n")
        
    except Exception as e:
        print(f"❌ Error: {e}\n")
