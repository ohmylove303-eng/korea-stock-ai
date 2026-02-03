"""
종가베팅 시그널 데이터 모델
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import date, datetime
from enum import Enum


class SignalStatus(Enum):
    """시그널 상태"""
    OPEN = "OPEN"
    TARGET_HIT = "TARGET_HIT"
    STOP_HIT = "STOP_HIT"
    TIME_EXIT = "TIME_EXIT"
    GAP_EXIT = "GAP_EXIT"


@dataclass
class StockData:
    """종목 기본 정보"""
    code: str                    # 종목 코드 (6자리)
    name: str                    # 종목명
    market: str                  # 시장 (KOSPI/KOSDAQ)
    sector: str = ""             # 업종
    
    # 가격 정보
    current_price: int = 0
    change_pct: float = 0.0
    trading_value: int = 0        # 거래대금
    
    # 수급 정보
    foreign_5d: int = 0           # 외국인 5일 순매수
    inst_5d: int = 0              # 기관 5일 순매수
    foreign_20d: int = 0          # 외국인 20일 순매수
    inst_20d: int = 0             # 기관 20일 순매수


@dataclass
class NewsItem:
    """뉴스 아이템"""
    title: str
    source: str = ""
    url: str = ""
    published_at: str = ""
    content: str = ""


@dataclass
class ScoreDetail:
    """점수 상세"""
    news: int = 0                 # 뉴스/재료 (max 3)
    volume: int = 0               # 거래대금 (max 3)
    chart: int = 0                # 차트패턴 (max 2)
    candle: int = 0               # 캔들형태 (max 1)
    consolidation: int = 0        # 기간조정 (max 1)
    supply: int = 0               # 수급 (max 2)
    llm_reason: str = ""          # LLM 분석 이유
    
    @property
    def total(self) -> int:
        """총점 계산 (max 12)"""
        return self.news + self.volume + self.chart + self.candle + self.consolidation + self.supply
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "news": self.news,
            "volume": self.volume,
            "chart": self.chart,
            "candle": self.candle,
            "consolidation": self.consolidation,
            "supply": self.supply,
            "llm_reason": self.llm_reason,
            "total": self.total
        }


@dataclass
class ChecklistDetail:
    """체크리스트 상세"""
    has_news: bool = False
    news_sources: List[str] = field(default_factory=list)
    is_new_high: bool = False
    is_breakout: bool = False
    supply_positive: bool = False
    volume_surge: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "has_news": self.has_news,
            "news_sources": self.news_sources,
            "is_new_high": self.is_new_high,
            "is_breakout": self.is_breakout,
            "supply_positive": self.supply_positive,
            "volume_surge": self.volume_surge
        }


@dataclass
class Signal:
    """종가베팅 시그널"""
    stock_code: str
    stock_name: str
    market: str
    sector: str
    grade: str                    # S, A, B, C
    
    # 점수 정보
    score: ScoreDetail
    checklist: ChecklistDetail
    
    # 가격 정보
    current_price: int
    entry_price: int              # 진입가 (종가)
    stop_price: int               # 손절가 (-3%)
    target_price: int             # 익절가 (+5%)
    change_pct: float             # 등락률
    trading_value: int            # 거래대금
    
    # 수급 정보
    foreign_5d: int = 0
    inst_5d: int = 0
    foreign_20d: int = 0
    inst_20d: int = 0
    
    # 뉴스 정보
    news_items: List[NewsItem] = field(default_factory=list)
    
    # 메타 정보
    signal_date: str = ""
    status: SignalStatus = SignalStatus.OPEN
    
    def to_dict(self) -> Dict[str, Any]:
        """JSON 직렬화용 딕셔너리 변환"""
        return {
            "stock_code": self.stock_code,
            "stock_name": self.stock_name,
            "market": self.market,
            "sector": self.sector,
            "grade": self.grade,
            "score": self.score.to_dict(),
            "checklist": self.checklist.to_dict(),
            "current_price": self.current_price,
            "entry_price": self.entry_price,
            "stop_price": self.stop_price,
            "target_price": self.target_price,
            "change_pct": self.change_pct,
            "trading_value": self.trading_value,
            "foreign_5d": self.foreign_5d,
            "inst_5d": self.inst_5d,
            "foreign_20d": self.foreign_20d,
            "inst_20d": self.inst_20d,
            "news_items": [
                {
                    "title": n.title,
                    "source": n.source,
                    "url": n.url,
                    "published_at": n.published_at
                } for n in self.news_items
            ],
            "signal_date": self.signal_date,
            "status": self.status.value
        }


@dataclass
class ScreenerResult:
    """스크리너 결과"""
    date: str
    total_candidates: int
    filtered_count: int
    signals: List[Signal]
    processing_time_ms: float = 0
    updated_at: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "date": self.date,
            "total_candidates": self.total_candidates,
            "filtered_count": self.filtered_count,
            "signals": [s.to_dict() for s in self.signals],
            "processing_time_ms": self.processing_time_ms,
            "updated_at": self.updated_at or datetime.now().isoformat()
        }


@dataclass
class PositionSize:
    """포지션 사이즈"""
    total_size: int               # 총 투자금액
    share_count: int              # 주식 수량
    r_value: float                # R 값 (리스크)
    risk_amount: float            # 리스크 금액
