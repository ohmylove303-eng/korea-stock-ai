# KR Market AI Stock Analysis System - Blueprint Part 9: Supporting Modules

> **Version**: 1.0  
> **Last Updated**: 2026-01-04  
> **Files**: `market_gate.py`, `scheduler.py`, `all_institutional_trend_data.py`

---

## 1. Overview

These supporting modules provide:
- **Market Gate**: Market condition scoring and signal gating (GREEN/YELLOW/RED)
- **Scheduler**: Automated data update scheduling
- **Institutional Data**: Foreign and institutional investor flow analysis

---

## 2. market_gate.py (301 lines)

Provides market condition analysis using technical indicators.

### 2.1 Key Classes

```python
from dataclasses import dataclass
from typing import Dict, List, Any

@dataclass
class SectorResult:
    name: str
    ticker: str
    score: int
    signal: str
    price: float
    change_1d: float
    rsi: float
    rs_vs_kospi: float

@dataclass
class KRMarketGateResult:
    gate: str          # "GREEN" | "YELLOW" | "RED"
    score: int         # 0-100
    reasons: List[str]
    sectors: List[SectorResult]
    metrics: Dict[str, Any]
```

### 2.2 Sector ETFs

```python
KR_SECTORS = {
    "반도체": "091160.KS",   # KODEX 반도체
    "2차전지": "305720.KS",  # KODEX 2차전지산업
    "자동차": "091170.KS",   # KODEX 자동차
    "IT": "102780.KS",       # KODEX IT
    "은행": "102960.KS",     # KODEX 은행
    "철강": "117680.KS",     # KODEX 철강
    "증권": "102970.KS",     # KODEX 증권
}
```

### 2.3 Technical Indicators

```python
def calculate_rsi(series: pd.Series, period: int = 14) -> float:
    """Calculate RSI (Relative Strength Index)"""
    delta = series.diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else 50.0

def calculate_macd_signal(series: pd.Series) -> str:
    """Calculate MACD signal"""
    ema12 = series.ewm(span=12, adjust=False).mean()
    ema26 = series.ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    
    if macd_line.iloc[-1] > signal_line.iloc[-1]:
        return "BULLISH"
    else:
        return "BEARISH"

def calculate_volume_ratio(volume: pd.Series, period: int = 20) -> float:
    """Calculate volume ratio vs 20-day average"""
    avg_vol = volume.rolling(period).mean().iloc[-1]
    return float(volume.iloc[-1] / avg_vol) if avg_vol > 0 else 1.0

def calculate_rs_vs_benchmark(sector_close: pd.Series, bench_close: pd.Series, period: int = 20) -> float:
    """Calculate Relative Strength vs KOSPI"""
    sector_ret = (sector_close.iloc[-1] - sector_close.iloc[-period]) / sector_close.iloc[-period]
    bench_ret = (bench_close.iloc[-1] - bench_close.iloc[-period]) / bench_close.iloc[-period]
    return float((sector_ret - bench_ret) * 100)
```

### 2.4 Enhanced Scoring

```python
def calculate_enhanced_score(close: pd.Series, volume: pd.Series, kospi_close: pd.Series = None) -> Tuple[int, str, dict]:
    """Enhanced scoring with RSI, MACD, Volume, RS"""
    if len(close) < 60:
        return 50, "NEUTRAL", {}
    
    score = 0
    details = {}
    
    # 1. Trend Alignment (25 pts)
    e20 = close.rolling(20).mean()
    e60 = close.rolling(60).mean()
    curr_price, curr_e20, curr_e60 = close.iloc[-1], e20.iloc[-1], e60.iloc[-1]
    
    if curr_price > curr_e20 > curr_e60:
        score += 25
        details['trend'] = '정배열 강세'
    elif curr_price > curr_e20:
        score += 15
        details['trend'] = '단기 상승'
    elif curr_price > curr_e60:
        score += 10
        details['trend'] = '60MA 지지'
    else:
        details['trend'] = '하락추세'
    
    # 2. RSI (25 pts)
    rsi = calculate_rsi(close)
    details['rsi'] = rsi
    if 50 <= rsi <= 70:
        score += 25
    elif 40 <= rsi < 50:
        score += 15
    elif 30 <= rsi < 40:
        score += 20  # Oversold bounce potential
    elif rsi < 30:
        score += 10
    
    # 3. MACD Signal (20 pts)
    macd_sig = calculate_macd_signal(close)
    details['macd'] = macd_sig
    if macd_sig == "BULLISH":
        score += 20
    
    # 4. Volume Confirmation (15 pts)
    vol_ratio = calculate_volume_ratio(volume)
    details['vol_ratio'] = vol_ratio
    if vol_ratio > 1.2:
        score += 15
    elif vol_ratio > 0.8:
        score += 10
    
    # 5. Relative Strength vs KOSPI (15 pts)
    if kospi_close is not None and len(kospi_close) >= 20:
        rs = calculate_rs_vs_benchmark(close, kospi_close)
        details['rs_vs_kospi'] = rs
        if rs > 2:
            score += 15
        elif rs > 0:
            score += 10
        elif rs > -2:
            score += 5
    
    score = int(min(100, max(0, score)))
    signal = "BULLISH" if score >= 70 else ("BEARISH" if score < 40 else "NEUTRAL")
    return score, signal, details
```

### 2.5 Main Function

```python
def run_kr_market_gate() -> KRMarketGateResult:
    """Run enhanced KR Market Gate Analysis"""
    # 1. Fetch data from Yahoo Finance / FinanceDataReader
    # 2. Calculate KOSPI gate score
    # 3. Calculate sector scores
    # 4. Determine gate (GREEN/YELLOW/RED)
    # 5. Return comprehensive result
```

---

## 3. scheduler.py (389 lines)

Automated scheduling for data updates.

### 3.1 Configuration

```python
class Config:
    """Deployment configuration"""
    
    BASE_DIR = os.environ.get('KR_MARKET_DIR', '/path/to/project')
    LOG_DIR = os.environ.get('KR_MARKET_LOG_DIR', os.path.join(BASE_DIR, 'logs'))
    DATA_DIR = os.path.join(BASE_DIR, 'kr_market')
    
    # Schedule times (KST)
    PRICE_UPDATE_TIME = '16:00'   # Daily prices
    INST_UPDATE_TIME = '16:10'    # Institutional data
    SIGNAL_SCAN_TIME = '16:20'    # VCP signal scan
    REPORT_TIME = '16:30'         # Daily report
    HISTORY_TIME = '10:00'        # Saturday only
    
    # Timeouts (seconds)
    PRICE_TIMEOUT = 600
    INST_TIMEOUT = 600
    SIGNAL_TIMEOUT = 300
    HISTORY_TIMEOUT = 900
    
    PYTHON_PATH = sys.executable
```

### 3.2 Task Functions

```python
def update_daily_prices():
    """Update daily price data"""
    return run_command(
        [Config.PYTHON_PATH, '-c', script],
        'Daily price update',
        timeout=Config.PRICE_TIMEOUT
    )

def update_institutional_data():
    """Update institutional flow data"""
    return run_command(
        [Config.PYTHON_PATH, '-c', script],
        'Institutional data update',
        timeout=Config.INST_TIMEOUT
    )

def run_vcp_signal_scan():
    """Run VCP signal scan"""
    return run_command(
        [Config.PYTHON_PATH, '-m', 'kr_market.signal_tracker'],
        'VCP signal scan',
        timeout=Config.SIGNAL_TIMEOUT
    )

def generate_daily_report():
    """Generate daily report JSON"""
    # Reads signals_log.csv
    # Outputs daily_report.json
```

### 3.3 Scheduler Class

```python
class Scheduler:
    """Main scheduler class"""
    
    def __init__(self):
        self.running = True
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def setup_schedules(self):
        """Register schedules"""
        weekdays = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']
        
        for day in weekdays:
            getattr(schedule.every(), day).at(Config.PRICE_UPDATE_TIME).do(update_daily_prices)
            getattr(schedule.every(), day).at(Config.INST_UPDATE_TIME).do(update_institutional_data)
            getattr(schedule.every(), day).at(Config.SIGNAL_SCAN_TIME).do(run_vcp_signal_scan)
            getattr(schedule.every(), day).at(Config.REPORT_TIME).do(generate_daily_report)
        
        # Saturday history collection
        schedule.every().saturday.at(Config.HISTORY_TIME).do(collect_historical_institutional)
    
    def run(self):
        """Run scheduler loop"""
        while self.running:
            schedule.run_pending()
            time.sleep(30)
```

### 3.4 CLI Usage

```bash
# Run scheduler daemon
python kr_market/scheduler.py

# Run full update immediately
python kr_market/scheduler.py --now

# Run specific tasks
python kr_market/scheduler.py --prices
python kr_market/scheduler.py --inst
python kr_market/scheduler.py --signals
```

---

## 4. all_institutional_trend_data.py (1,041 lines)

Scrapes foreign and institutional investor data from Naver Finance.

### 4.1 Data Classes

```python
@dataclass
class TrendConfig:
    """Trend analysis thresholds"""
    strong_buy_inst: int = 3_000_000      # Institutional strong buy threshold
    buy_inst: int = 1_000_000             
    strong_buy_foreign: int = 5_000_000   # Foreign strong buy threshold
    buy_foreign: int = 2_000_000
    high_ratio_inst: float = 8.0          # High ratio threshold
    high_ratio_foreign: float = 12.0

@dataclass
class InstitutionalData:
    """Complete institutional data structure"""
    ticker: str
    scrape_date: str
    data_source: str
    total_days: int
    
    # Net buy amounts by period
    institutional_net_buy_60d: int = 0
    institutional_net_buy_20d: int = 0
    institutional_net_buy_10d: int = 0
    institutional_net_buy_5d: int = 0
    
    foreign_net_buy_60d: int = 0
    foreign_net_buy_20d: int = 0
    foreign_net_buy_10d: int = 0
    foreign_net_buy_5d: int = 0
    
    # Volume ratios
    institutional_ratio_20d: float = 0.0
    foreign_ratio_20d: float = 0.0
    
    # Trend analysis
    institutional_trend: str = 'neutral'
    foreign_trend: str = 'neutral'
    supply_demand_index: float = 50.0
    supply_demand_stage: str = '중립'
    
    # Accumulation signals
    strong_accumulation: int = 0
    accumulation_signal: int = 0
    accumulation_intensity: str = '보통'
```

### 4.2 Main Analyzer Class

```python
class EnhancedKoreanInstitutionalTrendAnalyzer:
    """Enhanced institutional trend analyzer"""
    
    def __init__(self, data_dir: str = None):
        self.data_dir = Path(data_dir or os.getenv('DATA_DIR', '.'))
        self.all_institutional_csv_path = self.data_dir / 'all_institutional_trend_data.csv'
        self.base_url = "https://finance.naver.com/item/frgn.naver"
        
        # Session settings
        self.session = requests.Session()
        self.request_delay = 0.3
        self.max_retries = 3
    
    def scrape_naver_institutional_trend_data(self, ticker: str) -> Optional[InstitutionalData]:
        """Scrape 60-day institutional data from Naver"""
        url = f"{self.base_url}?code={ticker}"
        # Parse HTML table
        # Extract: date, close_price, volume, institutional_net_buy, foreign_net_buy
        # Return analyzed InstitutionalData
    
    def download_all_institutional_data(self, max_stocks: int = None, max_workers: int = 5):
        """Download institutional data for all stocks (multithreaded)"""
        # Uses concurrent.futures.ThreadPoolExecutor
        # Saves to all_institutional_trend_data.csv
```

### 4.3 Supply Demand Index Calculation

```python
def _calculate_enhanced_supply_demand_index(self, metrics: Dict) -> float:
    """Calculate supply demand index (0-100)"""
    
    # Institutional score (0-50)
    inst_score = self._calculate_investor_score(
        metrics['institutional_net_buy_60d'],
        metrics['institutional_net_buy_20d'],
        metrics['institutional_net_buy_5d'],
        metrics['institutional_ratio_20d'],
        'institutional'
    )
    
    # Foreign score (0-50)
    foreign_score = self._calculate_investor_score(...)
    
    # Volume weight
    volume_weight = min(metrics['total_volume_20d'] / 10_000_000, 1.0)
    
    final_score = (inst_score + foreign_score) * (0.8 + 0.2 * volume_weight)
    return min(max(final_score, 0), 100)
```

### 4.4 Supply Demand Stages

| Score Range | Stage | Korean |
|:---|:---|:---|
| 85-100 | Strong Accumulation | 강한매집 |
| 70-84 | Accumulation | 매집 |
| 60-69 | Weak Accumulation | 약매집 |
| 40-59 | Neutral | 중립 |
| 30-39 | Weak Distribution | 약분산 |
| 15-29 | Distribution | 분산 |
| 0-14 | Strong Distribution | 강한분산 |

### 4.5 Output File

| Column | Description |
|:---|:---|
| `ticker` | 6-digit stock code |
| `institutional_net_buy_5d` | 5-day institutional net buy |
| `foreign_net_buy_5d` | 5-day foreign net buy |
| `supply_demand_index` | Combined score (0-100) |
| `supply_demand_stage` | Korean stage label |
| `accumulation_signal` | 1 if accumulation detected |
| `strong_accumulation` | 1 if strong accumulation |

---

## 5. Integration with Signal Tracker

`signal_tracker.py` loads `all_institutional_trend_data.csv` to filter stocks:

```python
def scan_today_signals(self) -> pd.DataFrame:
    # Load institutional data
    inst_path = os.path.join(self.data_dir, 'all_institutional_trend_data.csv')
    df = pd.read_csv(inst_path, encoding='utf-8-sig')
    
    # Filter: Foreign buy + Supply demand index
    signals = df[
        (df['foreign_net_buy_5d'] >= self.strategy_params['foreign_min']) &
        (df['supply_demand_index'] >= 60)
    ].copy()
```

---

## 6. Deployment

### 6.1 macOS launchd

Create `~/Library/LaunchAgents/com.krmarket.scheduler.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.krmarket.scheduler</string>
    <key>ProgramArguments</key>
    <array>
        <string>/path/to/.venv/bin/python</string>
        <string>/path/to/kr_market/scheduler.py</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>WorkingDirectory</key>
    <string>/path/to/project</string>
    <key>StandardOutPath</key>
    <string>/path/to/logs/scheduler.out.log</string>
    <key>StandardErrorPath</key>
    <string>/path/to/logs/scheduler.err.log</string>
</dict>
</plist>
```

```bash
# Load
launchctl load ~/Library/LaunchAgents/com.krmarket.scheduler.plist

# Unload
launchctl unload ~/Library/LaunchAgents/com.krmarket.scheduler.plist
```

### 6.2 Linux systemd

Create `/etc/systemd/system/kr-market-scheduler.service`:

```ini
[Unit]
Description=KR Market Scheduler
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/project
ExecStart=/path/to/.venv/bin/python kr_market/scheduler.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable kr-market-scheduler
sudo systemctl start kr-market-scheduler
```

---

## Next Steps

This completes the supporting modules documentation. For the full system:
- See **[BLUEPRINT_01_OVERVIEW.md](./BLUEPRINT_01_OVERVIEW.md)** for system overview
- See **[BLUEPRINT_05_BACKEND_DATA_SIGNALS.md](./BLUEPRINT_05_BACKEND_DATA_SIGNALS.md)** for `signal_tracker.py`
