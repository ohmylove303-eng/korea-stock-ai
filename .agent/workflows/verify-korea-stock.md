---
description: 한국주식 프로젝트 전체 자동 검증 (Alias)
---

# 한국주식 프로젝트 검증

// turbo-all

이 명령어는 `/ralph-kr`의 **별칭(alias)**입니다.

백엔드 + 프론트엔드를 자동으로 검증하고 최종 통합 테스트를 수행합니다.

## 실행 방법
채팅창에 입력:
```
/verify-korea-stock
```

## 수행 작업
1. ✅ Python 의존성 설치 (pykrx, Flask, Gemini, GPT)
2. ✅ 백엔드 파일 문법 검증 (flask_app.py, kr_market)
3. ✅ 모듈 Import 테스트
4. ✅ HTML 파일 문법 검증 (dashboard.html)
5. ✅ API 호출 존재 확인
6. ✅ Flask 서버 구동 테스트
7. ✅ .env 설정 확인

## 자동 수정
- 누락된 패키지 자동 설치
- 문법 오류 자동 수정
- 파일 누락 시 재생성
