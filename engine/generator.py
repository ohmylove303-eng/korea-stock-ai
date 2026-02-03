"""
종가베팅 시그널 생성기 (V2)

사용법:
    from engine.generator import run_screener
    result = await run_screener(capital=50_000_000)
"""

import asyncio
import json
import os
import time
from datetime import date, datetime
from typing import List, Optional, Dict, Any

from .config import SignalConfig, Grade
from .models import Signal, StockData, ScoreDetail, ChecklistDetail, ScreenerResult, NewsItem
from .collectors import DataCollector, NewsCollector
from .scorer import Scorer
from .llm_analyzer import LLMAnalyzer
from .position_sizer import PositionSizer


class SignalGenerator:
    """종가베팅 시그널 생성기"""
    
    def __init__(
        self,
        capital: float = 50_000_000,
        config: SignalConfig = None
    ):
        self.capital = capital
        self.config = config or SignalConfig.default()
        
        self._collector = DataCollector(self.config)
        self._news_collector: Optional[NewsCollector] = None
        self._scorer = Scorer(self.config)
        self._llm = LLMAnalyzer()
        self._sizer = PositionSizer(self.config)
        
        self._request_count = 0
        self._last_request_time = 0
    
    async def __aenter__(self):
        self._news_collector = NewsCollector()
        await self._news_collector.__aenter__()
        return self
    
    async def __aexit__(self, *args):
        if self._news_collector:
            await self._news_collector.__aexit__(*args)
    
    async def generate(
        self,
        target_date: date = None,
        markets: List[str] = None,
        top_n: int = 30,
    ) -> List[Signal]:
        """
        시그널 생성
        
        Args:
            target_date: 분석 날짜 (기본: 오늘)
            markets: 분석 시장 (기본: KOSPI, KOSDAQ)
            top_n: 시장당 분석 종목 수
        
        Returns:
            등급순 정렬된 시그널 리스트
        """
        if target_date is None:
            target_date = date.today()
        
        if markets is None:
            markets = ["KOSPI", "KOSDAQ"]
        
        all_signals = []
        
        for market in markets:
            print(f"\n[INFO] Scanning {market}...")
            
            # 1. 상승 상위 종목 조회
            candidates = await self._collector.get_top_gainers(market, top_n, target_date)
            print(f"[INFO] Found {len(candidates)} candidates in {market}")
            
            # 2. 각 종목 분석
            for i, stock in enumerate(candidates):
                try:
                    signal = await self._analyze_stock(stock, target_date)
                    
                    if signal and signal.grade != "C":
                        all_signals.append(signal)
                        print(f"  [{signal.grade}] {signal.stock_name} - Score: {signal.score.total}")
                    
                    # Rate limiting (LLM API)
                    await self._rate_limit()
                    
                except Exception as e:
                    print(f"[WARN] Failed to analyze {stock.name}: {e}")
                    continue
        
        # 3. 등급 및 점수순 정렬
        grade_order = {"S": 0, "A": 1, "B": 2, "C": 3}
        all_signals.sort(key=lambda s: (grade_order.get(s.grade, 3), -s.score.total))
        
        # 4. 상위 N개만
        max_signals = self.config.max_positions * 2
        return all_signals[:max_signals]
    
    async def _analyze_stock(
        self,
        stock: StockData,
        target_date: date
    ) -> Optional[Signal]:
        """개별 종목 분석"""
        
        # 1. 차트 데이터 조회
        chart_data = await self._collector.get_chart_data(stock.code, days=60)
        
        # 2. 수급 데이터 조회
        supply_data = await self._collector.get_supply_data(stock.code, days=20)
        stock.foreign_5d = supply_data['foreign_5d']
        stock.inst_5d = supply_data['inst_5d']
        stock.foreign_20d = supply_data['foreign_20d']
        stock.inst_20d = supply_data['inst_20d']
        
        # 3. 뉴스 조회
        news_items = []
        if self._news_collector:
            raw_news = await self._news_collector.collect_news(stock.name, stock.code)
            news_items = [
                NewsItem(
                    title=n.title,
                    source=n.source,
                    url=n.url,
                    published_at=n.published_at
                ) for n in raw_news
            ]
        
        # 4. LLM 뉴스 분석
        news_dicts = [{"title": n.title, "source": n.source} for n in news_items]
        llm_result = await self._llm.analyze_news_sentiment(stock.name, news_dicts)
        news_score = llm_result.get('score', 0)
        news_reason = llm_result.get('reason', '')
        
        # 5. 점수 계산
        score_detail, checklist = self._scorer.calculate(
            trading_value=stock.trading_value,
            change_pct=stock.change_pct,
            chart_data=chart_data,
            news_items=news_items,
            news_score=news_score,
            news_reason=news_reason,
            supply_data=supply_data
        )
        
        # 6. 등급 결정
        grade = self._scorer.determine_grade(
            score_detail,
            stock.trading_value,
            stock.change_pct
        )
        
        # 7. 가격 계산
        entry_price, stop_price, target_price = self._sizer.calculate_entry_stop_target(
            stock.current_price
        )
        
        # 8. 시그널 생성
        signal = Signal(
            stock_code=stock.code,
            stock_name=stock.name,
            market=stock.market,
            sector=stock.sector,
            grade=grade,
            score=score_detail,
            checklist=checklist,
            current_price=stock.current_price,
            entry_price=entry_price,
            stop_price=stop_price,
            target_price=target_price,
            change_pct=stock.change_pct,
            trading_value=stock.trading_value,
            foreign_5d=stock.foreign_5d,
            inst_5d=stock.inst_5d,
            foreign_20d=stock.foreign_20d,
            inst_20d=stock.inst_20d,
            news_items=news_items,
            signal_date=target_date.strftime("%Y-%m-%d")
        )
        
        return signal
    
    async def _rate_limit(self):
        """API Rate Limiting"""
        self._request_count += 1
        current_time = time.time()
        
        # 분당 15회 제한
        if self._request_count >= 15:
            elapsed = current_time - self._last_request_time
            if elapsed < 60:
                wait_time = 60 - elapsed
                print(f"[INFO] Rate limit: waiting {wait_time:.0f}s...")
                await asyncio.sleep(wait_time)
            self._request_count = 0
            self._last_request_time = time.time()
    
    def get_summary(self, signals: List[Signal]) -> Dict[str, Any]:
        """시그널 요약 통계"""
        return {
            "total": len(signals),
            "by_grade": {
                "S": len([s for s in signals if s.grade == "S"]),
                "A": len([s for s in signals if s.grade == "A"]),
                "B": len([s for s in signals if s.grade == "B"]),
            },
            "by_market": {
                "KOSPI": len([s for s in signals if s.market == "KOSPI"]),
                "KOSDAQ": len([s for s in signals if s.market == "KOSDAQ"]),
            },
            "avg_score": sum(s.score.total for s in signals) / len(signals) if signals else 0
        }


async def run_screener(
    capital: float = 50_000_000,
    markets: List[str] = None,
    save_result: bool = True
) -> ScreenerResult:
    """
    스크리너 실행 (엔트리 포인트)
    
    Args:
        capital: 투자 자본금
        markets: 분석 시장 리스트
        save_result: 결과 저장 여부
    
    Returns:
        ScreenerResult
    """
    start_time = time.time()
    
    async with SignalGenerator(capital=capital) as generator:
        signals = await generator.generate(markets=markets)
        summary = generator.get_summary(signals)
    
    processing_time = (time.time() - start_time) * 1000
    
    result = ScreenerResult(
        date=date.today().strftime("%Y-%m-%d"),
        total_candidates=summary.get('total', 0),
        filtered_count=len(signals),
        signals=signals,
        processing_time_ms=processing_time,
        updated_at=datetime.now().isoformat()
    )
    
    if save_result:
        save_result_to_json(result)
    
    print(f"\n[DONE] Generated {len(signals)} signals in {processing_time:.0f}ms")
    return result


def save_result_to_json(result: ScreenerResult):
    """결과 JSON 저장"""
    data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
    os.makedirs(data_dir, exist_ok=True)
    
    # Latest 파일
    latest_path = os.path.join(data_dir, 'jongga_v2_latest.json')
    with open(latest_path, 'w', encoding='utf-8') as f:
        json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)
    
    # 날짜별 히스토리
    date_str = result.date.replace('-', '')
    history_path = os.path.join(data_dir, f'jongga_v2_results_{date_str}.json')
    with open(history_path, 'w', encoding='utf-8') as f:
        json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)
    
    print(f"[INFO] Saved results to {latest_path}")


# CLI 실행
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="종가베팅 V2 스크리너")
    parser.add_argument("--capital", type=float, default=50_000_000, help="투자 자본금")
    parser.add_argument("--markets", nargs="+", default=["KOSPI", "KOSDAQ"], help="분석 시장")
    
    args = parser.parse_args()
    
    asyncio.run(run_screener(
        capital=args.capital,
        markets=args.markets
    ))
