#!/bin/bash
# ============================================================
# K-Stock 데일리 파이프라인
# 매일 장 마감 후 실행 (15:35 KST)
# ============================================================
#
# 실행 순서:
#   1. quick_scan.py      → signals_log.csv (VCP 스캔)
#   2. run_v2_scoring.py  → jongga_v2_latest.json (12점 채점)  
#   3. refresh_ai_cache.py → kr_ai_analysis.json (AI 분석 + 시장 논평)
#
# 사용법:
#   수동 실행: ./run_daily_pipeline.sh
#   자동 실행: launchd (com.kstock.daily-pipeline.plist)
# ============================================================

set -e  # 에러 시 중단

# 프로젝트 경로
PROJECT_DIR="$HOME/Desktop/한국주식"
VENV_DIR="$PROJECT_DIR/.venv"
LOG_DIR="$PROJECT_DIR/logs"

# 로그 디렉토리 생성
mkdir -p "$LOG_DIR"

# 타임스탬프
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="$LOG_DIR/pipeline_${TIMESTAMP}.log"

# 로깅 함수
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# ============================================================
log "============================================"
log "🚀 K-Stock 데일리 파이프라인 시작"
log "============================================"

# 가상환경 활성화
if [ -f "$VENV_DIR/bin/activate" ]; then
    source "$VENV_DIR/bin/activate"
    log "✅ 가상환경 활성화 완료"
else
    log "❌ 가상환경을 찾을 수 없습니다: $VENV_DIR"
    exit 1
fi

cd "$PROJECT_DIR"

# ============================================================
# Step 1: VCP 스캔
# ============================================================
log ""
log "📊 [Step 1/3] VCP 스캔 시작 (quick_scan.py)"
log "  대상: 시가총액 상위 200개 종목"

if python3 quick_scan.py >> "$LOG_FILE" 2>&1; then
    SIGNAL_COUNT=$(wc -l < kr_market/data/signals_log.csv)
    SIGNAL_COUNT=$((SIGNAL_COUNT - 1))  # 헤더 제외
    log "✅ [Step 1/3] 완료 — ${SIGNAL_COUNT}개 시그널 발견"
else
    log "❌ [Step 1/3] VCP 스캔 실패"
    exit 1
fi

# ============================================================
# Step 2: 12점 채점
# ============================================================
log ""
log "📊 [Step 2/3] 12점 채점 시작 (run_v2_scoring.py)"

if python3 run_v2_scoring.py >> "$LOG_FILE" 2>&1; then
    log "✅ [Step 2/3] 완료 — jongga_v2_latest.json 생성"
else
    log "⚠️ [Step 2/3] 12점 채점 실패 (비 치명적, 계속 진행)"
fi

# ============================================================
# Step 3: AI 분석 캐시 갱신
# ============================================================
log ""
log "🤖 [Step 3/3] AI 분석 캐시 갱신 (refresh_ai_cache.py)"
log "  Gemini + GPT 분석, 시장 논평 생성"

if python3 refresh_ai_cache.py --max 15 >> "$LOG_FILE" 2>&1; then
    log "✅ [Step 3/3] 완료 — kr_ai_analysis.json 갱신"
else
    log "⚠️ [Step 3/3] AI 캐시 갱신 실패 (비 치명적)"
fi

# ============================================================
# 완료 요약
# ============================================================
log ""
log "============================================"
log "✅ 데일리 파이프라인 완료!"
log "   시각: $(date '+%Y-%m-%d %H:%M:%S')"
log "   로그: $LOG_FILE"
log "============================================"

# 오래된 로그 정리 (30일 이상)
find "$LOG_DIR" -name "pipeline_*.log" -mtime +30 -delete 2>/dev/null || true
