#!/usr/bin/env python3
"""
K-Stock 데이터 정합성 검사 스크립트
- 만료된 시그널 자동 아카이브
- 데이터 무결성 검사
- 중복 데이터 감지
"""

import os
import json
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

# 설정
DATA_DIR = Path(__file__).parent / "kr_market" / "data"
SIGNALS_CSV = DATA_DIR / "signals_log.csv"
AI_ANALYSIS_JSON = DATA_DIR / "kr_ai_analysis.json"
HISTORY_DIR = DATA_DIR / "history"
MAX_SIGNAL_AGE_DAYS = 7

def ensure_dirs():
    """필요한 디렉토리 생성"""
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)

def check_signal_freshness():
    """시그널 신선도 검사"""
    print("\n=== 시그널 신선도 검사 ===")
    
    if not SIGNALS_CSV.exists():
        print("❌ signals_log.csv 파일이 없습니다.")
        return
    
    df = pd.read_csv(SIGNALS_CSV)
    today = datetime.now().date()
    
    fresh_count = 0
    recent_count = 0
    expired_count = 0
    expired_tickers = []
    
    for _, row in df.iterrows():
        try:
            signal_date = datetime.strptime(str(row['signal_date']), '%Y-%m-%d').date()
            days_old = (today - signal_date).days
            
            if days_old <= 1:
                fresh_count += 1
            elif days_old <= MAX_SIGNAL_AGE_DAYS:
                recent_count += 1
            else:
                expired_count += 1
                expired_tickers.append((row['ticker'], row['name'], days_old))
        except:
            expired_count += 1
            expired_tickers.append((row['ticker'], 'PARSE_ERROR', 999))
    
    print(f"🟢 실시간 (D+0~1): {fresh_count}개")
    print(f"🟡 최근 (D+2~7): {recent_count}개")
    print(f"🔴 만료 (D+8 이상): {expired_count}개")
    
    if expired_tickers:
        print(f"\n⚠️ 만료된 시그널 목록 (상위 10개):")
        for ticker, name, days in expired_tickers[:10]:
            print(f"   - {ticker} {name}: D+{days}")
    
    return expired_tickers

def archive_expired_signals(expired_tickers):
    """만료된 시그널을 history 폴더로 이동"""
    if not expired_tickers:
        print("\n✅ 아카이브할 만료 시그널이 없습니다.")
        return
    
    print(f"\n=== 만료 시그널 아카이브 ({len(expired_tickers)}개) ===")
    
    df = pd.read_csv(SIGNALS_CSV)
    expired_ticker_set = {t[0] for t in expired_tickers}
    
    # 만료 데이터 분리
    expired_df = df[df['ticker'].isin(expired_ticker_set)]
    active_df = df[~df['ticker'].isin(expired_ticker_set)]
    
    # 아카이브 저장
    archive_filename = f"archived_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    archive_path = HISTORY_DIR / archive_filename
    expired_df.to_csv(archive_path, index=False)
    print(f"📦 아카이브 저장: {archive_path}")
    
    # 활성 시그널만 유지
    active_df.to_csv(SIGNALS_CSV, index=False)
    print(f"✅ 활성 시그널 {len(active_df)}개 유지, {len(expired_df)}개 아카이브 완료")

def check_data_integrity():
    """데이터 무결성 검사"""
    print("\n=== 데이터 무결성 검사 ===")
    
    issues = []
    
    # 1. CSV 파일 검사
    if SIGNALS_CSV.exists():
        df = pd.read_csv(SIGNALS_CSV)
        
        # 중복 티커 검사
        duplicates = df[df.duplicated(subset=['ticker'], keep=False)]
        if not duplicates.empty:
            issues.append(f"중복 티커 발견: {duplicates['ticker'].unique().tolist()}")
        
        # 비정상 가격 검사
        invalid_prices = df[df['entry_price'] <= 0]
        if not invalid_prices.empty:
            issues.append(f"비정상 진입가 (0 이하): {len(invalid_prices)}개")
        
        # 미래 날짜 검사
        today = datetime.now().strftime('%Y-%m-%d')
        future_dates = df[df['signal_date'] > today]
        if not future_dates.empty:
            issues.append(f"미래 날짜 시그널: {len(future_dates)}개")
    
    # 2. JSON 파일 검사
    if AI_ANALYSIS_JSON.exists():
        with open(AI_ANALYSIS_JSON, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        json_tickers = {s['ticker'] for s in data.get('signals', [])}
        csv_tickers = set(df['ticker'].astype(str)) if SIGNALS_CSV.exists() else set()
        
        # 불일치 검사
        only_in_json = json_tickers - csv_tickers
        only_in_csv = csv_tickers - json_tickers
        
        if only_in_json:
            issues.append(f"JSON에만 있는 티커: {len(only_in_json)}개")
        if only_in_csv:
            issues.append(f"CSV에만 있는 티커: {len(only_in_csv)}개")
    
    # 결과 출력
    if issues:
        print("❌ 발견된 문제:")
        for issue in issues:
            print(f"   - {issue}")
    else:
        print("✅ 모든 무결성 검사 통과")
    
    return issues

def generate_report():
    """검사 리포트 생성"""
    print("\n" + "="*50)
    print("K-Stock 데이터 정합성 검사 리포트")
    print(f"검사 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*50)
    
    ensure_dirs()
    expired = check_signal_freshness()
    issues = check_data_integrity()
    
    print("\n" + "="*50)
    print("요약")
    print("="*50)
    print(f"• 만료 시그널: {len(expired)}개")
    print(f"• 무결성 이슈: {len(issues)}개")
    
    if expired:
        response = input("\n만료된 시그널을 아카이브하시겠습니까? (y/n): ")
        if response.lower() == 'y':
            archive_expired_signals(expired)
    
    print("\n✅ 검사 완료")

if __name__ == "__main__":
    generate_report()
