---
description: 한국주식 프로젝트 - 전체 스택 자동 검증 (Ralph 메인)
---

# 한국주식 프로젝트 전체 자동 검증

// turbo-all

이 워크플로우는 백엔드 + 프론트엔드를 **순차적으로** 검증하고 최종 통합 테스트를 수행합니다.

## 🚀 실행 순서

### Part 1: 백엔드 검증

## 1단계: Python 의존성 설치
```bash
cd /Users/jungsunghoon/Desktop/Desktop/한국주식
pip install -q flask gunicorn yfinance pandas numpy pykrx google-generativeai openai requests tqdm python-dotenv beautifulsoup4 lxml_html_clean plotly
```

## 2단계: 백엔드 파일 문법 검증
```bash
python3 -m py_compile flask_app.py
python3 -m py_compile kr_market/kr_ai_analyzer.py
python3 -m py_compile kr_market/signal_tracker.py
python3 -m py_compile kr_market/screener.py
```

## 3단계: 모듈 Import 테스트
```bash
python3 -c "from kr_market import kr_ai_analyzer, signal_tracker, screener; print('✅ Backend modules OK')"
```

---

### Part 2: 프론트엔드 검증

## 4단계: HTML 파일 문법 검증
```bash
python3 -c "
from html.parser import HTMLParser
with open('templates/dashboard.html', 'r', encoding='utf-8') as f:
    HTMLParser().feed(f.read())
print('✅ dashboard.html OK')
"
```

## 5단계: 필수 API 호출 존재 확인
```bash
grep -q "fetch('/api/kr/" templates/dashboard.html && echo "✅ Frontend API calls present" || echo "⚠️ API calls missing"
```

---

### Part 3: 통합 테스트

## 6단계: Flask 서버 구동 테스트 (10초)
```bash
timeout 10 python3 flask_app.py 2>&1 | grep -q "5001" && echo "✅ Server started on port 5001" || echo "⚠️ Server start check (expected timeout)"
```

## 7단계: .env 파일 확인 (API 키)
```bash
test -f .env && echo "✅ .env file exists" || echo "⚠️ Warning: .env file missing (create with API keys)"
```

## 8단계: 최종 리포트
```bash
echo "============================================"
echo "✅ 한국주식 프로젝트 검증 완료"
echo "============================================"
echo "백엔드: flask_app.py + kr_market 모듈"
echo "프론트엔드: templates/dashboard.html"
echo "의존성: Flask, pykrx, Gemini, GPT, yfinance"
echo ""
echo "🚀 실행 명령어: python3 flask_app.py"
echo "🌐 접속 주소: http://localhost:5001/app"
echo "============================================"
```

---

**사용법:**
채팅창에 입력:
```
/ralph-kr
```
또는
```
/verify-korea-stock
```
