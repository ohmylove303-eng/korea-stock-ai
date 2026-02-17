#!/bin/bash

# 프로젝트 디렉토리로 이동
cd "$(dirname "$0")"

# 1. Backend (Flask) 실행
echo "🚀 Starting Backend (Flask)..."
if [ -d "venv" ]; then
    # venv 파이썬 직접 호출 (activate 필요 없음)
    nohup ./venv/bin/python flask_app.py > flask_run.log 2>&1 &
    BACKEND_PID=$!
    echo "   Backend PID: $BACKEND_PID"
else
    echo "❌ Error: 'venv' not found. Please setup python environment."
    exit 1
fi

echo "   Waiting for Backend port 5001..."
# 포트 5001이 열릴 때까지 최대 15초 대기
count=0
while ! lsof -i :5001 >/dev/null; do
    sleep 1
    count=$((count+1))
    if [ $count -ge 15 ]; then
        echo "❌ Timeout waiting for Backend (Port 5001)."
        echo "   Check flask_run.log for errors."
        exit 1
    fi
done
echo "✅ Backend is RUNNING on port 5001."

# 2. Frontend (Next.js) 실행
echo "🚀 Starting Frontend (Next.js)..."
cd frontend

# node_modules 확인 (없으면 설치)
if [ ! -d "node_modules" ]; then
    echo "   Installing dependencies (first run, may take time)..."
    npm install
fi

# Next.js Dev Server 실행 (백그라운드)
# 포트 충돌 방지 및 명시적 선언
PORT=3000 nohup npm run dev > ../next_run.log 2>&1 &
FRONTEND_PID=$!
echo "   Frontend PID: $FRONTEND_PID"

echo "   Waiting for Frontend port 3000..."
# 포트 3000이 열릴 때까지 최대 30초 대기 (Next.js 컴파일 시간 고려)
count=0
while ! lsof -i :3000 >/dev/null; do
    sleep 1
    count=$((count+1))
    if [ $count -ge 30 ]; then
        echo "⚠️ Timeout waiting for Frontend port 3000 (It might still be compiling)."
        echo "   Check next_run.log for details."
        break 
    fi
done

# 3. 브라우저 열기
echo "🌐 Opening Dashboard..."
open "http://localhost:3000" 

echo "✅ All Systems Go!"
echo "   Backend Logs: flask_run.log"
echo "   Frontend Logs: next_run.log"
echo "   To stop servers: kill $BACKEND_PID $FRONTEND_PID"
