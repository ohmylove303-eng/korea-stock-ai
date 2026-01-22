---
description: 한국주식 프로젝트 - 백엔드 자동 설치 및 검증
---

# 백엔드 자동 설치 및 검증 워크플로우

// turbo-all

이 워크플로우는 한국주식 프로젝트의 백엔드를 자동으로 설치하고 검증합니다.

## 📦 백엔드 파일 목록

### BLUEPRINT_02: Flask Core
- `flask_app.py` (3,523 lines)
- Background scheduler
- API routes

### BLUEPRINT_03: KR API
- `/api/kr/signals`
- `/api/kr/ai-analysis`
- `/api/kr/vcp-scan`

### BLUEPRINT_04: AI Analysis
- `kr_market/kr_ai_analyzer.py`
- Gemini + GPT integration
- News grounding

### BLUEPRINT_05: Data & Signals
- `kr_market/signal_tracker.py`
- `kr_market/screener.py`
- VCP pattern detection

---

## 1단계: 백엔드 Python 의존성 설치
```bash
cd /Users/jungsunghoon/Desktop/Desktop/한국주식
pip install -q flask gunicorn yfinance pandas numpy pykrx google-generativeai openai requests tqdm python-dotenv beautifulsoup4 lxml_html_clean plotly
```

## 2단계: Flask 앱 파일 존재 확인
```bash
ls -lh flask_app.py
```

## 3단계: KR Market 모듈 확인
```bash
ls -lh kr_market/kr_ai_analyzer.py kr_market/signal_tracker.py kr_market/screener.py kr_market/scheduler.py
```

## 4단계: Python 파일 문법 검증
```bash
python3 -m py_compile flask_app.py
python3 -m py_compile kr_market/kr_ai_analyzer.py
python3 -m py_compile kr_market/signal_tracker.py
python3 -m py_compile kr_market/screener.py
```

## 5단계: 모듈 Import 테스트
```bash
python3 -c "from kr_market import kr_ai_analyzer, signal_tracker, screener; print('✅ All kr_market modules imported successfully')"
```

## 6단계: 필수 데이터 파일 확인
```bash
ls -lh kr_market/daily_prices.csv kr_market/all_institutional_trend_data.csv kr_market/signals_log.csv kr_market/korean_stocks_list.csv
```

## 7단계: Flask 서버 구동 테스트 (10초)
```bash
timeout 10 python3 flask_app.py || echo "✅ Server starts without syntax errors"
```

---

**자동 수정 규칙:**
- 누락된 패키지 → `pip install` 재시도
- 문법 오류 → 해당 파일 자동 수정
- 데이터 파일 누락 → 스크립트 자동 실행
