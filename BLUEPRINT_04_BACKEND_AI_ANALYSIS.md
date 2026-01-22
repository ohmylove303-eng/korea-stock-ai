# KR Market AI Stock Analysis System - Blueprint Part 4: AI Analysis Module

> **Version**: 1.0  
> **Last Updated**: 2026-01-03  
> **File**: `kr_market/kr_ai_analyzer.py` (398 lines)

---

## 1. Module Overview

This module is the **brain** of the system, providing dual AI analysis using:

- **Gemini 3.0 Flash Preview** - Real-time Google Search grounding for news
- **GPT-5.2** - Technical and fundamental analysis with provided news

### 1.1 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  generate_ai_recommendations()              │
│                        (Main Orchestrator)                  │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│ fetch_market  │   │    fetch_     │   │ fetch_current │
│   _indices()  │   │ fundamentals()│   │    _price()   │
│  (yfinance)   │   │   (pykrx)     │   │   (pykrx)     │
└───────────────┘   └───────────────┘   └───────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │ analyze_with_   │
                    │    gemini()     │  ──→ Returns: Recommendation + News
                    │ (Google Search) │
                    └─────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │ analyze_with_   │
                    │     gpt()       │  ──→ Returns: Recommendation
                    │ (Uses Gemini    │
                    │   news input)   │
                    └─────────────────┘
```

---

## 2. Full Source Code

### 2.1 Imports and Constants

```python
"""
KR VCP AI Analyzer
GPT-4 + Gemini를 활용한 VCP 종목 AI 분석
"""
import os
import json

from datetime import datetime
from typing import Dict, List, Optional
from dotenv import load_dotenv
import yfinance as yf

load_dotenv()

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
```

---

### 2.2 Market Indices Fetching

```python
def fetch_market_indices() -> Dict:
    """KOSPI, KOSDAQ 지수 조회"""
    indices = {
        'kospi': {'value': 0, 'change_pct': 0},
        'kosdaq': {'value': 0, 'change_pct': 0}
    }
    
    try:
        # KOSPI: ^KS11, KOSDAQ: ^KQ11
        tickers = ['^KS11', '^KQ11']
        data = yf.download(tickers, period='2d', progress=False)
        
        if not data.empty and 'Close' in data.columns:
            closes = data['Close']
            
            for ticker, name in [('^KS11', 'kospi'), ('^KQ11', 'kosdaq')]:
                if ticker in closes.columns and len(closes[ticker].dropna()) >= 2:
                    today = closes[ticker].dropna().iloc[-1]
                    prev = closes[ticker].dropna().iloc[-2]
                    change_pct = ((today - prev) / prev) * 100
                    indices[name] = {
                        'value': round(float(today), 2),
                        'change_pct': round(change_pct, 2)
                    }
    except Exception as e:
        print(f"Market indices fetch error: {e}")
    
    return indices
```

---

### 2.3 Current Price Fetching (pykrx)

```python
def fetch_current_price(ticker: str) -> int:
    """pykrx를 통한 실시간 현재가 조회"""
    try:
        from pykrx import stock
        from datetime import datetime
        today = datetime.now().strftime("%Y%m%d")
        
        # 오늘 날짜의 시세 조회 (장중이면 실시간, 장 마감이면 종가)
        df = stock.get_market_ohlcv(today, today, ticker)
        
        if not df.empty:
             return int(df['종가'].iloc[-1])
        
        # 데이터가 없으면(휴장일 등), 최근 영업일 기준 조회
        return int(stock.get_market_price_change_by_ticker(today, today).loc[ticker, '종가'])
        
    except Exception as e:
        print(f"Current price fetch error for {ticker}: {e}")
        return 0
```

---

### 2.4 Fundamentals Fetching (pykrx)

```python
def fetch_fundamentals(ticker: str, name: str) -> Dict:
    """pykrx를 통한 주요 재무지표(PER, PBR, ROE, 시총) 조회"""
    fundamentals = {
        'per': 'N/A',
        'pbr': 'N/A',
        'roe': 'N/A',
        'eps': 'N/A',
        'bps': 'N/A',
        'div_yield': 'N/A',
        'marcap': 'N/A'
    }
    
    try:
        from pykrx import stock
        from datetime import datetime, timedelta
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=7)).strftime("%Y%m%d")
        
        # 1. 시가총액 정보
        df_cap = stock.get_market_cap(start_date, end_date, ticker)
        if not df_cap.empty:
            last_cap = df_cap.iloc[-1]
            fundamentals['marcap'] = f"{last_cap['시가총액'] // 100000000:,.0f}억원"
            
        # 2. 투자지표 (PER, PBR, EPS, BPS, DIV)
        df_fund = stock.get_market_fundamental(start_date, end_date, ticker)
        if not df_fund.empty:
            last_fund = df_fund.iloc[-1]
            fundamentals['per'] = str(last_fund['PER']) if last_fund['PER'] != 0 else 'N/A'
            fundamentals['pbr'] = str(last_fund['PBR']) if last_fund['PBR'] != 0 else 'N/A'
            fundamentals['eps'] = f"{int(last_fund['EPS']):,}원" if last_fund['EPS'] != 0 else 'N/A'
            fundamentals['bps'] = f"{int(last_fund['BPS']):,}원" if last_fund['BPS'] != 0 else 'N/A'
            fundamentals['div_yield'] = f"{last_fund['DIV']:.2f}%" if last_fund['DIV'] != 0 else '0.00%'
            
            # ROE 계산 (PBR / PER * 100) - 대략적인 수치
            if fundamentals['per'] != 'N/A' and fundamentals['pbr'] != 'N/A':
                per = float(fundamentals['per'])
                pbr = float(fundamentals['pbr'])
                if per != 0:
                    roe = (pbr / per) * 100
                    fundamentals['roe'] = f"{roe:.2f}%"
                
    except Exception as e:
        print(f"Fundamentals fetch error for {ticker}: {e}")
        
    return fundamentals
```

---

### 2.5 GPT-5.2 Analysis Function

```python
def analyze_with_gpt(signal_data: Dict, market_indices: Dict, news: List[Dict]) -> Dict:
    """OpenAI GPT-5.2 flagship model analysis"""
    if not OPENAI_API_KEY:
        return {'action': 'N/A', 'confidence': 0, 'reason': 'API 키 없음'}
    
    try:
        import openai
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        
        # 뉴스 요약 (제목 + 내용)
        news_text = "\n".join([
            f"- 제목: {n['title']}\n  요약: {n.get('summary', '내용 없음')}" 
            for n in news[:3]
        ]) if news else "최근 뉴스 없음"
        
        prompt = f"""당신은 한국 주식시장 전문 애널리스트입니다. 아래 데이터를 기반으로 매수/관망/매도 추천을 해주세요.

## 분석 시 핵심 가이드라인
1. **뉴스 신뢰**: 제공된 뉴스는 Gemini 3.0이 검증한 최신 뉴스입니다. 적극적으로 참고하세요.
2. **호재 반영**: 실적 개선, 대규모 수주, 신사업 진출 등의 구체적인 호재가 있다면, 수급이 다소 부족('강한 수급' 기준 미달)하더라도 '매수' 관점을 유지하세요.
3. **종합 판단**: VCP 기술적 지표와 뉴스 모멘텀을 50:50 비중으로 고려하여 판단하세요. 수급은 보조 지표로 활용하세요.

## 종목 기본 정보
- 티커: {signal_data.get('ticker')}
- 종목명: {signal_data.get('name')}
- VCP Score: {signal_data.get('score')}
- 수축비율 (낮을수록 좋음): {signal_data.get('contraction_ratio')}
- 외국인 5일 순매수: {signal_data.get('foreign_5d'):,}주
- 기관 5일 순매수: {signal_data.get('inst_5d'):,}주
- 진입가: ₩{signal_data.get('entry_price'):,}
- 현재가: ₩{signal_data.get('current_price', 0):,} (수익률: {signal_data.get('return_pct', 0):+.2f}%)

## 재무지표 (KRX 공식 데이터)
- 시가총액: {signal_data.get('fundamentals', {}).get('marcap', 'N/A')}
- PER: {signal_data.get('fundamentals', {}).get('per', 'N/A')}
- PBR: {signal_data.get('fundamentals', {}).get('pbr', 'N/A')}
- ROE: {signal_data.get('fundamentals', {}).get('roe', 'N/A')}
- 배당수익률: {signal_data.get('fundamentals', {}).get('div_yield', 'N/A')}

## 시장 현황
- KOSPI: {market_indices['kospi']['value']} ({market_indices['kospi']['change_pct']:+.2f}%)
- KOSDAQ: {market_indices['kosdaq']['value']} ({market_indices['kosdaq']['change_pct']:+.2f}%)

## 수집된 뉴스 (Gemini Grounding)
{news_text}

## 분석 참고
- 뉴스 '요약' 내용을 꼼꼼히 읽고, 해당 이슈가 기업 실적이나 주가에 미칠 구체적인 영향을 분석하세요.

## 응답 형식 (JSON)
{{"action": "BUY/HOLD/SELL", "confidence": 0-100, "reason": "한줄 이유"}}

JSON만 응답하세요:"""

        response = client.chat.completions.create(
            model="gpt-5.2",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_completion_tokens=200,
            response_format={"type": "json_object"}
        )
        
        result_text = response.choices[0].message.content.strip()
        result = json.loads(result_text)
        return {
            'action': result.get('action', 'HOLD'),
            'confidence': result.get('confidence', 50),
            'reason': result.get('reason', '')
        }
        
    except Exception as e:
        print(f"GPT analysis error: {e}")
    
    return {'action': 'HOLD', 'confidence': 50, 'reason': '분석 실패'}
```

---

### 2.6 Gemini 3.0 Analysis Function (with Google Search Grounding)

```python
def analyze_with_gemini(signal_data: Dict, market_indices: Dict, news: List[Dict]) -> Dict:
    """Google Gemini 3.0 Flash Preview with Google Search grounding"""
    if not GOOGLE_API_KEY:
        return {'action': 'N/A', 'confidence': 0, 'reason': 'API 키 없음'}
    
    try:
        from google import genai
        client = genai.Client(api_key=GOOGLE_API_KEY)
        model_id = 'gemini-3-flash-preview'
        
        prompt = f"""당신은 한국 주식시장 전문 애널리스트입니다. **구글 실시간 검색**을 적극 활용하여 최신 정보를 수집하고 매수/관망/매도 추천을 해주세요.
 
## 분석 시 핵심 가이드라인
1. **Google Search 필수**: {signal_data.get('name')}({signal_data.get('ticker')})의 가장 최신 뉴스(실적, 공시, 수급, 업황)를 반드시 검색하세요.
2. **뉴스 리스트 작성**: 검색을 통해 찾은 핵심 뉴스 3~5개를 제목, **핵심 내용 요약(1~2문장)**, 정확한 출처(URL)와 함께 응답에 포함하세요.
3. **종합 판단**: 검색된 최신 뉴스, 현재 수급(외국인/기관), VCP Score를 종합하여 최종 의견을 제시하세요.
 
## 제공 수급 데이터
- VCP Score: {signal_data.get('score')}
- 수축비율: {signal_data.get('contraction_ratio')}
- 외국인 5일 순매수: {signal_data.get('foreign_5d'):,}주
- 기관 5일 순매수: {signal_data.get('inst_5d'):,}주
- 진입가: ₩{signal_data.get('entry_price'):,}
- 현재가: ₩{signal_data.get('current_price', 0):,} (수익률: {signal_data.get('return_pct', 0):+.2f}%)
- 재무(PER/PBR 등): {signal_data.get('fundamentals')}
 
## 응답 형식 (JSON)
반드시 아래 JSON 형식으로만 응답하세요. 다른 설명은 포함하지 마세요.
{{
  "recommendation": {{
      "action": "BUY/HOLD/SELL",
      "confidence": 0-100,
      "reason": "한줄 핵심 근거"
  }},
  "news_found": [
      {{ "title": "뉴스 제목1", "summary": "뉴스 핵심 내용 1~2문장 요약", "url": "뉴스 URL1" }},
      {{ "title": "뉴스 제목2", "summary": "뉴스 핵심 내용 1~2문장 요약", "url": "뉴스 URL2" }}
  ]
}}"""

        # KEY: Enable Google Search grounding
        response = client.models.generate_content(
            model=model_id,
            contents=prompt,
            config={
                'tools': [{'google_search': {}}],  # Enable search
                'temperature': 0.1, 
                'response_mime_type': 'application/json'
            }
        )
        
        result_text = response.text.strip()
        
        # JSON 파싱
        try:
            result = json.loads(result_text)
            news_list = result.get('news_found', [])
            
            return {
                'recommendation': result.get('recommendation', {
                    'action': 'HOLD', 
                    'confidence': 50, 
                    'reason': '분석 실패'
                }),
                'grounding_news': news_list
            }
        except json.JSONDecodeError:
            # Handle markdown code blocks
            import re
            json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                return {
                    'recommendation': result.get('recommendation', {}),
                    'grounding_news': result.get('news_found', [])
                }
            return {
                'recommendation': {'action': 'HOLD', 'confidence': 50, 'reason': 'JSON 파싱 실패'},
                'grounding_news': []
            }
            
    except Exception as e:
        print(f"Gemini analysis error: {e}")
    
    return {
        'recommendation': {'action': 'HOLD', 'confidence': 50, 'reason': '분석 실패'},
        'grounding_news': []
    }
```

---

### 2.7 Main Orchestrator Function

```python
def generate_ai_recommendations(vcp_signals: List[Dict]) -> Dict:
    """VCP 시그널에 대한 AI 추천 생성 (Main Entry Point)"""
    
    # 1. 시장 지수 조회
    market_indices = fetch_market_indices()
    
    # 2. 각 종목별 분석
    analyzed_signals = []
    
    for signal in vcp_signals[:10]:  # Top 10만 분석
        ticker = signal.get('ticker', '')
        name = signal.get('name', '')
        
        # 재무 데이터 수집
        fundamentals = fetch_fundamentals(ticker, name)
        
        # 시그널 데이터에 재무정보 추가
        signal_with_fund = {
            **signal,
            'fundamentals': fundamentals
        }

        # 실시간 현재가 및 수익률 조회
        current_price = fetch_current_price(ticker)
        if current_price > 0 and signal_with_fund.get('entry_price', 0) > 0:
            entry = signal_with_fund['entry_price']
            ret = ((current_price - entry) / entry) * 100
            signal_with_fund['current_price'] = current_price
            signal_with_fund['return_pct'] = round(ret, 2)
        elif current_price > 0:
            signal_with_fund['current_price'] = current_price
        
        # 1. Gemini 먼저 (구글 검색 결과 확보)
        gemini_res = analyze_with_gemini(signal_with_fund, market_indices, [])
        grounding_news = gemini_res.get('grounding_news', [])
        
        # 2. GPT (Gemini 뉴스 전달)
        gpt_rec = analyze_with_gpt(signal_with_fund, market_indices, grounding_news)
        
        analyzed_signals.append({
            **signal_with_fund,
            'news': grounding_news,
            'gpt_recommendation': gpt_rec,
            'gemini_recommendation': gemini_res.get('recommendation', {})
        })
    
    return {
        'market_indices': market_indices,
        'signals': analyzed_signals,
        'generated_at': datetime.now().isoformat(),
        'signal_date': datetime.now().strftime('%Y-%m-%d')
    }
```

---

## 3. Key Design Decisions

### 3.1 Dual AI Cross-Validation

| Aspect | Gemini 3.0 | GPT-5.2 |
|:---|:---|:---|
| **Role** | News researcher | Technical analyst |
| **Special Ability** | Google Search grounding | Structured reasoning |
| **Input** | VCP data only | VCP data + Gemini's news |
| **Output** | Recommendation + News list | Recommendation |

### 3.2 Analysis Flow Priority

1. **Gemini First**: Gemini must run first to fetch real-time news via Google Search
2. **News Handoff**: Gemini's `news_found` is passed to GPT
3. **Dual Opinions**: Both AI opinions are preserved for the frontend

### 3.3 Prompt Engineering Principles

- **Trust News**: GPT is instructed to trust Gemini-verified news
- **50:50 Balance**: Technical indicators and news momentum are weighted equally
- **Supply as Secondary**: Institutional flow is used as a supporting indicator

---

## 4. Testing

```python
if __name__ == '__main__':
    test_signal = {
        'ticker': '005930',
        'name': '삼성전자',
        'score': 65,
        'contraction_ratio': 0.55,
        'foreign_5d': 150000,
        'inst_5d': 80000,
        'entry_price': 55000
    }
    
    result = generate_ai_recommendations([test_signal])
    print(json.dumps(result, ensure_ascii=False, indent=2))
```

---

## Next Steps

Continue to **[BLUEPRINT_05_BACKEND_DATA_SIGNALS.md](./BLUEPRINT_05_BACKEND_DATA_SIGNALS.md)** for VCP signal tracking and screener logic.
