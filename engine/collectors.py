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
import yfinance as yf

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
            
            # Reset index to get 'comp_code' or 'ticker' as a column
            df = df.reset_index()
            
            # Robust Column Renaming
            # PyKRX columns can be Korean ['티커', '시가', '고가', '저가', '종가', '거래량', '거래대금', '등락률']
            # or English ['ticker', 'open', 'high', 'low', 'close', 'volume', 'amount', 'rate']
            
            # Map known Korean/English headers to standard internal names
            col_map = {
                '티커': 'code', '종목코드': 'code', 'ticker': 'code',
                '시가': 'open', 'Open': 'open', 'open': 'open',
                '고가': 'high', 'High': 'high', 'high': 'high',
                '저가': 'low', 'Low': 'low', 'low': 'low',
                '종가': 'close', 'Close': 'close', 'close': 'close',
                '거래량': 'volume', 'Volume': 'volume', 'volume': 'volume',
                '거래대금': 'trading_value', 'Amount': 'trading_value', 'amount': 'trading_value', 'value': 'trading_value',
                '등락률': 'change_pct', 'Fluctuation': 'change_pct', 'fluctuation': 'change_pct', 'change': 'change_pct', 'rate': 'change_pct'
            }
            
            new_cols = []
            for c in df.columns:
                # remove spaces
                clean_c = str(c).strip()
                new_cols.append(col_map.get(clean_c, clean_c))
            
            df.columns = new_cols
            
            # Fallback for 'code' if it was the index and not named properly
            if 'code' not in df.columns and len(df.columns) >= 1:
                 # Check if the first column looks like a ticker (6 digits)
                 first_val = str(df.iloc[0, 0])
                 if len(first_val) >= 6 and first_val.isdigit():
                     rename_map = {df.columns[0]: 'code'}
                     df = df.rename(columns=rename_map)

            # Ensure essential columns exist
            required = ['code', 'close', 'trading_value', 'change_pct']
            for r in required:
                if r not in df.columns:
                    # Try to calculate if missing
                    if r == 'trading_value' and 'close' in df.columns and 'volume' in df.columns:
                         df['trading_value'] = df['close'] * df['volume']
                    elif r == 'change_pct':
                         # If change_pct is missing, we can't easily filter by it without yesterday's close.
                         # For now, assume 0 or handle error.
                         df['change_pct'] = 0.0
                    else:
                         print(f"[WARN] Missing column {r} in {market} data. Columns: {df.columns}")
                         continue

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
                    trading_value=int(row['trading_value']),
                    data_source="pykrx",
                    fetched_at=datetime.now().isoformat()
                ))
            
            return results
            
        except Exception as e:
            print(f"[ERROR] PyKRX Market OHLCV failed: {e}. Switching to YFinance Fallback...")
            return await self._get_top_gainers_yfinance_fallback(market, top_n)

    async def _get_top_gainers_yfinance_fallback(self, market: str, top_n: int) -> List[StockData]:
        """
        YFinance Fallback: Scan pre-defined major stocks
        Since we can't scan the whole market efficiently, we scan a static universe of major stocks.
        """
        # Major Stocks List (Examples)
        # In a real scenario, this should be a larger static list or fetched from a cache.
        kospi_majors = [
            ("005930", "삼성전자"), ("000660", "SK하이닉스"), ("035420", "NAVER"), ("035720", "카카오"),
            ("005380", "현대차"), ("000270", "기아"), ("006400", "삼성SDI"), ("051910", "LG화학"),
            ("086790", "하나금융지주"), ("105560", "KB금융"), ("055550", "신한지주"), ("032830", "삼성생명"),
            ("017800", "현대엘리베이터"), ("161390", "한국타이어앤테크놀로지"), ("005935", "삼성전자우"),
            ("012330", "현대모비스"), ("005490", "POSCO홀딩스"), ("034020", "두산에너빌리티")
        ]
        
        kosdaq_majors = [
            ("247540", "에코프로비엠"), ("086520", "에코프로"), ("091990", "셀트리온헬스케어"), ("028300", "HLB"),
            ("298380", "에이비엘바이오"), ("066970", "엘앤에프"), ("403870", "HPSP"), ("035900", "JYP Ent."),
            ("112040", "위메이드"), ("041510", "에스엠"), ("025980", "아난티"), ("005290", "동진쎄미켐")
        ]
        
        targets = kospi_majors if market == "KOSPI" else kosdaq_majors
        results = []
        
        for code, name in targets:
            try:
                df = await self._fetch_yfinance_data(code, days=5)
                if df.empty: continue
                
                last_row = df.iloc[-1]
                
                # Basic Filtering (Min Trading Value 10B KRW approx, >0% change)
                # Relaxed filter for fallback
                
                results.append(StockData(
                    code=code,
                    name=name,
                    market=market,
                    current_price=int(last_row['close']),
                    change_pct=float(last_row['change_pct']),
                    trading_value=int(last_row['trading_value']),
                    data_source="yfinance-fallback",
                    fetched_at=datetime.now().isoformat()
                ))
            except Exception as e:
                print(f"[WARN] YFinance Fallback failed for {code}: {e}")
                continue
            
        # Sort by change_pct
        results.sort(key=lambda x: x.change_pct, reverse=True)
        return results[:top_n]
    
    async def get_target_universe(self, target_date: date = None) -> List[str]:
        """
        Q1. 대상 범위: 거래대금 상위 300종목 (Top-300)
        Using OHLCV bulk fetch for reliability.
        """
        try:
            from pykrx import stock
            if target_date is None: 
                target_date = date.today() - timedelta(days=1)
                # Weekend correction
                if target_date.weekday() >= 5:
                    target_date -= timedelta(days=target_date.weekday() - 4)
            
            date_str = target_date.strftime("%Y%m%d")
            
            # Fetch All Tickers OHLCV
            try:
                kospi = stock.get_market_ohlcv(date_str, market="KOSPI")
                kosdaq = stock.get_market_ohlcv(date_str, market="KOSDAQ")
            except:
                # Retry with T-2 if T-1 fails (Holiday)
                target_date -= timedelta(days=1)
                date_str = target_date.strftime("%Y%m%d")
                kospi = stock.get_market_ohlcv(date_str, market="KOSPI")
                kosdaq = stock.get_market_ohlcv(date_str, market="KOSDAQ")

            
            # Calculate Trading Value if missing (Approx)
            # Columns: 시가, 고가, 저가, 종가, 거래량, (거래대금?), 등락률
            # Pykrx sometimes lacks '거래대금' column.
            if '거래대금' not in kospi.columns and '종가' in kospi.columns and '거래량' in kospi.columns:
                kospi['거래대금'] = kospi['종가'] * kospi['거래량']
            if '거래대금' not in kosdaq.columns and '종가' in kosdaq.columns and '거래량' in kosdaq.columns:
                kosdaq['거래대금'] = kosdaq['종가'] * kosdaq['거래량']
                
            # If '거래대금' still missing (e.g. English columns 'trading_value'), check that.
            # But usually it is recursive.
                
            # Sort
            top_kospi = kospi.nlargest(200, '거래대금')
            top_kosdaq = kosdaq.nlargest(100, '거래대금')
            
            universe = list(top_kospi.index) + list(top_kosdaq.index)
            print(f"[Universe] Selected {len(universe)} tickers (date: {date_str})")
            return universe
            
        except Exception as e:
            print(f"[ERROR] Failed to get universe: {e}")
            return []

    async def normalize_flow(self, code: str, target_date: date = None, window: int = 5) -> Dict[str, float]:
        """Q3. 수급 정규화: 거래대금 대비 비율 (%)"""
        if target_date is None: target_date = date.today()
        
        # 1. Try PyKrx first
        try:
            from pykrx import stock
            # Only try if we think PyKRX might work, or just try-except it
            supply = await self.get_supply_data(code, days=window)
            foreign_net = supply['foreign_5d']
            inst_net = supply['inst_5d']
        except Exception:
            foreign_net = 0
            inst_net = 0
        
        # 2. Fallback Scraper
        if foreign_net == 0 and inst_net == 0:
            scraped = self._scrape_naver_supply(code, window)
            if scraped:
                try:
                    df = await self.get_chart_data(code, days=1)
                    if not df.empty:
                        price = float(df['close'].iloc[-1])
                        foreign_net = scraped['foreign_sum'] * price
                        inst_net = scraped['inst_sum'] * price
                except: pass
        
        # 3. Get Total Trading Value
        try:
            df = await self.get_chart_data(code, days=window)
            total_trade_value = df['trading_value'].sum() if not df.empty else 1
        except:
            total_trade_value = 10_000_000_000
            
        if total_trade_value == 0: total_trade_value = 1
            
        # 4. Calculate Ratios
        foreign_pct = (foreign_net / total_trade_value) * 100
        inst_pct = (inst_net / total_trade_value) * 100
        
        return {
            'foreign_net': foreign_net,
            'inst_net': inst_net,
            'trading_value_sum': total_trade_value,
            'foreign_pct': round(foreign_pct, 4),
            'inst_pct': round(inst_pct, 4),
            'data_source': supply.get('source', 'unknown'),
            'fetched_at': datetime.now().isoformat()
        }
        
    def _scrape_naver_supply(self, code: str, days: int) -> Optional[Dict[str, int]]:
        """Verified fallback scraper"""
        try:
            url = f"https://finance.naver.com/item/frgn.naver?code={code}"
            headers = {'User-Agent': 'Mozilla/5.0'}
            resp = requests.get(url, headers=headers, timeout=3)
            soup = BeautifulSoup(resp.content, "html.parser")
            
            tables = soup.select('table.type2')
            foreign_sum = 0; inst_sum = 0; count = 0
            for table in tables:
                if '기관' in table.text and '외국인' in table.text:
                    rows = table.select('tr')
                    for row in rows:
                        cols = row.select('td')
                        if len(cols) > 6:
                            try:
                                f_val = int(cols[6].get_text().replace(',', ''))
                                i_val = int(cols[5].get_text().replace(',', ''))
                                foreign_sum += f_val
                                inst_sum += i_val
                                count += 1
                                if count >= days: break
                            except: continue
                    if count > 0: return {'foreign_sum': foreign_sum, 'inst_sum': inst_sum}
            return None
        except: return None

    # Keeping legacy method for compatibility but internally updated
    async def get_supply_data(self, code: str, days: int = 20) -> Dict[str, Any]:
        """수급 데이터 조회 (외국인/기관 순매매)"""
        try:
            from pykrx import stock
            end_date = date.today()
            start_date = end_date - timedelta(days=days + 10)
            start_str = start_date.strftime("%Y%m%d")
            end_str = end_date.strftime("%Y%m%d")
            
            df = stock.get_market_net_purchases_of_equities(start_str, end_str, code)
            
            if df.empty: return {'foreign_5d': 0, 'inst_5d': 0, 'foreign_20d': 0, 'inst_20d': 0}
            
            df = df.tail(days)
            foreign_col = '외국인' if '외국인' in df.columns else df.columns[0]
            inst_col = '기관합계' if '기관합계' in df.columns else '기관' if '기관' in df.columns else df.columns[1]
            
            return {
                'foreign_5d': foreign_5d, 
                'inst_5d': inst_5d, 
                'foreign_20d': 0, 
                'inst_20d': 0,
                'source': 'pykrx',
                'fetched_at': datetime.now().isoformat()
            }
        except Exception as e:
            print(f"[DEBUG] PyKRX supply fetch failed for {code}: {e}")
            return {'foreign_5d': 0, 'inst_5d': 0, 'foreign_20d': 0, 'inst_20d': 0, 'source': 'none'}

    
    async def get_chart_data(self, code: str, days: int = 60) -> pd.DataFrame:
        """차트 데이터 조회 (OHLCV) - Fixed for 6 columns"""
        try:
            from pykrx import stock
            end_date = date.today()
            start_date = end_date - timedelta(days=days + 10)
            start_str = start_date.strftime("%Y%m%d")
            end_str = end_date.strftime("%Y%m%d")
            
            df = stock.get_market_ohlcv(start_str, end_str, code)
            
            if df.empty: return pd.DataFrame()
            
            df = df.tail(days)
            # Fix: Handle 6 columns vs 7
            if len(df.columns) == 6:
                df.columns = ['open', 'high', 'low', 'close', 'volume', 'change_pct']
                df['trading_value'] = df['close'] * df['volume']
            elif len(df.columns) == 7:
                 df.columns = ['open', 'high', 'low', 'close', 'volume', 'trading_value', 'change_pct']
            
            return df
        except Exception as e:
            print(f"Chart data error {code} (PyKRX): {e}. Trying YFinance...")
            return await self._fetch_yfinance_data(code, days)

    async def _fetch_yfinance_data(self, code: str, days: int = 60) -> pd.DataFrame:
        """YFinance Fallback for Chart Data"""
        try:
            # Determine suffix based on market (Need market info, but here we just try both or guess)
            # Optimization: Try .KS first, then .KQ if empty
            ticker = f"{code}.KS"
            stock = yf.Ticker(ticker)
            history = stock.history(period=f"{days+20}d")
            
            if history.empty:
                ticker = f"{code}.KQ"
                stock = yf.Ticker(ticker)
                history = stock.history(period=f"{days+20}d")
            
            if history.empty:
                return pd.DataFrame()
            
            # Formatting to match internal structure
            # YF: Open, High, Low, Close, Volume
            history = history.reset_index()
            history.columns = [c.lower() for c in history.columns]
            
            # Calculate basics
            history['change_pct'] = history['close'].pct_change() * 100
            history['trading_value'] = history['close'] * history['volume']
            
            # Select and rename
            df = history[['open', 'high', 'low', 'close', 'volume', 'trading_value', 'change_pct']].tail(days)
            
            return df
            
        except Exception as e:
             print(f"YFinance error {code}: {e}")
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
                    published_at=pub_date,
                    data_source="naver-finance-item",
                    fetched_at=datetime.now().isoformat()
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
                    published_at=datetime.now().strftime('%Y-%m-%d'),
                    data_source="naver-search",
                    fetched_at=datetime.now().isoformat()
                ))
            
            return items
            
        except Exception as e:
            print(f"[WARN] Naver search news error: {e}")
            return []

