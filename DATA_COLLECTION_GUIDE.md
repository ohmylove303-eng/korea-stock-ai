# 한국주식 AI 분석 시스템 - 데이터 수집 가이드

## 개요
시스템이 작동하려면 3개의 필수 데이터 파일이 필요합니다:
1. `korean_stocks_list.csv` - 전체 종목 리스트
2. `daily_prices.csv` - 2년치 일봉 데이터
3. `all_institutional_trend_data.csv` - 외인/기관 순매매 데이터

## 🚀 빠른 시작 (전체 자동 수집)

```bash
cd /Users/jungsunghoon/Desktop/Desktop/한국주식

# 전체 데이터 한 번에 수집 (약 15-20분 소요)
python3 kr_market/scripts/collect_all_data.py
```

## 📋 개별 스크립트 실행

### 1. 종목 리스트 생성 (~1분)
```bash
python3 kr_market/scripts/create_stock_list.py
```
**결과**: `kr_market/korean_stocks_list.csv` (~2,500개 종목)

### 2. 일별 가격 데이터 수집 (5-10분)
```bash
python3 kr_market/scripts/create_daily_prices.py
```
**결과**: `kr_market/daily_prices.csv` (~120MB, 2년치 OHLCV)

### 3. 수급 데이터 수집 (10-15분)
```bash
python3 kr_market/scripts/create_institutional_data.py
```
**결과**: `kr_market/all_institutional_trend_data.csv` (외인/기관 순매매)

## ⚠️ 주의사항

1. **네트워크 연결** 필요 (pykrx, 네이버 금융 API)
2. **시간 소요**: 전체 약 15-20분
3. **재실행 가능**: 데이터가 오래되면 다시 실행하세요

## 📊 생성되는 파일 구조

### korean_stocks_list.csv
```csv
ticker,name,market
005930,삼성전자,KOSPI
000270,기아,KOSPI
```

### daily_prices.csv
```csv
ticker,date,open,high,low,close,current_price,volume
005930,2024-01-02,72000,73000,71500,72500,72500,15000000
```

### all_institutional_trend_data.csv
```csv
ticker,name,scrape_date,foreign_net_buy_5d,institutional_net_buy_5d,supply_demand_index
005930,삼성전자,2026-01-07,150000,80000,65.5
```

## 🔄 데이터 업데이트 주기

- **일별 가격**: 매일 장 마감 후
- **수급 데이터**: 매일 또는 주 1회
- **종목 리스트**: 월 1회

## 다음 단계

데이터 수집 완료 후:
```bash
# 1. API 키 설정
cp .env.example .env
# .env 파일에 GOOGLE_API_KEY, OPENAI_API_KEY 입력

# 2. 서버 실행
python3 flask_app.py

# 3. 브라우저 접속
# http://localhost:5001/app
```
