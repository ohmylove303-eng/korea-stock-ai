#!/usr/bin/env python3
"""
빠른 VCP 스캔 - 상위 200개 종목만 스캔 (약 5분 소요)
"""

import os
import sys
from datetime import datetime
import pandas as pd

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR) if 'kr_market' in SCRIPT_DIR else SCRIPT_DIR
sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)

print("="*50)
print(f"빠른 VCP 스캔 시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("대상: 시가총액 상위 200개 종목")
print("="*50)

try:
    from pykrx import stock
    import FinanceDataReader as fdr
    
    # 오늘 날짜
    today = datetime.now().strftime('%Y%m%d')
    today_dash = datetime.now().strftime('%Y-%m-%d')
    
    # KOSPI + KOSDAQ 상위 200개 종목 가져오기
    print("\n📊 시가총액 상위 종목 로딩 중...")
    
    kospi_caps = stock.get_market_cap(today, market="KOSPI")
    kosdaq_caps = stock.get_market_cap(today, market="KOSDAQ")
    
    # 상위 150 KOSPI + 상위 50 KOSDAQ
    top_kospi = kospi_caps.nlargest(150, '시가총액').index.tolist()
    top_kosdaq = kosdaq_caps.nlargest(50, '시가총액').index.tolist()
    target_tickers = top_kospi + top_kosdaq
    
    print(f"✅ 스캔 대상: {len(target_tickers)}개 종목")
    
    # VCP 스캔 로직 (간소화 버전)
    signals = []
    
    for i, ticker in enumerate(target_tickers):
        try:
            # 60일 OHLCV 데이터
            df = stock.get_market_ohlcv(
                (datetime.now() - pd.Timedelta(days=90)).strftime('%Y%m%d'),
                today,
                ticker
            )
            
            if df.empty or len(df) < 20:
                continue
            
            # 기본 지표 계산
            close = df['종가'].iloc[-1]
            high_20d = df['고가'].tail(20).max()
            low_20d = df['저가'].tail(20).min()
            
            # 변동성 수축 비율 (VCP 핵심 지표)
            contraction = (high_20d - low_20d) / high_20d if high_20d > 0 else 1
            
            # 거래량 체크
            vol_avg = df['거래량'].tail(20).mean()
            vol_today = df['거래량'].iloc[-1]
            
            # 수급 데이터
            try:
                inv_data = stock.get_market_trading_value_by_date(
                    (datetime.now() - pd.Timedelta(days=7)).strftime('%Y%m%d'),
                    today,
                    ticker
                )
                foreign_5d = inv_data['외국인합계'].sum() if '외국인합계' in inv_data.columns else 0
                inst_5d = inv_data['기관합계'].sum() if '기관합계' in inv_data.columns else 0
            except:
                foreign_5d, inst_5d = 0, 0
            
            # VCP 조건 체크
            is_vcp = contraction < 0.15  # 15% 이내 수축
            is_vol_ok = vol_today > vol_avg * 0.5  # 평균 50% 이상 거래량
            is_supply_ok = foreign_5d > 0 or inst_5d > 0  # 수급 유입
            
            if is_vcp and is_vol_ok and is_supply_ok:
                # 점수 계산
                score = 50
                score += (1 - contraction) * 30  # 수축률 점수
                score += min(10, (foreign_5d + inst_5d) / 100000000)  # 수급 점수
                score += 10 if vol_today > vol_avg else 0  # 거래량 점수
                
                name = stock.get_market_ticker_name(ticker)
                
                signals.append({
                    'ticker': ticker,
                    'name': name,
                    'current_price': close,
                    'entry_price': close,
                    'score': round(score, 1),
                    'contraction_ratio': round(contraction, 3),
                    'foreign_5d': int(foreign_5d),
                    'inst_5d': int(inst_5d),
                    'signal_date': today_dash
                })
                print(f"🔥 Signal Found: {name} ({ticker}) | Score: {round(score, 1)}")
            
            # 진행률 표시
            if (i + 1) % 20 == 0:
                print(f"  ... {i + 1}/{len(target_tickers)} 종목 스캔 완료")
                
        except Exception as e:
            continue
    
    # 결과 저장
    if signals:
        signals_df = pd.DataFrame(signals)
        signals_df = signals_df.sort_values('score', ascending=False)
        
        # CSV 저장
        output_path = os.path.join(PROJECT_ROOT, 'kr_market', 'data', 'signals_log.csv')
        signals_df.to_csv(output_path, index=False)
        
        print("\n" + "="*50)
        print(f"✅ 스캔 완료! {len(signals)}개 신규 시그널 발견")
        print("="*50)
        print("\n📋 상위 10개 시그널:")
        for _, sig in signals_df.head(10).iterrows():
            print(f"  - {sig['name']} ({sig['ticker']}) | Score: {sig['score']} | 수축률: {sig['contraction_ratio']}")
    else:
        print("\n⚠️ VCP 조건을 만족하는 종목이 없습니다.")
    
    print(f"\n완료 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
except Exception as e:
    print(f"❌ 스캔 오류: {e}")
    import traceback
    traceback.print_exc()
