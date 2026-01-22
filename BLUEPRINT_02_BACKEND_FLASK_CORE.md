# KR Market AI Stock Analysis System - Blueprint Part 2: Backend Flask Core

> **Version**: 1.0  
> **Last Updated**: 2026-01-03  
> **File**: `flask_app.py` (3,523 lines)

---

## 1. Flask Application Structure

### 1.1 Imports and Initialization

```python
import os
import json
import threading
import pandas as pd
import numpy as np
import yfinance as yf
import subprocess
from flask import Flask, render_template, jsonify, request
import traceback
from datetime import datetime
import time

app = Flask(__name__)
```

### 1.2 Application Layout

The Flask app is organized into these major sections:

| Section | Line Range | Description |
|:---|:---|:---|
| **Background Scheduler** | 13-147 | Price update daemon thread |
| **Sector Mapping** | 149-298 | US stock sector classification |
| **Page Routes** | 339-363 | HTML template rendering |
| **KR Market APIs** | 364-430, 2755-3400 | Korean market endpoints |
| **US Market APIs** | 753-1600 | US market endpoints |
| **Dividend APIs** | 1849-2055 | Dividend portfolio endpoints |
| **Crypto APIs** | 2186-2631 | Cryptocurrency endpoints |
| **Utility Functions** | Throughout | Helper functions |

---

## 2. Background Price Scheduler

The scheduler runs as a **daemon thread** to update prices every 5 minutes.

### 2.1 Implementation

```python
def start_kr_price_scheduler():
    """Background thread for live price updates"""
    def _run_scheduler():
        print("⏰ KR Price Scheduler started (5min interval, 10s stagger)")
        while True:
            try:
                # 1. Load existing analysis data
                json_path = 'kr_market/data/kr_ai_analysis.json'
                if not os.path.exists(json_path):
                    time.sleep(60)
                    continue

                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                signals = data.get('signals', [])
                if not signals:
                    time.sleep(300)
                    continue

                # 2. Iterate and update each ticker
                updated_count = 0
                for signal in signals:
                    ticker = signal.get('ticker')
                    if not ticker:
                        continue

                    try:
                        from kr_market.kr_ai_analyzer import fetch_current_price
                        current_price = fetch_current_price(ticker)
                        
                        if current_price > 0:
                            entry = signal.get('entry_price', 0)
                            signal['current_price'] = current_price
                            if entry > 0:
                                signal['return_pct'] = round(
                                    ((current_price - entry) / entry) * 100, 2
                                )
                            
                            # Save immediately after each update
                            with open(json_path, 'w', encoding='utf-8') as f:
                                json.dump(data, f, ensure_ascii=False, indent=2)
                            
                            print(f"🔄 Updated price for {signal.get('name')} ({ticker}): {current_price}")
                            updated_count += 1
                        
                    except Exception as e:
                        print(f"Error updating price for {ticker}: {e}")

                    # 3. Stagger delay (10 seconds between tickers)
                    time.sleep(10)

                print(f"✅ Completed 5-min price update cycle ({updated_count} updated)")
                time.sleep(300)  # Wait 5 minutes before next cycle

            except Exception as e:
                print(f"Scheduler error: {e}")
                time.sleep(60)

    # Start daemon thread
    thread = threading.Thread(target=_run_scheduler, daemon=True)
    thread.start()
```

### 2.2 Key Design Decisions

- **Daemon Thread**: Runs independently of Flask request cycle
- **Staggered Updates**: 10-second delay between tickers to avoid API rate limits
- **Immediate Save**: JSON is saved after each ticker update for "real-time" feel
- **Error Resilience**: Catches exceptions per-ticker, continues with others

---

## 3. Complete Route Reference

### 3.1 Page Routes (HTML Templates)

```python
@app.route('/')
def home():
    """Landing page"""
    return render_template('index.html')

@app.route('/app')
def dashboard():
    """Main dashboard with all market views"""
    return render_template('dashboard.html')

@app.route('/dividend')
def dividend_page():
    """Dividend portfolio optimization page"""
    return render_template('dashboard.html')
```

### 3.2 KR Market API Routes

| Endpoint | Method | Description |
|:---|:---|:---|
| `/api/kr/market-status` | GET | Market open/close status |
| `/api/kr/signals` | GET | Active VCP signals |
| `/api/kr/stock-chart/<ticker>` | GET | Price chart data |
| `/api/kr/ai-summary/<ticker>` | GET | Individual stock AI analysis |
| `/api/kr/ai-analysis` | GET | Top 10 AI recommendations |
| `/api/kr/ai-history-dates` | GET | Available history dates |
| `/api/kr/ai-history/<date>` | GET | Historical analysis |
| `/api/kr/cumulative-return` | GET | Portfolio cumulative returns |
| `/api/kr/performance` | GET | Signal performance metrics |
| `/api/kr/market-gate` | GET | Market condition gate |

### 3.3 US Market API Routes

| Endpoint | Method | Description |
|:---|:---|:---|
| `/api/us/portfolio` | GET | US portfolio holdings |
| `/api/us/smart-money` | GET | Smart money flow analysis |
| `/api/us/etf-flows` | GET | ETF fund flows |
| `/api/us/stock-chart/<ticker>` | GET | US stock chart data |
| `/api/us/history-dates` | GET | Available analysis dates |
| `/api/us/history/<date>` | GET | Historical analysis |
| `/api/us/macro-analysis` | GET | Macro economic analysis |
| `/api/us/sector-heatmap` | GET | Sector performance |
| `/api/us/options-flow` | GET | Options activity |
| `/api/us/sec-filings` | GET | SEC filing feed |
| `/api/us/earnings-transcripts` | GET | Earnings call data |
| `/api/us/ai-summary/<ticker>` | GET | Individual AI summary |
| `/api/us/calendar` | GET | Economic calendar |
| `/api/us/technical-indicators/<ticker>` | GET | Technical analysis |
| `/api/us/super-performance` | GET | High performance stocks |
| `/api/us/portfolio-performance` | GET | Portfolio metrics |
| `/api/us/market-gate` | GET | US market gate |

### 3.4 Dividend API Routes

| Endpoint | Method | Description |
|:---|:---|:---|
| `/api/dividend/optimize` | POST | Portfolio optimization |
| `/api/dividend/themes` | GET | Dividend themes |
| `/api/dividend/portfolio` | POST | Build portfolio |
| `/api/dividend/all-tiers` | POST | Multi-tier analysis |
| `/api/dividend/risk-metrics/<ticker>` | GET | Risk metrics |
| `/api/dividend/sustainability/<ticker>` | GET | Dividend safety |
| `/api/dividend/backtest` | POST | Historical backtest |
| `/api/dividend/optimize-advanced` | POST | Advanced optimization |

### 3.5 Crypto API Routes

| Endpoint | Method | Description |
|:---|:---|:---|
| `/api/crypto/vcp-signals` | GET | Crypto VCP signals |
| `/api/crypto/run-scan` | POST | Run crypto scanner |
| `/api/crypto/market-gate` | GET | Crypto market gate |
| `/api/crypto/gate-scan` | POST | Gate-based scan |
| `/api/crypto/timeline` | GET | Signal timeline |
| `/api/crypto/monthly-report` | GET | Monthly performance |
| `/api/crypto/lead-lag` | GET | Lead-lag analysis |

---

## 4. Sector Mapping System

### 4.1 Static Sector Map

```python
SECTOR_MAP = {
    # Technology
    'AAPL': 'Tech', 'MSFT': 'Tech', 'NVDA': 'Tech', 'AVGO': 'Tech',
    'CRM': 'Tech', 'AMD': 'Tech', 'ADBE': 'Tech', 'CSCO': 'Tech',
    
    # Financials
    'BRK-B': 'Fin', 'JPM': 'Fin', 'V': 'Fin', 'MA': 'Fin',
    'BAC': 'Fin', 'WFC': 'Fin', 'GS': 'Fin', 'MS': 'Fin',
    
    # Healthcare
    'LLY': 'Health', 'UNH': 'Health', 'JNJ': 'Health', 'ABBV': 'Health',
    'MRK': 'Health', 'PFE': 'Health', 'TMO': 'Health', 'ABT': 'Health',
    
    # Energy
    'XOM': 'Energy', 'CVX': 'Energy', 'COP': 'Energy', 'SLB': 'Energy',
    
    # Consumer
    'AMZN': 'Cons', 'TSLA': 'Cons', 'HD': 'Cons', 'MCD': 'Cons',
    'WMT': 'Staple', 'PG': 'Staple', 'COST': 'Staple', 'KO': 'Staple',
    
    # Industrials
    'CAT': 'Indust', 'GE': 'Indust', 'RTX': 'Indust', 'HON': 'Indust',
    
    # Communication
    'META': 'Comm', 'GOOGL': 'Comm', 'NFLX': 'Comm', 'DIS': 'Comm',
    
    # Real Estate
    'PLD': 'REIT', 'AMT': 'REIT', 'EQIX': 'REIT', 'SPG': 'REIT',
}
```

### 4.2 Dynamic Sector Fetching

```python
SECTOR_CACHE_FILE = os.path.join('us_market', 'sector_cache.json')

def get_sector(ticker: str) -> str:
    """Get sector for a ticker, auto-fetch from yfinance if not in SECTOR_MAP"""
    global _sector_cache
    
    # Check static map first
    if ticker in SECTOR_MAP:
        return SECTOR_MAP[ticker]
    
    # Check persistent cache
    if ticker in _sector_cache:
        return _sector_cache[ticker]
    
    # Fetch from yfinance and cache
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        sector = info.get('sector', '')
        
        # Map to short code
        sector_short_map = {
            'Technology': 'Tech',
            'Healthcare': 'Health',
            'Financials': 'Fin',
            'Consumer Discretionary': 'Cons',
            'Consumer Staples': 'Staple',
            'Energy': 'Energy',
            'Industrials': 'Indust',
            'Materials': 'Mater',
            'Utilities': 'Util',
            'Real Estate': 'REIT',
            'Communication Services': 'Comm',
        }
        
        short_sector = sector_short_map.get(sector, sector[:5] if sector else '-')
        
        # Persist to cache
        _sector_cache[ticker] = short_sector
        _save_sector_cache(_sector_cache)
        
        return short_sector
    except Exception as e:
        _sector_cache[ticker] = '-'
        return '-'
```

---

## 5. Common Response Patterns

### 5.1 Success Response

```python
@app.route('/api/example')
def example_endpoint():
    try:
        data = some_processing()
        return jsonify({
            'status': 'success',
            'data': data,
            'generated_at': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
```

### 5.2 Caching Pattern

```python
CACHE_FILE = 'data/cache.json'

@app.route('/api/cached-data')
def cached_endpoint():
    force_refresh = request.args.get('refresh', 'false').lower() == 'true'
    
    # Check cache unless force refresh
    if not force_refresh and os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                cached = json.load(f)
            
            # Check if cache is still valid
            if cached.get('date') == datetime.now().strftime('%Y-%m-%d'):
                return jsonify(cached)
        except:
            pass
    
    # Generate fresh data
    data = generate_data()
    data['date'] = datetime.now().strftime('%Y-%m-%d')
    
    # Save to cache
    with open(CACHE_FILE, 'w') as f:
        json.dump(data, f)
    
    return jsonify(data)
```

---

## 6. Server Startup

### 6.1 Main Entry Point

```python
if __name__ == '__main__':
    # Start background scheduler
    start_kr_price_scheduler()
    
    # Start Flask server
    print("🚀 Flask Server Starting on port 5001...")
    app.run(debug=True, host='127.0.0.1', port=5001)
```

### 6.2 Production Deployment

```bash
# Using gunicorn
gunicorn -w 4 -b 0.0.0.0:5001 flask_app:app

# With timeout for long requests
gunicorn -w 4 -b 0.0.0.0:5001 --timeout 120 flask_app:app
```

---

## 7. Error Handling

### 7.1 Global Exception Pattern

```python
@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'status': 'error',
        'message': 'Internal server error',
        'details': str(error)
    }), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'status': 'error',
        'message': 'Endpoint not found'
    }), 404
```

### 7.2 Per-Route Error Handling

```python
@app.route('/api/example')
def example():
    try:
        # Main logic
        result = process_data()
        return jsonify(result)
    except FileNotFoundError:
        return jsonify({'error': 'Data file not found'}), 404
    except ValueError as e:
        return jsonify({'error': f'Invalid input: {e}'}), 400
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
```

---

## 8. File Constants

### 8.1 Important File Paths

```python
# KR Market files
KR_AI_ANALYSIS_FILE = 'kr_market/data/kr_ai_analysis.json'
KR_SIGNALS_FILE = 'kr_market/signals_log.csv'
KR_STOCKS_FILE = 'kr_market/korean_stocks_list.csv'

# US Market files
US_SMART_MONEY_FILE = 'us_market/data/smart_money_picks_v2.csv'
US_PORTFOLIO_FILE = 'us_market/data/final_top10_report.json'
US_MACRO_FILE = 'us_market/data/macro_analysis.json'

# Cache files
SECTOR_CACHE_FILE = 'us_market/sector_cache.json'
```

---

## Next Steps

Continue to **[BLUEPRINT_03_BACKEND_KR_API.md](./BLUEPRINT_03_BACKEND_KR_API.md)** for detailed KR Market API implementations.
