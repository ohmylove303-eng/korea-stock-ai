#!/bin/bash

# 프로젝트 디렉토리로 이동 (스크립트가 있는 위치 기준)
cd "$(dirname "$0")"

# 가상환경 활성화 (필수 라이브러리 로드)
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "Error: 'venv' directory not found. Please setup python virtual environment first."
    exit 1
fi

# Python 경로 강제 지정하여 스크립트 실행
# 사용자가 실행하려던 scripts/score_outcomes.py 실행
# 필요한 인자값 등을 자동으로 넘김

echo "Running score_outcomes.py with VENV..."
./venv/bin/python scripts/score_outcomes.py --db db.sqlite3 --run_id "KR|EOD|2024-01-08|live150+bt300|h=5,10|rule=v1.1" --calendar_end "2026-12-31"

# 실행 후 화면이 바로 꺼지지 않게 대기 (선택 사항)
echo "Done."
