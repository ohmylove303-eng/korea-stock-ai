# 한국주식 AI 분석 시스템 - 최종 설정 가이드

## 🎉 구현 완료!

전체 시스템이 성공적으로 구현되었습니다.

---

## 📊 현재 상태

### ✅ 완료된 항목
- [x] 백엔드 모듈 (config, signal_tracker, kr_ai_analyzer)
- [x] Flask 서버 (flask_app.py)
- [x] 프론트엔드 템플릿 (dashboard.html, index.html)
- [x] 데이터 수집 스크립트 (4개)
- [x] `.env` 파일 생성
- [x] **데이터 수집 백그라운드 실행 중** 🔄

### ⏳ 진행 중
- 데이터 수집 프로세스 (약 15-20분 소요)
  - 종목 리스트 생성
  - 일별 가격 데이터 (2년치)
  - 외인/기관 순매매 데이터

---

## 🔑 API 키 설정 (필수!)

`.env` 파일이 생성되었습니다. **실제 API 키를 입력**하세요:

```bash
# .env 파일 편집
nano /Users/jungsunghoon/Desktop/Desktop/한국주식/.env
```

또는 직접 파일을 열어서 수정:
- `GOOGLE_API_KEY` → https://aistudio.google.com/apikey 에서 발급
- `OPENAI_API_KEY` → https://platform.openai.com/api-keys 에서 발급

---

## 📋 데이터 수집 진행 상황 확인

```bash
cd "/Users/jungsunghoon/Desktop/Desktop/한국주식"

# 실시간 로그 확인
tail -f data_collection.log

# 또는 간단 확인
tail -20 data_collection.log
```

---

## 🚀 서버 실행 (데이터 수집 완료 후)

### 1. 데이터 수집 완료 확인
```bash
# 생성된 파일 확인
ls -lh kr_market/*.csv

# 다음 파일들이 있어야 함:
# - korean_stocks_list.csv
# - daily_prices.csv
# - all_institutional_trend_data.csv
```

### 2. 서버 시작
```bash
python3 flask_app.py
```

### 3. 브라우저 접속
```
http://localhost:5001/app
```

---

## 🎯 대시보드 사용법

1. **VCP 스캔 실행** 버튼 클릭
   → `signals_log.csv` 생성 및 VCP 패턴 탐지

2. **AI 분석 실행** 버튼 클릭
   → Gemini + GPT 추천 생성

3. **새로고침** 버튼
   → 최신 시그널 조회

---

## ⚠️ 문제 해결

### 데이터 수집이 너무 오래 걸리는 경우
- 네트워크 연결 확인
- `Ctrl+C`로 중단 후 나중에 재실행 가능

### API 키 오류
- `.env` 파일에 실제 키가 입력되었는지 확인
- 따옴표 없이 키만 입력

### 서버 시작 실패
- `pip install -r requirements.txt` 재실행
- Python 3.11+ 사용 확인

---

## 📞 다음 단계

데이터 수집이 완료되면:
1. ✅ API 키 설정 확인
2. ✅ `python3 flask_app.py` 실행
3. ✅ http://localhost:5001/app 접속
4. ✅ VCP 스캔 테스트
5. ✅ AI 분석 테스트

**현재 백그라운드에서 데이터 수집 진행 중입니다!**
약 15-20분 후 완료 예정.
