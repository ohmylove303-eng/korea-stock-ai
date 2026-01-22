# 🚀 Render 배포 가이드

## 프로젝트 구조
```
한국주식/
├── flask_app.py          # 백엔드 메인
├── requirements.txt      # Python 의존성
├── render.yaml           # Render Blueprint
├── frontend/             # Next.js 프론트엔드
│   └── next.config.mjs   # 프론트엔드 설정
└── kr_market/            # 핵심 로직
```

---

## 1단계: GitHub 업로드

```bash
cd /Users/jungsunghoon/Desktop/Desktop/한국주식

# Git 초기화 (처음이면)
git init
git branch -M main

# 커밋
git add .
git commit -m "Render 배포 준비 완료"

# GitHub 레포 생성 후 (예: korea-stock-ai)
git remote add origin https://github.com/YOUR_USERNAME/korea-stock-ai.git
git push -u origin main
```

---

## 2단계: Render 배포 (Blueprint 사용)

### 방법 A: 자동 배포 (추천)
1. [Render Dashboard](https://dashboard.render.com) 접속
2. **New+** → **Blueprint**
3. GitHub 레포 연결
4. `render.yaml` 자동 감지됨 → **Apply**

### 방법 B: 수동 배포

#### 백엔드 (Flask)
| 항목 | 값 |
|------|-----|
| Name | `korea-stock-backend` |
| Runtime | Python 3 |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `gunicorn flask_app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120` |

#### 프론트엔드 (Next.js)
| 항목 | 값 |
|------|-----|
| Name | `korea-stock-frontend` |
| Root Directory | `frontend` |
| Build Command | `npm install && npm run build` |
| Start Command | `npm run start` |

---

## 3단계: 환경 변수 설정

Render Dashboard → 각 서비스 → **Environment** 에서 추가:

### 백엔드 필수 변수
| Key | 설명 |
|-----|------|
| `GEMINI_API_KEY` | Google Gemini API 키 |
| `OPENAI_API_KEY` | OpenAI API 키 |
| `FRED_API_KEY` | FRED 경제 데이터 키 (선택) |

### 프론트엔드 필수 변수
| Key | 값 |
|-----|------|
| `NEXT_PUBLIC_API_URL` | `https://korea-stock-backend.onrender.com` |

---

## 4단계: 배포 완료 확인

1. **백엔드 테스트**:
   ```
   https://korea-stock-backend.onrender.com/api/kr/market-status
   ```

2. **프론트엔드 접속**:
   ```
   https://korea-stock-frontend.onrender.com
   ```

---

## ⚠️ 주의사항

1. **첫 배포는 5-10분 소요** (의존성 설치)
2. **무료 플랜은 15분 비활성 시 슬립** → 첫 접속 느림
3. `.env` 파일은 **절대 커밋 금지** (이미 .gitignore에 추가됨)
4. 백엔드 배포가 먼저 완료된 후 프론트엔드 환경변수 설정

---

## 문제 해결

### "Module not found" 에러
→ `requirements.txt`에 패키지 추가 후 재배포

### API 연결 실패
→ `NEXT_PUBLIC_API_URL`이 `https://`로 시작하는지 확인

### 차트 안 뜸
→ 백엔드 Health Check: `/api/kr/signals` 응답 확인
