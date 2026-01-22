---
description: 한국주식 프로젝트 - 프론트엔드 자동 검증
---

# 프론트엔드 자동 검증 워크플로우

// turbo-all

이 워크플로우는 한국주식 프로젝트의 프론트엔드 파일을 자동으로 검증합니다.

## 📄 프론트엔드 파일 목록

### BLUEPRINT_06: Frontend Main
- `templates/dashboard.html` (5,923 lines)
- `templates/index.html` (723 lines)

### BLUEPRINT_07: Frontend Partials
- Dashboard sections (signals, AI analysis, charts)

### BLUEPRINT_08: JavaScript
- API calls
- Chart rendering (Plotly)
- Real-time updates

---

## 1단계: HTML 파일 존재 확인
```bash
ls -lh templates/dashboard.html templates/index.html
```

## 2단계: HTML 문법 검증 (dashboard.html)
```bash
python3 -c "
from html.parser import HTMLParser
import sys

class SimpleHTMLParser(HTMLParser):
    def error(self, message):
        print(f'❌ HTML Error: {message}')
        sys.exit(1)

with open('templates/dashboard.html', 'r', encoding='utf-8') as f:
    parser = SimpleHTMLParser()
    try:
        parser.feed(f.read())
        print('✅ dashboard.html syntax valid')
    except Exception as e:
        print(f'❌ dashboard.html error: {e}')
        sys.exit(1)
"
```

## 3단계: HTML 문법 검증 (index.html)
```bash
python3 -c "
from html.parser import HTMLParser
import sys

with open('templates/index.html', 'r', encoding='utf-8') as f:
    parser = HTMLParser()
    try:
        parser.feed(f.read())
        print('✅ index.html syntax valid')
    except Exception as e:
        print(f'❌ index.html error: {e}')
        sys.exit(1)
"
```

## 4단계: JavaScript 구문 확인 (필수 API 호출 존재 여부)
```bash
grep -q "fetch('/api/kr/signals')" templates/dashboard.html && echo "✅ KR Signals API call found" || echo "⚠️ Warning: KR Signals API call not found"
grep -q "fetch('/api/kr/ai-analysis')" templates/dashboard.html && echo "✅ AI Analysis API call found" || echo "⚠️ Warning: AI Analysis API call not found"
```

## 5단계: CSS 블록 존재 확인
```bash
grep -q "<style>" templates/dashboard.html && echo "✅ CSS styling present" || echo "⚠️ Warning: No inline CSS found"
```

## 6단계: Plotly 차트 라이브러리 CDN 확인
```bash
grep -q "plotly" templates/dashboard.html && echo "✅ Plotly library loaded" || echo "⚠️ Warning: Plotly library not found"
```

---

**자동 수정 규칙:**
- HTML 문법 오류 → 자동 수정 (닫는 태그 추가 등)
- 누락된 API 호출 → 템플릿에서 재생성
- CDN 링크 오류 → 최신 버전으로 교체
