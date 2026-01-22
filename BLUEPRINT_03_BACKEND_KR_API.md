# KR Market AI Stock Analysis System - Blueprint Part 3: KR Market APIs

> **Version**: 1.0  
> **Last Updated**: 2026-01-03  
> **Primary File**: `flask_app.py` (Lines 2755-3200)

---

## 1. Overview

This document contains the complete source code for all Korean market API endpoints.

### 1.1 Endpoint Summary

| Endpoint | Description |
|:---|:---|
| `/api/kr/signals` | Active VCP signals (Top 20) |
| `/api/kr/stock-chart/<ticker>` | Price chart data |
| `/api/kr/ai-analysis` | AI recommendations (Top 10) |
| `/api/kr/ai-summary/<ticker>` | Individual stock AI analysis |
| `/api/kr/ai-history-dates` | Available history dates |
| `/api/kr/ai-history/<date>` | Historical analysis by date |
| `/api/kr/cumulative-return` | Portfolio cumulative returns |
| `/api/kr/performance` | Signal performance metrics |
| `/api/kr/market-gate` | Market condition gate |

---

## 2. GET /api/kr/signals

Returns Top 20 VCP signals with institutional flow data.

### 2.1 Full Implementation

```python
@app.route('/api/kr/signals')
def get_kr_signals():
    """오늘의 VCP + 외인매집 시그널 (Top 20 순위)"""
    try:
        signals_path = 'kr_market/signals_log.csv'
        
        if not os.path.exists(signals_path):
            return jsonify({
                'signals': [],
                'count': 0,
                'message': '시그널 로그가 없습니다. 먼저 스캔을 실행하세요.'
            })
        
        df = pd.read_csv(signals_path, encoding='utf-8-sig')
        df['ticker'] = df['ticker'].astype(str).str.zfill(6)
        
        # 종목명 및 시장 정보 로드
        stock_names = {}
        stock_markets = {}
        stocks_file = 'kr_market/korean_stocks_list.csv'
        if os.path.exists(stocks_file):
            stocks_df = pd.read_csv(stocks_file, encoding='utf-8-sig', dtype={'ticker': str})
            stocks_df['ticker'] = stocks_df['ticker'].astype(str).str.zfill(6)
            stock_names = dict(zip(stocks_df['ticker'], stocks_df['name']))
            stock_markets = dict(zip(stocks_df['ticker'], stocks_df['market']))
        
        # 최신 시그널 (OPEN 상태)
        open_signals = df[df['status'] == 'OPEN'].copy()
        today = datetime.now().strftime('%Y-%m-%d')
        
        signals = []
        for _, row in open_signals.iterrows():
            score = float(row['score']) if pd.notna(row['score']) else 0
            contraction = float(row['contraction_ratio']) if pd.notna(row['contraction_ratio']) else 1
            foreign_5d = int(row['foreign_5d']) if pd.notna(row['foreign_5d']) else 0
            inst_5d = int(row['inst_5d']) if pd.notna(row['inst_5d']) else 0
            signal_date = row['signal_date']
            
            # 제외 조건
            if contraction > 0.8:  # 수축 미완료
                continue
            if foreign_5d < 0 and inst_5d < 0:  # 수급 모두 이탈
                continue
            if score < 50:  # 기본 점수 미달
                continue
            
            # Final Score 계산
            # score (40%) + contraction_score (30%) + 수급 (20%) + 최신 보너스 (10%)
            contraction_score = (1 - contraction) * 100
            supply_score = min((foreign_5d + inst_5d) / 100000, 30)
            today_bonus = 10 if signal_date == today else 0
            
            final_score = (score * 0.4) + (contraction_score * 0.3) + (supply_score * 0.2 * 10) + today_bonus
            
            signals.append({
                'ticker': row['ticker'],
                'name': stock_names.get(row['ticker'], ''),
                'market': stock_markets.get(row['ticker'], ''),
                'signal_date': signal_date,
                'foreign_5d': foreign_5d,
                'inst_5d': inst_5d,
                'score': round(score, 1),
                'contraction_ratio': round(contraction, 2),
                'entry_price': round(row['entry_price'], 0) if pd.notna(row['entry_price']) else 0,
                'status': row['status'],
                'final_score': round(final_score, 1)
            })
        
        # final_score 기준 정렬 후 Top 20
        signals_sorted = sorted(signals, key=lambda x: x['final_score'], reverse=True)[:20]
        
        # Top 20에 대해 현재가 조회 및 수익률 계산
        if signals_sorted:
            # 티커 맵 로드 (Yahoo Finance용)
            ticker_map = {}
            ticker_map_file = 'kr_market/ticker_to_yahoo_map.csv'
            if os.path.exists(ticker_map_file):
                try:
                    tm_df = pd.read_csv(ticker_map_file, dtype=str)
                    ticker_map = dict(zip(tm_df['ticker'].str.zfill(6), tm_df['yahoo_ticker']))
                except:
                    pass
            
            # Yahoo 티커 변환
            tickers = [s['ticker'] for s in signals_sorted]
            yahoo_tickers = [ticker_map.get(t, f"{t}.KS") for t in tickers]
            
            # 현재가 조회
            current_prices = {}
            try:
                data = yf.download(yahoo_tickers, period='1d', progress=False)
                if not data.empty and 'Close' in data.columns:
                    closes = data['Close']
                    if isinstance(closes, pd.Series):
                        closes = closes.to_frame()
                        closes.columns = yahoo_tickers
                    for orig, yf_t in zip(tickers, yahoo_tickers):
                        if yf_t in closes.columns:
                            val = closes[yf_t].iloc[-1]
                            if not pd.isna(val):
                                current_prices[orig] = float(val)
            except Exception as e:
                print(f"Price fetch error: {e}")
            
            # 현재가 및 수익률 추가
            for sig in signals_sorted:
                entry = sig['entry_price']
                curr = current_prices.get(sig['ticker'], entry)
                sig['current_price'] = round(curr, 0)
                if entry > 0 and curr > 0:
                    sig['return_pct'] = round(((curr - entry) / entry) * 100, 2)
                else:
                    sig['return_pct'] = 0
        
        return jsonify({
            'signals': signals_sorted,
            'count': len(signals_sorted),
            'total_filtered': len(signals),
            'generated_at': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

### 2.2 Response Example

```json
{
  "signals": [
    {
      "ticker": "123410",
      "name": "코리아에프티",
      "market": "KOSDAQ",
      "signal_date": "2025-12-29",
      "foreign_5d": 1036584,
      "inst_5d": 223456,
      "score": 82.5,
      "contraction_ratio": 0.41,
      "entry_price": 8240,
      "current_price": 8180,
      "return_pct": -0.73,
      "status": "OPEN",
      "final_score": 71.3
    }
  ],
  "count": 20,
  "total_filtered": 35,
  "generated_at": "2026-01-03T10:00:00"
}
```

---

## 3. GET /api/kr/ai-analysis

Returns Top 10 VCP signals with GPT and Gemini AI recommendations.

### 3.1 Full Implementation

```python
KR_AI_ANALYSIS_FILE = 'kr_market/data/kr_ai_analysis.json'

@app.route('/api/kr/ai-analysis')
def kr_ai_analysis():
    """
    🧠 KR VCP Top 10 AI 매수/매도 분석
    
    Design Decisions:
    - 파일 기반 캐싱: 서버 재시작해도 유지
    - 시그널 날짜 기준 재생성: 새 시그널이 있을 때만 분석
    - Top 10만 분석: 비용/성능 최적화
    - GPT + Gemini 분석 결과 저장
    """
    try:
        from kr_market.kr_ai_analyzer import generate_ai_recommendations
        
        signals_file = 'kr_market/signals_log.csv'
        if not os.path.exists(signals_file):
            return jsonify({'error': 'signals_log.csv not found'}), 404
        
        # 현재 시그널의 최신 날짜 확인
        df = pd.read_csv(signals_file, encoding='utf-8-sig')
        df['ticker'] = df['ticker'].astype(str).str.zfill(6)
        
        # 가장 최근 시그널 날짜
        open_signals = df[df['status'] == 'OPEN']
        if open_signals.empty:
            return jsonify({'error': 'No open signals'}), 404
        
        latest_signal_date = open_signals['signal_date'].max()
        
        # 강제 새로고침 여부 확인
        force_refresh = request.args.get('refresh', 'false').lower() == 'true'
        
        # 저장된 분석 결과 확인 (refresh=true 시 캐시 무시)
        if not force_refresh and os.path.exists(KR_AI_ANALYSIS_FILE):
            try:
                with open(KR_AI_ANALYSIS_FILE, 'r', encoding='utf-8') as f:
                    cached_data = json.load(f)
                
                # 같은 날짜의 분석 결과가 있으면 반환
                if cached_data.get('signal_date') == latest_signal_date:
                    print(f"✅ Using cached AI analysis for {latest_signal_date}")
                    return jsonify(cached_data)
            except Exception as load_error:
                print(f"Cache load error: {load_error}")
        
        print(f"🔄 Generating new AI analysis for {latest_signal_date} (refresh={force_refresh})...")
        
        # 종목명/시장 로드
        stock_names = {}
        stock_markets = {}
        stocks_file = 'kr_market/korean_stocks_list.csv'
        if os.path.exists(stocks_file):
            stocks_df = pd.read_csv(stocks_file, encoding='utf-8-sig', dtype={'ticker': str})
            stocks_df['ticker'] = stocks_df['ticker'].astype(str).str.strip().str.zfill(6)
            stock_names = dict(zip(stocks_df['ticker'], stocks_df['name']))
            stock_markets = dict(zip(stocks_df['ticker'], stocks_df['market']))
        
        # VCP 필터링 및 Top 10 선정
        today = datetime.now().strftime('%Y-%m-%d')
        signals = []
        
        for _, row in open_signals.iterrows():
            score = float(row['score']) if pd.notna(row['score']) else 0
            contraction = float(row['contraction_ratio']) if pd.notna(row['contraction_ratio']) else 1
            foreign_5d = int(row['foreign_5d']) if pd.notna(row['foreign_5d']) else 0
            inst_5d = int(row['inst_5d']) if pd.notna(row['inst_5d']) else 0
            signal_date = row['signal_date']
            
            if contraction > 0.8 or (foreign_5d < 0 and inst_5d < 0) or score < 50:
                continue
            
            contraction_score = (1 - contraction) * 100
            supply_score = min((foreign_5d + inst_5d) / 100000, 30)
            today_bonus = 10 if signal_date == today else 0
            final_score = (score * 0.4) + (contraction_score * 0.3) + (supply_score * 0.2 * 10) + today_bonus
            
            signals.append({
                'ticker': row['ticker'],
                'name': stock_names.get(row['ticker'], ''),
                'market': stock_markets.get(row['ticker'], ''),
                'score': round(score, 1),
                'contraction_ratio': round(contraction, 2),
                'foreign_5d': foreign_5d,
                'inst_5d': inst_5d,
                'entry_price': round(row['entry_price'], 0) if pd.notna(row['entry_price']) else 0,
                'final_score': round(final_score, 1)
            })
        
        # Top 10
        top10 = sorted(signals, key=lambda x: x['final_score'], reverse=True)[:10]
        
        # AI 분석 수행
        result = generate_ai_recommendations(top10)
        
        # 결과에 시그널 날짜 추가
        result['signal_date'] = latest_signal_date
        
        # 파일에 저장 (최신 버전 + 히스토리 보관)
        os.makedirs(os.path.dirname(KR_AI_ANALYSIS_FILE), exist_ok=True)
        
        # 1. 최신 분석 파일 (항상 덮어쓰기)
        with open(KR_AI_ANALYSIS_FILE, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        # 2. 히스토리 파일 (날짜별 보관)
        history_dir = 'kr_market/data/history'
        os.makedirs(history_dir, exist_ok=True)
        history_file = f"{history_dir}/kr_ai_analysis_{latest_signal_date}.json"
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        print(f"✅ AI analysis saved to {KR_AI_ANALYSIS_FILE}")
        
        return jsonify(result)
        
    except Exception as e:
        print(f"KR AI Analysis error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
```

### 3.2 Key Features

- **Caching**: Uses `signal_date` to determine if cached data is valid
- **Force Refresh**: `?refresh=true` bypasses cache
- **History**: Saves dated copies to `kr_market/data/history/`
- **AI Integration**: Calls `generate_ai_recommendations()` from `kr_ai_analyzer.py`

---

## 4. GET /api/kr/ai-history-dates

Returns list of available AI analysis history dates.

### 4.1 Implementation

```python
@app.route('/api/kr/ai-history-dates')
def get_kr_ai_history_dates():
    """Get list of available KR AI analysis history dates"""
    try:
        history_dir = 'kr_market/data/history'
        
        if not os.path.exists(history_dir):
            return jsonify({'dates': []})
        
        dates = []
        for filename in os.listdir(history_dir):
            if filename.startswith('kr_ai_analysis_') and filename.endswith('.json'):
                # Extract date from filename
                date = filename.replace('kr_ai_analysis_', '').replace('.json', '')
                dates.append(date)
        
        # Sort descending (newest first)
        dates.sort(reverse=True)
        
        return jsonify({
            'dates': dates,
            'count': len(dates)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

---

## 5. GET /api/kr/ai-history/<date>

Returns AI analysis for a specific date.

### 5.1 Implementation

```python
@app.route('/api/kr/ai-history/<date>')
def get_kr_ai_history(date):
    """Get KR AI analysis for a specific date"""
    try:
        history_file = f'kr_market/data/history/kr_ai_analysis_{date}.json'
        
        if not os.path.exists(history_file):
            return jsonify({'error': f'No analysis found for {date}'}), 404
        
        with open(history_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return jsonify(data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

---

## 6. GET /api/kr/cumulative-return

Calculates cumulative portfolio returns based on signals.

### 6.1 Implementation (Condensed)

```python
@app.route('/api/kr/cumulative-return')
def get_kr_cumulative_return():
    """Calculate cumulative return for KR signals portfolio"""
    try:
        signals_path = 'kr_market/signals_log.csv'
        
        if not os.path.exists(signals_path):
            return jsonify({'error': 'No signals file'}), 404
        
        df = pd.read_csv(signals_path, encoding='utf-8-sig')
        df['ticker'] = df['ticker'].astype(str).str.zfill(6)
        
        # Get OPEN signals
        open_signals = df[df['status'] == 'OPEN']
        
        # Calculate returns for each signal
        returns = []
        for _, row in open_signals.iterrows():
            entry = row['entry_price']
            ticker = row['ticker']
            
            # Fetch current price
            try:
                from kr_market.kr_ai_analyzer import fetch_current_price
                current = fetch_current_price(ticker)
                if current > 0 and entry > 0:
                    ret = ((current - entry) / entry) * 100
                    returns.append({
                        'ticker': ticker,
                        'return_pct': round(ret, 2)
                    })
            except:
                pass
        
        # Calculate portfolio metrics
        if returns:
            avg_return = sum(r['return_pct'] for r in returns) / len(returns)
            winners = len([r for r in returns if r['return_pct'] > 0])
            losers = len([r for r in returns if r['return_pct'] <= 0])
            win_rate = (winners / len(returns)) * 100 if returns else 0
        else:
            avg_return = 0
            win_rate = 0
            winners = 0
            losers = 0
        
        return jsonify({
            'cumulative_return': round(avg_return, 2),
            'win_rate': round(win_rate, 1),
            'winners': winners,
            'losers': losers,
            'total_positions': len(returns),
            'positions': returns
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

---

## 7. GET /api/kr/market-gate

Returns market condition indicators.

### 7.1 Implementation

```python
@app.route('/api/kr/market-gate')
def get_kr_market_gate():
    """Get KR market condition gate status"""
    try:
        from kr_market.market_gate import get_market_status
        
        status = get_market_status()
        
        return jsonify({
            'status': status.get('status', 'UNKNOWN'),
            'kospi': status.get('kospi', {}),
            'kosdaq': status.get('kosdaq', {}),
            'usd_krw': status.get('usd_krw', 0),
            'foreign_net': status.get('foreign_net', 0),
            'gate_score': status.get('gate_score', 0),
            'recommendation': status.get('recommendation', ''),
            'generated_at': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

---

## 8. Constants and File Paths

```python
# KR Market file paths
KR_AI_ANALYSIS_FILE = 'kr_market/data/kr_ai_analysis.json'
KR_SIGNALS_FILE = 'kr_market/signals_log.csv'
KR_STOCKS_FILE = 'kr_market/korean_stocks_list.csv'
KR_TICKER_MAP_FILE = 'kr_market/ticker_to_yahoo_map.csv'
KR_HISTORY_DIR = 'kr_market/data/history'
```

---

## Next Steps

Continue to **[BLUEPRINT_04_BACKEND_AI_ANALYSIS.md](./BLUEPRINT_04_BACKEND_AI_ANALYSIS.md)** for the AI analysis logic implementation.
