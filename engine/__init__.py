"""
Engine Package - 종가베팅 시그널 생성 엔진

사용법:
    from engine.generator import run_screener
    result = await run_screener(capital=50_000_000)
"""

from .config import SignalConfig, Grade, GradeConfig
from .models import (
    StockData, Signal, SignalStatus, 
    ScoreDetail, ChecklistDetail, ScreenerResult, 
    NewsItem, PositionSize
)
from .collectors import DataCollector, NewsCollector
from .scorer import Scorer
from .llm_analyzer import LLMAnalyzer
from .position_sizer import PositionSizer
from .generator import SignalGenerator, run_screener

__all__ = [
    # Config
    'SignalConfig', 'Grade', 'GradeConfig',
    # Models
    'StockData', 'Signal', 'SignalStatus', 
    'ScoreDetail', 'ChecklistDetail', 'ScreenerResult',
    'NewsItem', 'PositionSize',
    # Components
    'DataCollector', 'NewsCollector',
    'Scorer', 'LLMAnalyzer', 'PositionSizer',
    # Main
    'SignalGenerator', 'run_screener'
]
