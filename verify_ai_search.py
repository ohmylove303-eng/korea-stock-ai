import sys
import os
import json
from datetime import datetime

# 프로젝트 루트 경로 추가
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

try:
    print(f"[{datetime.now()}] 🚀 AI 분석 모듈 직접 검증 시작...")
    
    # 1. 모듈 임포트 테스트
    from kr_market.kr_ai_analyzer import analyze_single_stock_realtime
    from kr_market.kr_ai_analyzer import GOOGLE_API_KEY
    
    if not GOOGLE_API_KEY:
        print("❌ GOOGLE_API_KEY가 설정되지 않았습니다.")
        sys.exit(1)
        
    print(f"✅ API Key 확인됨: {GOOGLE_API_KEY[:5]}...")
    
    # 2. 분석 실행 (종목: 삼성전자 005930)
    ticker = "005930"
    print(f"[{datetime.now()}] 🔍 '{ticker}' 종목에 대한 AI 분석 요청 중 (Google Search 포함)...")
    print("⏳ 약 20~40초 소요될 수 있습니다. 잠시만 기다려주세요...")
    
    # AI 분석 함수 직접 호출
    result = analyze_single_stock_realtime(ticker)
    
    # 3. 결과 검증
    print(f"[{datetime.now()}] ✅ 분석 완료!")
    
    # AI 추천 결과
    recommendation = result.get('gpt_recommendation', {}) # fallback 로직에 따라 키가 다를 수 있음
    if not recommendation:
        recommendation = result.get('gemini_recommendation', {})
        
    print("\n" + "="*50)
    print("📢 [AI 추천 결과]")
    print(f"Action: {recommendation.get('action')}")
    print(f"Reason: {recommendation.get('reason')}")
    print("="*50)
    
    # 뉴스 데이터 (Focus)
    news_list = result.get('news', [])
    print(f"\n📚 [수집된 근거 자료: {len(news_list)}건]")
    
    if news_list:
        for idx, news in enumerate(news_list, 1):
            print(f"{idx}. [{news.get('date', '날짜없음')}] {news.get('title')}")
            print(f"   🔗 {news.get('url')}")
    else:
        print("❌ 수집된 뉴스가 없습니다. (Google Search 실패 가능성)")
        
    print("="*50)
    
    # NICE 점수 확인
    nice = result.get('nice_layers', {})
    print("\n📊 [NICE 점수 확인]")
    print(f"Total: {nice.get('total')}/100")
    print(f"L3 감정(AI): {nice.get('L3_sentiment')}")
    print(f"AI Verified: {nice.get('ai_verified')}")

except ImportError as e:
    print(f"❌ Import Error: {e}")
    print("가상환경(venv)이 활성화되었는지 확인하세요.")
except Exception as e:
    print(f"❌ Execution Error: {e}")
    import traceback
    traceback.print_exc()
