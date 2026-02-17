#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI 분석 캐시 갱신 스크립트
kr_ai_analysis.json을 최신 VCP 시그널로 갱신합니다.
"""

import os
import sys
import json
import pandas as pd
from datetime import datetime

# 프로젝트 루트 설정
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv
load_dotenv()

def load_vcp_signals():
    """signals_log.csv에서 VCP 시그널 로드"""
    csv_path = os.path.join(PROJECT_ROOT, 'kr_market/data/signals_log.csv')
    
    if not os.path.exists(csv_path):
        print("❌ signals_log.csv 파일이 없습니다.")
        return []
    
    df = pd.read_csv(csv_path, dtype={'ticker': str})
    signals = []
    
    for _, row in df.iterrows():
        signals.append({
            'ticker': str(row.get('ticker', '')).zfill(6),
            'name': row.get('name', ''),
            'market': row.get('market', 'KOSPI'),
            'score': float(row.get('score', 0)),
            'contraction_ratio': float(row.get('contraction_ratio', 0.5)),
            'foreign_5d': int(row.get('foreign_5d', 0)),
            'inst_5d': int(row.get('inst_5d', 0)),
            'entry_price': float(row.get('entry_price', 0)),
            'current_price': float(row.get('current_price', 0)),
        })
    
    print(f"📊 {len(signals)}개 시그널 로드 완료")
    return signals


def refresh_ai_analysis(max_signals=10, skip_ai=False):
    """AI 분석 캐시 갱신 (상위 N개만 분석하여 API 비용 절감)"""
    from kr_market.kr_ai_analyzer import generate_ai_recommendations, fetch_market_indices
    
    signals = load_vcp_signals()
    
    if not signals:
        print("❌ 분석할 시그널이 없습니다.")
        return
    
    # 점수순 정렬 후 상위 N개만 분석
    signals.sort(key=lambda x: x['score'], reverse=True)
    top_signals = signals[:max_signals]
    
    print(f"🔍 상위 {len(top_signals)}개 종목 AI 분석 시작...")
    print(f"   대상: {', '.join([s['name'] for s in top_signals[:5]])}...")
    
    if skip_ai:
        # AI 호출 없이 기본 데이터만 저장 (테스트/빠른 갱신용)
        result = {
            'market_indices': fetch_market_indices(),
            'signals': top_signals,
            'generated_at': datetime.now().isoformat(),
            'signal_date': datetime.now().strftime('%Y-%m-%d'),
            'note': 'Quick refresh without AI analysis'
        }
    else:
        # 전체 AI 분석 실행
        result = generate_ai_recommendations(top_signals)
    
    # 저장
    output_path = os.path.join(PROJECT_ROOT, 'kr_market/data/kr_ai_analysis.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"✅ AI 분석 캐시 갱신 완료: {output_path}")
    print(f"   분석된 종목: {len(result.get('signals', []))}개")
    print(f"   생성 시각: {result.get('generated_at', 'N/A')}")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='AI 분석 캐시 갱신')
    parser.add_argument('--max', type=int, default=10, help='분석할 최대 종목 수 (기본: 10)')
    parser.add_argument('--skip-ai', action='store_true', help='AI 호출 없이 빠른 갱신')
    
    args = parser.parse_args()
    
    print("=" * 50)
    print("🚀 K-Stock AI 분석 캐시 갱신")
    print(f"   시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    refresh_ai_analysis(max_signals=args.max, skip_ai=args.skip_ai)
