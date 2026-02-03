"""
LLM 분석기 - Gemini API를 사용한 뉴스 감성 분석
"""

import os
import json
import asyncio
from typing import Dict, List, Optional, Any

import google.generativeai as genai


class LLMAnalyzer:
    """Gemini 기반 뉴스 감성 분석기"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')
        self.model = None
        
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
    
    async def analyze_news_sentiment(
        self,
        stock_name: str,
        news_items: List[Dict]
    ) -> Dict[str, Any]:
        """
        뉴스 종합 분석 → 호재 점수 (0~3)
        
        Args:
            stock_name: 종목명
            news_items: 뉴스 리스트 [{"title": ..., "source": ...}, ...]
        
        Returns:
            {"score": 0~3, "reason": "분석 이유"}
        """
        if not self.model:
            # API 키 없으면 키워드 기반 폴백
            return self._keyword_fallback_analysis(news_items)
        
        if not news_items:
            return {"score": 0, "reason": "뉴스 없음"}
        
        # 프롬프트 구성
        news_text = "\n".join([
            f"- [{n.get('source', '언론사')}] {n.get('title', '')}"
            for n in news_items[:5]
        ])
        
        prompt = f"""당신은 주식 투자 전문가입니다. 다음은 '{stock_name}' 종목에 대한 최신 뉴스들입니다.
이 뉴스들을 종합적으로 분석하여 현재 시점에서의 호재 강도를 0~3점으로 평가하세요.

### 뉴스 목록:
{news_text}

### 평가 기준:
- 0점: 호재 없음, 악재 또는 중립
- 1점: 약한 호재 (일반적인 긍정 뉴스)
- 2점: 중간 호재 (계약, 실적 개선 등)
- 3점: 강한 호재 (대규모 수주, FDA 승인, 기술 이전 등)

### 응답 형식 (JSON만 출력):
{{"score": 2, "reason": "종합적인 요약 이유 (1~2문장)"}}
"""
        
        try:
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            
            result = json.loads(response.text)
            
            # 검증
            if 'score' not in result:
                result['score'] = 0
            result['score'] = min(max(int(result.get('score', 0)), 0), 3)
            
            if 'reason' not in result:
                result['reason'] = "분석 완료"
            
            return result
            
        except json.JSONDecodeError:
            # JSON 파싱 실패 시 텍스트에서 추출 시도
            try:
                text = response.text
                score_match = text.find('"score"')
                if score_match != -1:
                    score_str = text[score_match:score_match+20]
                    for char in score_str:
                        if char.isdigit():
                            return {"score": int(char), "reason": "분석 완료"}
            except:
                pass
            return {"score": 0, "reason": "분석 실패"}
            
        except Exception as e:
            print(f"[WARN] LLM analysis error: {e}")
            return self._keyword_fallback_analysis(news_items)
    
    def _keyword_fallback_analysis(self, news_items: List[Dict]) -> Dict[str, Any]:
        """키워드 기반 폴백 분석"""
        if not news_items:
            return {"score": 0, "reason": "뉴스 없음"}
        
        # 긍정 키워드
        positive_keywords = [
            "흑자전환", "실적개선", "사상최대", "호실적", "수주", "계약체결",
            "공급계약", "MOU", "신약", "임상", "FDA", "승인", "특허",
            "기술이전", "상용화", "외국인매수", "기관매수", "상한가"
        ]
        
        # 부정 키워드
        negative_keywords = [
            "적자", "하락", "악재", "조사", "수사", "횡령", "배임",
            "상장폐지", "관리종목", "감사의견거절"
        ]
        
        text = " ".join([n.get('title', '') for n in news_items])
        
        positive_count = sum(1 for kw in positive_keywords if kw in text)
        negative_count = sum(1 for kw in negative_keywords if kw in text)
        
        if negative_count >= 2:
            return {"score": 0, "reason": "부정적 키워드 다수 발견"}
        
        if positive_count >= 3:
            return {"score": 3, "reason": f"강한 호재 키워드 {positive_count}개"}
        elif positive_count >= 2:
            return {"score": 2, "reason": f"호재 키워드 {positive_count}개"}
        elif positive_count >= 1:
            return {"score": 1, "reason": f"약한 호재 키워드"}
        
        return {"score": 0, "reason": "특별한 호재 없음"}
    
    async def get_trading_recommendation(
        self,
        stock_name: str,
        stock_code: str,
        score: int,
        change_pct: float,
        foreign_5d: int,
        inst_5d: int,
        news_items: List[Dict]
    ) -> Dict[str, Any]:
        """
        종합 매매 추천
        
        Returns:
            {"action": "BUY/HOLD/SELL", "confidence": 0~100, "reason": "..."}
        """
        if not self.model:
            # 폴백: 점수 기반 단순 추천
            if score >= 8:
                return {"action": "BUY", "confidence": 80, "reason": "높은 점수"}
            elif score >= 6:
                return {"action": "HOLD", "confidence": 60, "reason": "관망"}
            return {"action": "HOLD", "confidence": 50, "reason": "기준 미달"}
        
        news_text = "\n".join([
            f"- {n.get('title', '')}" for n in news_items[:3]
        ]) if news_items else "(뉴스 없음)"
        
        prompt = f"""당신은 한국 주식 투자 전문가입니다.

### 종목 정보
- 종목명: {stock_name} ({stock_code})
- 오늘 등락률: {change_pct:+.1f}%
- 종합 점수: {score}/12
- 외국인 5일 순매수: {foreign_5d:,}주
- 기관 5일 순매수: {inst_5d:,}주

### 최신 뉴스
{news_text}

### 분석 요청
위 정보를 바탕으로 단기(1~3일) 매매 추천을 해주세요.

### 응답 형식 (JSON만 출력):
{{"action": "BUY", "confidence": 85, "reason": "투자 이유 1~2문장"}}

action은 BUY, HOLD, SELL 중 하나입니다.
confidence는 0~100 사이 정수입니다.
"""
        
        try:
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            
            result = json.loads(response.text)
            
            # 검증
            if result.get('action') not in ['BUY', 'HOLD', 'SELL']:
                result['action'] = 'HOLD'
            result['confidence'] = min(max(int(result.get('confidence', 50)), 0), 100)
            
            return result
            
        except Exception as e:
            print(f"[WARN] Trading recommendation error: {e}")
            return {"action": "HOLD", "confidence": 50, "reason": "분석 오류"}
