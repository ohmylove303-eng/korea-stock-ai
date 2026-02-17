#!/bin/bash
# K-Stock 자동화 설정 스크립트
# macOS launchd를 이용한 일일 스캔 및 AI 분석 자동화

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"

echo "=================================================="
echo "🚀 K-Stock 자동화 설정"
echo "=================================================="

# logs 디렉토리 생성
mkdir -p "$SCRIPT_DIR/logs"
echo "✅ logs 디렉토리 준비 완료"

# plist 파일 복사
echo ""
echo "📋 launchd plist 설치 중..."

# 기존 작업 중지 (에러 무시)
launchctl unload "$LAUNCH_AGENTS_DIR/com.kstock.daily-scan.plist" 2>/dev/null || true
launchctl unload "$LAUNCH_AGENTS_DIR/com.kstock.ai-refresh.plist" 2>/dev/null || true

# plist 복사
cp "$SCRIPT_DIR/com.kstock.daily-scan.plist" "$LAUNCH_AGENTS_DIR/"
cp "$SCRIPT_DIR/com.kstock.ai-refresh.plist" "$LAUNCH_AGENTS_DIR/"

# plist 로드
launchctl load "$LAUNCH_AGENTS_DIR/com.kstock.daily-scan.plist"
launchctl load "$LAUNCH_AGENTS_DIR/com.kstock.ai-refresh.plist"

echo "✅ launchd 작업 등록 완료"

echo ""
echo "📅 등록된 스케줄:"
echo "   • 15:40 - VCP 시그널 스캔 (quick_scan.py)"
echo "   • 16:00 - AI 분석 캐시 갱신 (refresh_ai_cache.py)"

echo ""
echo "🔧 수동 실행 방법:"
echo "   스캔:     python quick_scan.py"
echo "   AI 갱신:  python refresh_ai_cache.py --max 15"

echo ""
echo "📊 로그 확인:"
echo "   tail -f logs/daily_scan.log"
echo "   tail -f logs/ai_refresh.log"

echo ""
echo "🛑 자동화 중지 방법:"
echo "   launchctl unload ~/Library/LaunchAgents/com.kstock.daily-scan.plist"
echo "   launchctl unload ~/Library/LaunchAgents/com.kstock.ai-refresh.plist"

echo ""
echo "✅ 설정 완료!"
