# K-Stock 한국주식 — Google Cloud Run 배포 가이드

## 🏗️ 아키텍처

```
사용자 → Cloud Run (Frontend) → Cloud Run (Backend) → pykrx / Gemini / GPT
          Next.js :3000           Flask :8080
```

## 📋 사전 준비

1. **Google Cloud 계정** + 프로젝트 생성
2. **gcloud CLI** 설치: https://cloud.google.com/sdk/install
3. **API 키** → Google Secret Manager에 등록

```bash
# gcloud 로그인
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# Secret Manager에 API 키 등록
echo -n "YOUR_GOOGLE_API_KEY" | gcloud secrets create GOOGLE_API_KEY --data-file=-
echo -n "YOUR_OPENAI_API_KEY" | gcloud secrets create OPENAI_API_KEY --data-file=-
```

## 🚀 배포 (한 줄)

```bash
# 프로젝트 ID 설정 후 실행
export GCP_PROJECT=your-project-id
./deploy.sh
```

자동으로:
1. 백엔드 Docker 이미지 빌드 → Cloud Run 배포
2. 백엔드 URL 캡처
3. 프론트엔드 빌드 (백엔드 URL 주입) → Cloud Run 배포
4. 최종 URL 출력

## 🔧 수동 배포

### 백엔드
```bash
# 빌드
gcloud builds submit --tag gcr.io/PROJECT_ID/kstock-backend --dockerfile=Dockerfile.backend .

# 배포
gcloud run deploy kstock-backend \
  --image gcr.io/PROJECT_ID/kstock-backend \
  --region asia-northeast3 \
  --allow-unauthenticated \
  --port 8080 \
  --memory 1Gi \
  --set-secrets "GOOGLE_API_KEY=GOOGLE_API_KEY:latest,OPENAI_API_KEY=OPENAI_API_KEY:latest"
```

### 프론트엔드
```bash
cd frontend

# 빌드 (백엔드 URL 주입)
gcloud builds submit \
  --tag gcr.io/PROJECT_ID/kstock-frontend \
  --build-arg "NEXT_PUBLIC_API_URL=https://kstock-backend-xxx.run.app" .

# 배포
gcloud run deploy kstock-frontend \
  --image gcr.io/PROJECT_ID/kstock-frontend \
  --region asia-northeast3 \
  --allow-unauthenticated \
  --port 3000 \
  --memory 512Mi
```

## 📁 파일 구조

```
한국주식/
├── Dockerfile.backend      ← 백엔드 Docker (Gunicorn)
├── .dockerignore            ← 백엔드 제외 목록
├── deploy.sh                ← 원클릭 배포 스크립트
├── requirements.txt         ← Python 의존성 (완전)
├── flask_app.py             ← PORT 환경변수 지원
│
└── frontend/
    ├── Dockerfile           ← 프론트엔드 Docker (standalone)
    ├── .dockerignore        ← 프론트엔드 제외 목록
    └── next.config.ts       ← output: 'standalone' 추가
```

## 🔑 환경변수

| 변수 | 위치 | 값 |
|------|------|------|
| `GOOGLE_API_KEY` | Secret Manager | Gemini API 키 |
| `OPENAI_API_KEY` | Secret Manager | GPT API 키 |
| `PORT` | Cloud Run 자동주입 | 8080 |
| `NEXT_PUBLIC_API_URL` | 빌드 ARG | 백엔드 Cloud Run URL |

## ⚠️ 주의사항

- **최초 요청이 느릴 수 있음**: `min-instances=0` (비용 절감) → Cold Start ~10초
- 비용 절감이 필요없으면 `--min-instances 1` 로 변경
- 데이터 파일(`signals_log.csv` 등)은 컨테이너 재시작 시 초기화됨
  - 영구 저장이 필요하면 Cloud Storage 연동 필요
