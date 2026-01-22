# KR Market AI Stock Analysis System - Blueprint Part 5: Data & Signals

> **Version**: 1.0  
> **Last Updated**: 2026-01-03  
> **Files**: `signal_tracker.py` (358 lines), `screener.py` (564 lines)

---

## 1. Module Overview

These modules handle:
- **VCP Pattern Detection**: Volatility Contraction Pattern identification
- **Signal Tracking**: Recording and updating trade signals
- **Performance Reporting**: Win rate, returns, strategy metrics
- **Institutional Flow Analysis**: Foreign and institutional net buying

---

## 2. Signal Tracker - Full Source

### 2.1 Class Initialization

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KR Market - Signal Tracker
실시간 시그널 기록 및 성과 추적 시스템

기능:
1. 오늘의 시그널 탐지 및 기록
2. 과거 시그널 성과 자동 업데이트
3. 전략 성과 통계 리포트
4. 점진적 전략 개선용 데이터 축적
"""
import pandas as pd
import numpy as np
import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class SignalTracker:
    """시그널 추적 및 성과 기록"""
    
    def __init__(self, data_dir: str = None):
        self.data_dir = data_dir or os.path.dirname(os.path.abspath(__file__))
        self.signals_log_path = os.path.join(self.data_dir, 'signals_log.csv')
        self.performance_path = os.path.join(self.data_dir, 'strategy_performance.json')
        
        # 전략 파라미터 (검증된 최적값)
        self.strategy_params = {
            'foreign_min': 50000,        # 최소 외인 순매수
            'consecutive_min': 3,         # 최소 연속 매수일
            'contraction_max': 0.8,       # 최대 축소비
            'near_high_pct': 0.92,        # 고점 대비 %
            'hold_days': 5,               # 기본 보유 기간
            'stop_loss_pct': 7.0,         # 손절 %
        }
        
        # 로컬 가격 데이터 로드
        self.price_df = self._load_price_data()
        
        logger.info("✅ Signal Tracker 초기화 완료")
    
    def _load_price_data(self) -> pd.DataFrame:
        """로컬 가격 데이터 로드"""
        # ⚠️ IMPORTANT: data_dir 그대로 사용 (dirname 제거됨 - 2026-01-03 수정)
        price_path = os.path.join(self.data_dir, 'daily_prices.csv')
        
        if os.path.exists(price_path):
            df = pd.read_csv(price_path, low_memory=False)
            df['ticker'] = df['ticker'].astype(str).str.zfill(6)
            df['date'] = pd.to_datetime(df['date'])
            logger.info(f"   📊 가격 데이터 로드: {len(df):,}개 레코드")
            return df
        else:
            logger.warning("⚠️ 가격 데이터 파일이 없습니다")
            return pd.DataFrame()
```

### 2.2 VCP Detection Method

```python
    def detect_vcp_forming(self, ticker: str) -> Tuple[bool, Dict]:
        """VCP 형성 초기 감지 (로컬 데이터 사용)"""
        try:
            if self.price_df.empty:
                return False, {}
            
            # 해당 종목 가격 데이터
            ticker_prices = self.price_df[self.price_df['ticker'] == ticker].sort_values('date')
            
            if len(ticker_prices) < 20:
                return False, {}
            
            recent = ticker_prices.tail(20)
            
            # 컬럼명 확인
            price_col = 'current_price' if 'current_price' in recent.columns else 'close'
            high_col = 'high' if 'high' in recent.columns else price_col
            low_col = 'low' if 'low' in recent.columns else price_col
            
            # 전반부/후반부 범위
            first_half = recent.head(10)
            second_half = recent.tail(10)
            
            range_first = first_half[high_col].max() - first_half[low_col].min()
            range_second = second_half[high_col].max() - second_half[low_col].min()
            
            if range_first == 0:
                return False, {}
            
            contraction = range_second / range_first
            current_price = recent.iloc[-1][price_col]
            recent_high = recent[price_col].max()
            
            near_high = current_price >= recent_high * self.strategy_params['near_high_pct']
            contracting = contraction <= self.strategy_params['contraction_max']
            
            is_vcp = near_high and contracting
            
            return is_vcp, {
                'contraction_ratio': round(contraction, 3),
                'price_from_high_pct': round((recent_high - current_price) / recent_high * 100, 2),
                'current_price': round(current_price, 0),
                'recent_high': round(recent_high, 0)
            }
            
        except Exception as e:
            logger.warning(f"⚠️ {ticker} VCP 감지 실패: {e}")
            return False, {}
```

### 2.3 Signal Scanning

```python
    def scan_today_signals(self) -> pd.DataFrame:
        """오늘의 시그널 스캔"""
        logger.info("🔍 오늘의 시그널 스캔 시작...")
        
        # ⚠️ IMPORTANT: data_dir 그대로 사용 (dirname 제거됨 - 2026-01-03 수정)
        inst_path = os.path.join(self.data_dir, 'all_institutional_trend_data.csv')
        
        if not os.path.exists(inst_path):
            logger.error("❌ 수급 데이터 파일이 없습니다")
            return pd.DataFrame()
        
        df = pd.read_csv(inst_path, encoding='utf-8-sig')
        df['ticker'] = df['ticker'].astype(str).str.zfill(6)
        
        # 기본 필터: 외인 매수 + 연속 매수
        signals = df[
            (df['foreign_net_buy_5d'] >= self.strategy_params['foreign_min']) &
            (df['supply_demand_index'] >= 60)
        ].copy()
        
        logger.info(f"   기본 필터 통과: {len(signals)}개 종목")
        
        # VCP 필터 적용
        vcp_signals = []
        for _, row in signals.iterrows():
            ticker = row['ticker']
            is_vcp, vcp_info = self.detect_vcp_forming(ticker)
            
            if is_vcp:
                signal = {
                    'signal_date': datetime.now().strftime('%Y-%m-%d'),
                    'ticker': ticker,
                    'foreign_5d': row['foreign_net_buy_5d'],
                    'inst_5d': row['institutional_net_buy_5d'],
                    'score': row['supply_demand_index'],
                    'contraction_ratio': vcp_info.get('contraction_ratio'),
                    'entry_price': vcp_info.get('current_price'),
                    'status': 'OPEN',
                    'exit_price': None,
                    'exit_date': None,
                    'return_pct': None,
                    'hold_days': 0
                }
                vcp_signals.append(signal)
        
        signals_df = pd.DataFrame(vcp_signals)
        
        if not signals_df.empty:
            self._append_to_log(signals_df)
        
        logger.info(f"✅ 오늘 VCP 시그널: {len(signals_df)}개")
        return signals_df
```

### 2.4 Signal Update and Performance

```python
    def update_open_signals(self):
        """열린 시그널 성과 업데이트"""
        if not os.path.exists(self.signals_log_path):
            return
        
        df = pd.read_csv(self.signals_log_path, encoding='utf-8-sig')
        df['ticker'] = df['ticker'].astype(str).str.zfill(6)
        
        open_signals = df[df['status'] == 'OPEN']
        
        price_col = 'current_price' if 'current_price' in self.price_df.columns else 'close'
        
        for idx, row in open_signals.iterrows():
            ticker = row['ticker']
            entry_price = row['entry_price']
            signal_date = pd.to_datetime(row['signal_date'])
            hold_days = (datetime.now() - signal_date).days
            
            ticker_prices = self.price_df[self.price_df['ticker'] == ticker].sort_values('date')
            
            if len(ticker_prices) > 0:
                current_price = ticker_prices.iloc[-1][price_col]
                return_pct = (current_price - entry_price) / entry_price * 100
                
                # 청산 조건 체크
                should_close = False
                
                if return_pct <= -self.strategy_params['stop_loss_pct']:
                    should_close = True
                    close_reason = "STOP_LOSS"
                elif hold_days >= self.strategy_params['hold_days']:
                    should_close = True
                    close_reason = "TIME_EXIT"
                
                if should_close:
                    df.at[idx, 'status'] = 'CLOSED'
                    df.at[idx, 'exit_price'] = round(current_price, 0)
                    df.at[idx, 'exit_date'] = datetime.now().strftime('%Y-%m-%d')
                    df.at[idx, 'return_pct'] = round(return_pct, 2)
                    df.at[idx, 'hold_days'] = hold_days
        
        df.to_csv(self.signals_log_path, index=False, encoding='utf-8-sig')

    def get_performance_report(self) -> Dict:
        """전략 성과 리포트"""
        if not os.path.exists(self.signals_log_path):
            return {"error": "시그널 로그가 없습니다"}
        
        df = pd.read_csv(self.signals_log_path, encoding='utf-8-sig')
        
        closed = df[df['status'] == 'CLOSED']
        open_signals = df[df['status'] == 'OPEN']
        
        if len(closed) == 0:
            return {
                "message": "아직 청산된 시그널이 없습니다",
                "open_signals": len(open_signals)
            }
        
        wins = len(closed[closed['return_pct'] > 0])
        losses = len(closed[closed['return_pct'] <= 0])
        
        return {
            "period": f"{closed['signal_date'].min()} ~ {closed['exit_date'].max()}",
            "total_signals": len(df),
            "closed_signals": len(closed),
            "open_signals": len(open_signals),
            "wins": wins,
            "losses": losses,
            "win_rate": round(wins / len(closed) * 100, 1),
            "avg_return": round(closed['return_pct'].mean(), 2),
            "total_return": round(closed['return_pct'].sum(), 2),
            "best_trade": round(closed['return_pct'].max(), 2),
            "worst_trade": round(closed['return_pct'].min(), 2),
            "avg_hold_days": round(closed['hold_days'].mean(), 1),
            "strategy_params": self.strategy_params
        }
```

---

## 3. Screener - Key Components

### 3.1 VCP Pattern Detection (from Crypto)

```python
class SmartMoneyScreener:
    """Smart Money Screener - 외인/기관 매집 종목 탐지"""
    
    def detect_vcp_pattern(self, prices_df: pd.DataFrame, 
                          lookback: int = 20,
                          contraction_threshold: float = 0.7) -> Tuple[bool, Dict]:
        """
        VCP (Volatility Contraction Pattern) 감지
        
        코인 VCP 백테스트에서 이식한 로직:
        - ATR(변동성)이 점점 줄어드는 패턴
        - 고가-저가 범위 축소
        - 현재가가 최근 고점 근처
        """
        if len(prices_df) < lookback:
            return False, {}
        
        recent = prices_df.tail(lookback).copy()
        
        # 컬럼명 통일
        price_col = 'current_price' if 'current_price' in recent.columns else 'close'
        high_col = 'high' if 'high' in recent.columns else price_col
        low_col = 'low' if 'low' in recent.columns else price_col
        
        # 1. 전반부/후반부 가격 범위 비교
        first_half = recent.head(lookback // 2)
        second_half = recent.tail(lookback // 2)
        
        range_first = first_half[high_col].max() - first_half[low_col].min()
        range_second = second_half[high_col].max() - second_half[low_col].min()
        
        if range_first == 0:
            return False, {}
        
        contraction_ratio = range_second / range_first
        
        # 2. 현재가 고점 근처 확인
        current_price = recent.iloc[-1][price_col]
        recent_high = recent[price_col].max()
        price_near_high = current_price >= recent_high * 0.95
        
        # 3. 트렌드 상승 확인
        price_start = recent.iloc[0][price_col]
        is_uptrend = current_price > price_start * 0.98
        
        is_vcp = (contraction_ratio <= contraction_threshold and 
                  price_near_high and 
                  is_uptrend)
        
        return is_vcp, {
            'contraction_ratio': round(contraction_ratio, 3),
            'price_from_high_pct': round((recent_high - current_price) / recent_high * 100, 2),
            'price_near_high': price_near_high,
            'is_uptrend': is_uptrend
        }
```

### 3.2 VCP Score Calculation

```python
    def calculate_vcp_score(self, vcp_info: Dict) -> float:
        """VCP 신호 강도 점수 (0-20점)"""
        if not vcp_info:
            return 0.0
        
        score = 0.0
        
        # 축소 비율이 낮을수록 고점수
        contraction = vcp_info.get('contraction_ratio', 1.0)
        if contraction <= 0.3:
            score += 10.0
        elif contraction <= 0.5:
            score += 7.0
        elif contraction <= 0.7:
            score += 4.0
        
        # 고점 근처 보너스
        if vcp_info.get('price_near_high', False):
            score += 5.0
        
        # 상승 추세 보너스
        if vcp_info.get('is_uptrend', False):
            score += 5.0
        
        return score
```

### 3.3 Naver Finance Scraping

```python
    def scrape_institutional_data(self, ticker: str) -> Optional[TrendAnalysis]:
        """네이버 금융에서 외인/기관 순매매 데이터 스크래핑"""
        try:
            url = f"https://finance.naver.com/item/frgn.naver?code={ticker}"
            response = self.session.get(url, timeout=10)
            response.encoding = 'euc-kr'
            
            if response.status_code != 200:
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 일별 데이터 추출
            daily_data = self._extract_daily_data(soup)
            
            if len(daily_data) < 5:
                return None
            
            # 트렌드 분석
            return self._analyze_trend(ticker, daily_data)
            
        except Exception as e:
            logger.warning(f"⚠️ {ticker} 스크래핑 실패: {e}")
            return None
```

---

## 4. Strategy Parameters

### 4.1 Default Configuration

```python
# From config.py
strategy_params = {
    'foreign_min': 50000,        # Minimum foreign net buy (shares)
    'consecutive_min': 3,         # Minimum consecutive buy days
    'contraction_max': 0.8,       # Maximum contraction ratio (VCP)
    'near_high_pct': 0.92,        # Price must be within 8% of high
    'hold_days': 5,               # Default holding period
    'stop_loss_pct': 7.0,         # Stop loss percentage
}
```

### 4.2 Scoring Weights

```python
# SmartMoneyScreener scoring
weight_foreign: float = 0.40     # Foreign flow (40%)
weight_inst: float = 0.30        # Institutional flow (30%)
weight_technical: float = 0.20   # Technical analysis (20%)
weight_fundamental: float = 0.10 # Fundamentals (10%)
```

---

## 5. Data Files

### 5.1 signals_log.csv Structure

| Column | Type | Description |
|:---|:---|:---|
| signal_date | date | Signal detection date |
| ticker | string | 6-digit stock code |
| foreign_5d | int | 5-day foreign net buy |
| inst_5d | int | 5-day institutional net buy |
| score | float | Supply/demand index score |
| contraction_ratio | float | VCP contraction ratio |
| entry_price | float | Recommended entry price |
| status | enum | OPEN / CLOSED |
| exit_price | float | Exit price (if closed) |
| exit_date | date | Exit date (if closed) |
| return_pct | float | Return percentage |
| hold_days | int | Days held |

---

## Next Steps

Continue to **[BLUEPRINT_06_FRONTEND_HTML.md](./BLUEPRINT_06_FRONTEND_HTML.md)** for frontend HTML structure.
