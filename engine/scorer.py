"""
종가베팅 점수 시스템 (12점 만점)

점수 항목:
- 뉴스/재료: 3점
- 거래대금: 3점
- 차트패턴: 2점
- 캔들형태: 1점
- 기간조정: 1점
- 수급: 2점
"""

from typing import Dict, List, Optional, Any
import pandas as pd
import numpy as np

from .config import SignalConfig, Grade
from .models import ScoreDetail, ChecklistDetail, NewsItem


class Scorer:
    """종가베팅 점수 계산기"""
    
    def __init__(self, config: SignalConfig = None):
        self.config = config or SignalConfig.default()
    
    def calculate(
        self,
        trading_value: int,
        change_pct: float,
        chart_data: pd.DataFrame,
        news_items: List[NewsItem],
        news_score: int,
        news_reason: str,
        supply_data: Dict[str, int]
    ) -> tuple[ScoreDetail, ChecklistDetail]:
        """
        종목 점수 계산
        
        Returns:
            (ScoreDetail, ChecklistDetail) 튜플
        """
        score = ScoreDetail()
        checklist = ChecklistDetail()
        
        # 1. 뉴스 점수 (0 ~ 3점)
        score.news = min(news_score, 3)
        score.llm_reason = news_reason
        
        if news_items:
            checklist.has_news = True
            checklist.news_sources = list(set(n.source for n in news_items if n.source))
        
        # 2. 거래대금 점수 (0 ~ 3점)
        score.volume = self._calculate_volume_score(trading_value)
        
        if trading_value >= 500_000_000_000:  # 5천억+
            checklist.volume_surge = True
        
        # 3. 차트 패턴 점수 (0 ~ 2점)
        if not chart_data.empty:
            score.chart = self._calculate_chart_score(chart_data)
            
            # 신고가 체크
            if len(chart_data) >= 20:
                high_20 = chart_data['high'].tail(20).max()
                current = chart_data['close'].iloc[-1]
                if current >= high_20 * 0.98:  # 2% 이내
                    checklist.is_new_high = True
            
            # 돌파 체크
            if len(chart_data) >= 5:
                avg_vol = chart_data['volume'].tail(20).mean()
                today_vol = chart_data['volume'].iloc[-1]
                if today_vol >= avg_vol * 2:
                    checklist.is_breakout = True
        
        # 4. 캔들 형태 점수 (0 ~ 1점)
        if not chart_data.empty:
            score.candle = self._calculate_candle_score(chart_data)
        
        # 5. 기간 조정 점수 (0 ~ 1점)
        if not chart_data.empty:
            score.consolidation = self._calculate_consolidation_score(chart_data)
        
        # 6. 수급 점수 (0 ~ 2점)
        score.supply = self._calculate_supply_score(supply_data)
        
        if supply_data.get('foreign_5d', 0) > 0 and supply_data.get('inst_5d', 0) > 0:
            checklist.supply_positive = True
        
        return score, checklist
    
    def _calculate_volume_score(self, trading_value: int) -> int:
        """거래대금 점수"""
        if trading_value >= 1_000_000_000_000:  # 1조+
            return 3
        elif trading_value >= 500_000_000_000:  # 5천억+
            return 2
        elif trading_value >= 100_000_000_000:  # 1천억+
            return 1
        return 0
    
    def _calculate_chart_score(self, df: pd.DataFrame) -> int:
        """차트 패턴 점수"""
        score = 0
        
        if len(df) < 20:
            return 0
        
        # EMA 계산
        df = df.copy()
        df['ema5'] = df['close'].ewm(span=5).mean()
        df['ema20'] = df['close'].ewm(span=20).mean()
        df['ema60'] = df['close'].ewm(span=60).mean() if len(df) >= 60 else df['ema20']
        
        current = df.iloc[-1]
        
        # 정배열 체크 (EMA5 > EMA20 > EMA60)
        if current['ema5'] > current['ema20'] > current['ema60']:
            score += 1
        
        # 신고가 돌파 체크
        high_20 = df['high'].tail(20).max()
        if current['close'] >= high_20 * 0.98:
            score += 1
        
        return min(score, 2)
    
    def _calculate_candle_score(self, df: pd.DataFrame) -> int:
        """캔들 형태 점수"""
        if df.empty:
            return 0
        
        today = df.iloc[-1]
        
        open_price = today['open']
        close = today['close']
        high = today['high']
        low = today['low']
        
        body = abs(close - open_price)
        upper_wick = high - max(open_price, close)
        lower_wick = min(open_price, close) - low
        
        # 장대양봉 + 윗꼬리 짧음
        if close > open_price:  # 양봉
            if body > 0:
                upper_ratio = upper_wick / body
                if upper_ratio < 0.3:  # 윗꼬리 30% 미만
                    return 1
        
        return 0
    
    def _calculate_consolidation_score(self, df: pd.DataFrame) -> int:
        """기간 조정 점수"""
        if len(df) < 20:
            return 0
        
        # 볼린저 밴드 수축 체크
        df = df.copy()
        df['sma20'] = df['close'].rolling(20).mean()
        df['std20'] = df['close'].rolling(20).std()
        df['bb_width'] = df['std20'] / df['sma20']
        
        if len(df) >= 20:
            recent_width = df['bb_width'].iloc[-5:].mean()
            prev_width = df['bb_width'].iloc[-20:-5].mean()
            
            if prev_width > 0 and recent_width < prev_width * 0.7:  # 30% 수축
                return 1
        
        return 0
    
    def _calculate_supply_score(self, supply_data: Dict[str, int]) -> int:
        """수급 점수"""
        score = 0
        
        foreign_5d = supply_data.get('foreign_5d', 0)
        inst_5d = supply_data.get('inst_5d', 0)
        
        # 외국인 순매수
        if foreign_5d > 0:
            score += 1
        
        # 기관 순매수
        if inst_5d > 0:
            score += 1
        
        return min(score, 2)
    
    def determine_grade(
        self,
        score: ScoreDetail,
        trading_value: int,
        change_pct: float
    ) -> str:
        """
        등급 결정
        
        - S급: 10점+ & 거래대금 1조+
        - A급: 8점+ & 거래대금 5천억+
        - B급: 6점+ & 거래대금 1천억+
        - C급: 그 외
        """
        total = score.total
        
        # S급 기준
        if total >= 10 and trading_value >= 1_000_000_000_000:
            return "S"
        
        # A급 기준
        if total >= 8 and trading_value >= 500_000_000_000:
            return "A"
        
        # B급 기준
        if total >= 6 and trading_value >= 100_000_000_000:
            return "B"
        
        # C급 (미달)
        return "C"
