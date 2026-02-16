#!/usr/bin/env python3
"""
V2 12점 채점 브릿지 — quick_scan.py 결과에 engine/scorer 12점 시스템 적용
signals_log.csv → data/jongga_v2_latest.json
"""

import asyncio
import json
import os
import sys
from datetime import datetime, date

import pandas as pd

# Project root
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

from engine.scorer import Scorer
from engine.collectors import DataCollector, NewsCollector
from engine.llm_analyzer import LLMAnalyzer
from engine.config import SignalConfig

async def main():
    print("=" * 60)
    print(f"🎯 V2 12점 채점 시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("  quick_scan 결과 → engine/scorer 12점 채점 적용")
    print("=" * 60)

    csv_path = os.path.join(ROOT, 'kr_market', 'data', 'signals_log.csv')
    if not os.path.exists(csv_path):
        print("❌ signals_log.csv가 없습니다. 먼저 quick_scan.py를 실행하세요.")
        return

    df = pd.read_csv(csv_path, encoding='utf-8-sig')
    df['ticker'] = df['ticker'].astype(str).str.zfill(6)
    print(f"📊 입력: {len(df)}개 종목 from signals_log.csv")

    # 상위 30개만 채점 (API 비용 절감)
    df = df.nlargest(30, 'score')

    config = SignalConfig.default()
    scorer = Scorer(config)
    collector = DataCollector(config)
    
    # News + LLM (optional — may hit rate limits)
    use_llm = True
    news_collector = None
    llm_analyzer = None
    
    if use_llm:
        try:
            news_collector = NewsCollector()
            await news_collector.__aenter__()
            llm_analyzer = LLMAnalyzer()
            print("✅ 뉴스 수집기 + LLM 분석기 초기화 완료")
        except Exception as e:
            print(f"⚠️ LLM 초기화 실패 (뉴스 없이 진행): {e}")
            use_llm = False

    signals = []
    
    for i, (_, row) in enumerate(df.iterrows()):
        ticker = row['ticker']
        name = row.get('name', ticker)
        
        print(f"\n[{i+1}/{len(df)}] {name} ({ticker})...")

        try:
            # 1. 차트 데이터 (60일 OHLCV)
            chart_data = await collector.get_chart_data(ticker, days=60)
            
            # 2. 수급 데이터
            supply_data = {
                'foreign_5d': int(row.get('foreign_5d', 0)),
                'inst_5d': int(row.get('inst_5d', 0)),
            }
            
            # Fresh supply fetch attempt
            try:
                fresh_supply = await collector.get_supply_data(ticker, days=5)
                if fresh_supply.get('foreign_5d', 0) != 0 or fresh_supply.get('inst_5d', 0) != 0:
                    supply_data = fresh_supply
                    print(f"  수급: 외인 {supply_data['foreign_5d']:,} / 기관 {supply_data['inst_5d']:,}")
            except:
                pass

            # 3. 뉴스 + LLM 분석
            news_items = []
            news_score = 1  # default
            news_reason = "기본 뉴스 점수"
            
            if use_llm and news_collector and llm_analyzer:
                try:
                    raw_news = await news_collector.collect_news(name, ticker)
                    from engine.models import NewsItem as NI
                    news_items = [
                        NI(title=n.title, source=n.source, url=n.url, published_at=n.published_at)
                        for n in raw_news
                    ]
                    if news_items:
                        news_dicts = [{"title": n.title, "source": n.source} for n in news_items]
                        llm_result = await llm_analyzer.analyze_news_sentiment(name, news_dicts)
                        news_score = llm_result.get('score', 1)
                        news_reason = llm_result.get('reason', '')
                        print(f"  뉴스: {len(news_items)}건 / LLM 점수: {news_score}")
                except Exception as e:
                    print(f"  ⚠️ 뉴스/LLM 실패: {e}")

            # 4. 12점 채점!
            current_price = float(row.get('current_price', 0))
            trading_value = int(current_price * 1_000_000)  # approx from price
            change_pct = 0.0

            score_detail, checklist = scorer.calculate(
                trading_value=trading_value,
                change_pct=change_pct,
                chart_data=chart_data,
                news_items=news_items,
                news_score=news_score,
                news_reason=news_reason,
                supply_data=supply_data
            )

            # 5. 등급 결정
            grade = scorer.determine_grade(score_detail, trading_value, change_pct)

            total = score_detail.total
            print(f"  📊 12점 채점: {total}/12 ({grade}급)")
            print(f"     뉴스:{score_detail.news} 거래:{score_detail.volume} 차트:{score_detail.chart} 캔들:{score_detail.candle} 조정:{score_detail.consolidation} 수급:{score_detail.supply}")

            signals.append({
                'stock_code': ticker,
                'stock_name': name,
                'market': 'KOSPI',
                'grade': grade,
                'score': {
                    'total': total,
                    'news': score_detail.news,
                    'volume': score_detail.volume,
                    'chart': score_detail.chart,
                    'candle': score_detail.candle,
                    'consolidation': score_detail.consolidation,
                    'supply': score_detail.supply,
                    'llm_reason': news_reason
                },
                'current_price': current_price,
                'entry_price': current_price,
                'stop_price': round(current_price * 0.93, 0),
                'target_price': round(current_price * 1.15, 0),
                'change_pct': change_pct,
                'trading_value': trading_value,
                'foreign_5d': supply_data.get('foreign_5d', 0),
                'inst_5d': supply_data.get('inst_5d', 0),
                'news_items': [{'title': n.title, 'source': n.source} for n in news_items],
                'signal_date': datetime.now().strftime('%Y-%m-%d'),
                'contraction_ratio': float(row.get('contraction_ratio', 0.5)),
            })

            # Rate limit
            await asyncio.sleep(1)

        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"  ❌ 채점 실패: {e}")
            continue

    # Sort by total score
    signals.sort(key=lambda x: x['score']['total'], reverse=True)

    # Save
    data_dir = os.path.join(ROOT, 'data')
    os.makedirs(data_dir, exist_ok=True)
    
    result = {
        'signals': signals,
        'date': datetime.now().strftime('%Y-%m-%d'),
        'processing_time_ms': 0,
        'updated_at': datetime.now().isoformat(),
        'source': 'ENGINE_SCORER_V2'
    }
    
    output_path = os.path.join(data_dir, 'jongga_v2_latest.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 60)
    print(f"✅ 완료! {len(signals)}개 종목 12점 채점 → {output_path}")
    print("=" * 60)
    
    # Summary
    for s in signals[:10]:
        sc = s['score']
        print(f"  [{s['grade']}] {s['stock_name']} ({s['stock_code']}) | {sc['total']}/12 | 뉴스:{sc['news']} 차트:{sc['chart']} 수급:{sc['supply']}")

    if news_collector:
        await news_collector.__aexit__(None, None, None)

if __name__ == '__main__':
    asyncio.run(main())
