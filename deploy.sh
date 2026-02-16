#!/bin/bash
# ============================================================
# K-Stock Cloud Run 배포 스크립트
# 
# 사용법:
#   1. gcloud CLI 로그인: gcloud auth login
#   2. 프로젝트 설정: gcloud config set project YOUR_PROJECT_ID
#   3. 실행: ./deploy.sh
#
# 환경변수 (필수):
#   GCP_PROJECT  — Google Cloud 프로젝트 ID
#   GCP_REGION   — 배포 리전 (기본: asia-northeast3 = 서울)
# ============================================================

set -e

# === 설정 ===
PROJECT_ID="${GCP_PROJECT:-adroit-particle-470608-v2}"
REGION="${GCP_REGION:-asia-northeast3}"
BACKEND_SERVICE="kstock-backend"
FRONTEND_SERVICE="kstock-frontend"
BACKEND_IMAGE="gcr.io/${PROJECT_ID}/${BACKEND_SERVICE}"
FRONTEND_IMAGE="gcr.io/${PROJECT_ID}/${FRONTEND_SERVICE}"

echo "============================================"
echo "🚀 K-Stock Cloud Run 배포"
echo "   Project: ${PROJECT_ID}"
echo "   Region:  ${REGION}"
echo "============================================"

# === API 활성화 ===
echo ""
echo "📦 필요한 API 활성화..."
gcloud services enable \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    containerregistry.googleapis.com \
    artifactregistry.googleapis.com \
    --project="${PROJECT_ID}" --quiet

# ============================================================
# 1. 백엔드 배포
# ============================================================
echo ""
echo "🔧 [1/2] 백엔드 빌드 & 배포..."
echo "   이미지: ${BACKEND_IMAGE}"

gcloud builds submit \
    --tag "${BACKEND_IMAGE}" \
    --project="${PROJECT_ID}" \
    --dockerfile="Dockerfile.backend" \
    .

gcloud run deploy "${BACKEND_SERVICE}" \
    --image "${BACKEND_IMAGE}" \
    --region "${REGION}" \
    --platform managed \
    --allow-unauthenticated \
    --port 8080 \
    --memory 1Gi \
    --cpu 1 \
    --timeout 300 \
    --min-instances 0 \
    --max-instances 3 \
    --set-env-vars "FLASK_DEBUG=false" \
    --project="${PROJECT_ID}" \
    --quiet

# 백엔드 URL 가져오기
BACKEND_URL=$(gcloud run services describe "${BACKEND_SERVICE}" \
    --region "${REGION}" \
    --project="${PROJECT_ID}" \
    --format="value(status.url)")

echo "✅ 백엔드 배포 완료: ${BACKEND_URL}"

# ============================================================
# 2. 프론트엔드 배포
# ============================================================
echo ""
echo "🎨 [2/2] 프론트엔드 빌드 & 배포..."
echo "   이미지: ${FRONTEND_IMAGE}"
echo "   API URL: ${BACKEND_URL}"

cd frontend

gcloud builds submit \
    --tag "${FRONTEND_IMAGE}" \
    --project="${PROJECT_ID}" \
    --build-arg "NEXT_PUBLIC_API_URL=${BACKEND_URL}" \
    .

gcloud run deploy "${FRONTEND_SERVICE}" \
    --image "${FRONTEND_IMAGE}" \
    --region "${REGION}" \
    --platform managed \
    --allow-unauthenticated \
    --port 3000 \
    --memory 512Mi \
    --cpu 1 \
    --timeout 60 \
    --min-instances 0 \
    --max-instances 5 \
    --project="${PROJECT_ID}" \
    --quiet

FRONTEND_URL=$(gcloud run services describe "${FRONTEND_SERVICE}" \
    --region "${REGION}" \
    --project="${PROJECT_ID}" \
    --format="value(status.url)")

cd ..

# ============================================================
# 완료 요약
# ============================================================
echo ""
echo "============================================"
echo "✅ 배포 완료!"
echo ""
echo "   🔧 백엔드:   ${BACKEND_URL}"
echo "   🎨 프론트엔드: ${FRONTEND_URL}"
echo ""
echo "   API 테스트: curl ${BACKEND_URL}/api/kr/signals"
echo "   대시보드:   ${FRONTEND_URL}"
echo "============================================"
