"""
종가베팅 데이터 수집기
- pykrx: 가격, 수급 데이터
- 네이버 금융: 뉴스 크롤링
"""

import os
import re
import asyncio
from datetime import date, datetime, timedelta
from typing import List, Dict, Optional, Any
from dataclasses import dataclass

import pandas as pd
import requests
from bs4 import BeautifulSoup

from .models import StockData, NewsItem
from .config import SignalConfig


class DataCollector:
    """주가 및 수급 데이터 수집기"""
    
    def __init__(self, config: SignalConfig = None):
        self.config = config or SignalConfig.default()
        self._price_cache: Dict[str, pd.DataFrame] = {}
        self._inst_cache: Dict[str, pd.DataFrame] = {}
    
    async def get_top_gainers(
        self,
        market: str = "KOSPI",
        top_n: int = 50,
        target_date: date = None
    ) -> List[StockData]:
        """
        상승 상위 종목 조회
        
        Args:
            market: KOSPI 또는 KOSDAQ
            top_n: 상위 N개
            target_date: 조회 날짜 (None이면 오늘)
        """
        try:
            from pykrx import stock
            
            if target_date is None:
                target_date = date.today()
            
            date_str = target_date.strftime("%Y%m%d")
            
            # 시장 데이터 조회
            df = stock.get_market_ohlcv(date_str, market=market)
            
            if df.empty:
                print(f"[WARN] No data for {market} on {date_str}")
                return []
            
            # 등락률 계산 (전일 대비)
            df = df.reset_index()
            df.columns = ['code', 'open', 'high', 'low', 'close', 'volume', 'trading_value', 'change_pct']
            
            # 필터: 거래대금 500억 이상, 등락률 5% ~ 29.9%
            df = df[
                (df['trading_value'] >= self.config.min_trading_value) &
                (df['change_pct'] >= self.config.min_change_pct) &
                (df['change_pct'] <= self.config.max_change_pct) &
                (df['close'] >= self.config.min_price) &
                (df['close'] <= self.config.max_price)
            ]
            
            # 정렬 및 상위 N개
            df = df.sort_values('change_pct', ascending=False).head(top_n)
            
            results = []
            for _, row in df.iterrows():
                code = str(row['code']).zfill(6)
                name = stock.get_market_ticker_name(code)
                
                # 제외 키워드 체크
                if any(kw in name for kw in self.config.exclude_keywords):
                    continue
                
                results.append(StockData(
                    code=code,
                    name=name,
                    market=market,
                    current_price=int(row['close']),
                    change_pct=float(row['change_pct']),
                    trading_value=int(row['trading_value'])
                ))
            
            return results
            
        except Exception as e:
            print(f"[ERROR] Failed to get top gainers: {e}")
            return []
    
    async def get_supply_data(
        self,
        code: str,
        days: int = 20
    ) -> Dict[str, Any]:
        """
        수급 데이터 조회 (외국인/기관 순매매)
        """
        try:
            from pykrx import stock
            
            end_date = date.today()
            start_date = end_date - timedelta(days=days + 10)  # 여유분
            
            start_str = start_date.strftime("%Y%m%d")
            end_str = end_date.strftime("%Y%m%d")
            
            df = stock.get_market_net_purchases_of_equities(
                start_str, end_str, code
            )
            
            if df.empty:
                return {
                    'foreign_5d': 0, 'inst_5d': 0,
                    'foreign_20d': 0, 'inst_20d': 0
                }
            
            # 최근 데이터 기준
            df = df.tail(days)
            
            foreign_col = '외국인' if '외국인' in df.columns else df.columns[0]
            inst_col = '기관합계' if '기관합계' in df.columns else '기관' if '기관' in df.columns else df.columns[1]
            
            foreign_5d = int(df[foreign_col].tail(5).sum())
            inst_5d = int(df[inst_col].tail(5).sum())
            foreign_20d = int(df[foreign_col].sum())
            inst_20d = int(df[inst_col].sum())
            
            return {
                'foreign_5d': foreign_5d,
                'inst_5d': inst_5d,
                'foreign_20d': foreign_20d,
                'inst_20d': inst_20d
            }
            
        except Exception as e:
            print(f"[WARN] Supply data failed for {code}: {e}")
            return {
                'foreign_5d': 0, 'inst_5d': 0,
                'foreign_20d': 0, 'inst_20d': 0
            }
    
    async def get_chart_data(
        self,
        code: str,
        days: int = 60
    ) -> pd.DataFrame:
        """
        차트 데이터 조회 (OHLCV)
        """
        try:
            from pykrx import stock
            
            end_date = date.today()
            start_date = end_date - timedelta(days=days + 10)
            
            start_str = start_date.strftime("%Y%m%d")
            end_str = end_date.strftime("%Y%m%d")
            
            df = stock.get_market_ohlcv(start_str, end_str, code)
            
            if df.empty:
                return pd.DataFrame()
            
            df = df.tail(days)
            df.columns = ['open', 'high', 'low', 'close', 'volume', 'trading_value', 'change_pct']
            
            return df
            
        except Exception as e:
            print(f"[WARN] Chart data failed for {code}: {e}")
            return pd.DataFrame()


class NewsCollector:
    """뉴스 수집기 (requests 기반)"""
    
    MAJOR_SOURCES = {
        "한국경제": 0.9,
        "매일경제": 0.9,
        "머니투데이": 0.85,
        "서울경제": 0.85,
        "이데일리": 0.85,
        "연합뉴스": 0.85,
        "뉴스1": 0.8,
    }
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, *args):
        pass
    
    async def collect_news(
        self,
        stock_name: str,
        stock_code: str,
        max_items: int = 5
    ) -> List[NewsItem]:
        """
        종목 관련 뉴스 수집
        
        1차: 네이버 금융 종목 뉴스
        2차: 네이버 뉴스 검색 (폴백)
        """
        news_items = []
        
        # 1. 네이버 금융 종목 뉴스
        try:
            items = await self._fetch_naver_finance_news(stock_code)
            news_items.extend(items)
        except Exception as e:
            print(f"[WARN] Naver Finance news failed: {e}")
        
        # 2. 검색으로 보충
        if len(news_items) < max_items:
            try:
                items = await self._fetch_naver_search_news(stock_name)
                for item in items:
                    if len(news_items) >= max_items:
                        break
                    # 중복 제거
                    if not any(n.title == item.title for n in news_items):
                        news_items.append(item)
            except Exception as e:
                print(f"[WARN] Naver search news failed: {e}")
        
        return news_items[:max_items]
    
    async def _fetch_naver_finance_news(
        self,
        stock_code: str,
        max_items: int = 5
    ) -> List[NewsItem]:
        """네이버 금융 종목 뉴스 크롤링"""
        url = f"https://finance.naver.com/item/news_news.naver?code={stock_code}"
        
        try:
            # requests 동기 요청 (asyncio에서 호출)
            response = await asyncio.to_thread(
                requests.get, url, headers=self.headers, timeout=10
            )
            
            if response.status_code != 200:
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            items = []
            table = soup.select_one('table.type5')
            
            if not table:
                return []
            
            for row in table.select('tr')[:max_items]:
                title_el = row.select_one('td.title a')
                source_el = row.select_one('td.info')
                date_el = row.select_one('td.date')
                
                if not title_el:
                    continue
                
                title = title_el.get_text(strip=True)
                href = title_el.get('href', '')
                source = source_el.get_text(strip=True) if source_el else ''
                pub_date = date_el.get_text(strip=True) if date_el else ''
                
                # URL 완성
                if href and not href.startswith('http'):
                    href = f"https://finance.naver.com{href}"
                
                items.append(NewsItem(
                    title=title,
                    source=source,
                    url=href,
                    published_at=pub_date
                ))
            
            return items
            
        except Exception as e:
            print(f"[WARN] Naver finance news fetch error: {e}")
            return []
    
    async def _fetch_naver_search_news(
        self,
        keyword: str,
        max_items: int = 5
    ) -> List[NewsItem]:
        """네이버 뉴스 검색"""
        encoded = keyword.replace(' ', '+')
        url = f"https://search.naver.com/search.naver?where=news&query={encoded}&sort=1"
        
        try:
            response = await asyncio.to_thread(
                requests.get, url, headers=self.headers, timeout=10
            )
            
            if response.status_code != 200:
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            items = []
            news_list = soup.select('div.news_area')
            
            for news in news_list[:max_items]:
                title_el = news.select_one('a.news_tit')
                source_el = news.select_one('a.info.press')
                
                if not title_el:
                    continue
                
                title = title_el.get('title', title_el.get_text(strip=True))
                href = title_el.get('href', '')
                source = source_el.get_text(strip=True) if source_el else ''
                
                items.append(NewsItem(
                    title=title,
                    source=source,
                    url=href,
                    published_at=datetime.now().strftime('%Y-%m-%d')
                ))
            
            return items
            
        except Exception as e:
            print(f"[WARN] Naver search news error: {e}")
            return []

