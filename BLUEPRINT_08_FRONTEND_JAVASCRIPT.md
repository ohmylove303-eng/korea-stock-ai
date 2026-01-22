# KR Market AI Stock Analysis System - Blueprint Part 8: Frontend JavaScript

> **Version**: 1.0  
> **Last Updated**: 2026-01-04  
> **Location**: `templates/dashboard.html` (lines 655-5924)

---

## 1. Core Functions Overview

| Function | Purpose |
|:---|:---|
| `fetchKrSignalsForDashboard()` | KR 시그널 테이블 로드 |
| `loadKrAiAnalysis()` | GPT/Gemini 추천 로드 및 렌더링 |
| `loadKrStockChart()` | LightweightCharts 차트 렌더링 |
| `updateMarketGate()` | Market Gate 게이지 업데이트 |
| `switchMarketTab()` | 탭 전환 로직 |

---

## 2. KR Signal Fetching

```javascript
// --- Global Variables ---
let priceUpdateInterval;
let currentChartTicker = null;
let selectedDate = null;
let krAiAnalysisData = null;
let currentKrChartPick = null;

// --- KR Market Signal Fetching ---
async function fetchKrSignalsForDashboard() {
    const countEl = document.getElementById('kr-dash-count');
    const tableBody = document.getElementById('kr-dashboard-signal-list');
    const lastUpdatedEl = document.getElementById('kr-dash-last-updated');
    const refreshIcon = document.getElementById('kr-dash-refresh-icon');

    if (refreshIcon) refreshIcon.classList.add('animate-spin');

    try {
        const response = await fetch('/api/kr/signals');
        const data = await response.json();

        if (data.error) {
            if (tableBody) tableBody.innerHTML = `<tr><td colspan="7" class="p-6 text-center text-red-400">${data.error}</td></tr>`;
            return;
        }

        // Update KR Market Gate
        updateMarketGate('kr');

        const signals = data.signals || [];
        if (countEl) countEl.textContent = signals.length;
        if (lastUpdatedEl) lastUpdatedEl.textContent = new Date().toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' });

        if (tableBody) {
            if (signals.length === 0) {
                tableBody.innerHTML = '<tr><td colspan="7" class="p-6 text-center text-gray-500">오늘 시그널이 없습니다.</td></tr>';
            } else {
                tableBody.innerHTML = signals.map((sig, idx) => `
                    <tr class="hover:bg-white/5 transition-colors cursor-pointer" 
                        onclick="loadKrStockChart(${JSON.stringify(sig).replace(/"/g, '&quot;')}, ${idx})"
                        style="animation: fadeIn 0.3s ease ${idx * 0.05}s both;"
                        data-kr-idx="${idx}">
                        <td class="p-3">
                            <div class="flex items-center gap-2">
                                <span class="text-white font-bold">${sig.ticker}</span>
                                ${sig.market ? `<span class="px-1.5 py-0.5 rounded text-[9px] font-bold ${sig.market === 'KOSPI' ? 'bg-blue-500/20 text-blue-400' : 'bg-pink-500/20 text-pink-400'}">${sig.market}</span>` : ''}
                            </div>
                            <span class="text-xs text-gray-500">${sig.name || ''}</span>
                        </td>
                        <td class="p-3 text-gray-400 text-xs">${sig.signal_date || '-'}</td>
                        <td class="p-3 text-right font-mono text-xs ${sig.foreign_5d > 0 ? 'text-green-400' : 'text-red-400'}">${sig.foreign_5d ? sig.foreign_5d.toLocaleString() : '-'}</td>
                        <td class="p-3 text-right font-mono text-xs ${sig.inst_5d > 0 ? 'text-green-400' : 'text-red-400'}">${sig.inst_5d ? sig.inst_5d.toLocaleString() : '-'}</td>
                        <td class="p-3 text-center"><span class="px-2 py-0.5 rounded-full text-xs font-bold bg-blue-500/20 text-blue-400 border border-blue-500/30">${sig.score || '-'}</span></td>
                        <td class="p-3 text-center font-mono text-xs ${sig.contraction_ratio && sig.contraction_ratio <= 0.6 ? 'text-emerald-400' : 'text-purple-400'}">${sig.contraction_ratio ? sig.contraction_ratio.toFixed(2) : '-'}</td>
                        <td class="p-3 text-right font-mono text-xs text-gray-400">₩${sig.entry_price ? sig.entry_price.toLocaleString() : '-'}</td>
                        <td class="p-3 text-right font-mono text-xs text-white">₩${sig.current_price ? sig.current_price.toLocaleString() : '-'}</td>
                        <td class="p-3 text-right font-mono text-xs font-bold ${sig.return_pct >= 0 ? 'text-green-400' : 'text-red-400'}">${sig.return_pct !== undefined ? (sig.return_pct >= 0 ? '+' : '') + sig.return_pct.toFixed(1) + '%' : '-'}</td>
                        <td class="p-3 text-center" id="gpt-${sig.ticker}"><span class="text-gray-500 text-[10px]"><i class="fas fa-spinner fa-spin"></i></span></td>
                        <td class="p-3 text-center" id="gemini-${sig.ticker}"><span class="text-gray-500 text-[10px]"><i class="fas fa-spinner fa-spin"></i></span></td>
                    </tr>
                `).join('');

                // AI 분석 로드 (비동기)
                loadKrAiAnalysis();
            }
        }
    } catch (err) {
        console.error('KR signals fetch error:', err);
        if (tableBody) tableBody.innerHTML = '<tr><td colspan="11" class="p-6 text-center text-red-400">시그널 로딩 실패</td></tr>';
    } finally {
        if (refreshIcon) refreshIcon.classList.remove('animate-spin');
    }
}
```

---

## 3. AI Analysis Loading

```javascript
// Load KR AI Analysis (GPT + Gemini recommendations)
async function loadKrAiAnalysis() {
    try {
        const res = await fetch('/api/kr/ai-analysis');
        const data = await res.json();

        if (data.error) {
            console.log('AI Analysis error:', data.error);
            return;
        }

        krAiAnalysisData = data;

        // Update AI Summary section status
        const summaryEl = document.getElementById('kr-ai-summary');
        if (summaryEl && summaryEl.innerHTML.includes('AI 분석 준비 중')) {
            summaryEl.innerHTML = '<div class="text-emerald-400"><i class="fas fa-check-circle mr-2"></i> AI 분석 완료! 종목을 클릭하세요.</div>';
        }

        // Update Overview if stock is already selected
        if (currentKrChartPick) {
            loadKrAISummary(currentKrChartPick.ticker);
        }

        const signals = data.signals || [];

        // Helper: action to badge
        function actionBadge(rec) {
            if (!rec || !rec.action) return '<span class="text-gray-500 text-[10px]">-</span>';

            const action = rec.action.toUpperCase();
            let bgClass, textClass, icon;

            if (action === 'BUY') {
                bgClass = 'bg-green-500/20';
                textClass = 'text-green-400';
                icon = '▲';
            } else if (action === 'SELL') {
                bgClass = 'bg-red-500/20';
                textClass = 'text-red-400';
                icon = '▼';
            } else {
                bgClass = 'bg-yellow-500/20';
                textClass = 'text-yellow-400';
                icon = '■';
            }

            const label = action === 'BUY' ? '매수' : action === 'SELL' ? '매도' : '관망';
            const tooltip = rec.reason || '';

            return `<span class="px-1.5 py-0.5 rounded text-[9px] font-bold ${bgClass} ${textClass} border border-current/30 cursor-help" title="${tooltip}">${icon} ${label}</span>`;
        }

        // Update each cell
        signals.forEach(sig => {
            const gptCell = document.getElementById(`gpt-${sig.ticker}`);
            const geminiCell = document.getElementById(`gemini-${sig.ticker}`);

            if (gptCell) gptCell.innerHTML = actionBadge(sig.gpt_recommendation);
            if (geminiCell) geminiCell.innerHTML = actionBadge(sig.gemini_recommendation);
        });

    } catch (e) {
        console.log('KR AI Analysis load failed:', e);
    }
}
```

---

## 4. Stock Chart (LightweightCharts)

```javascript
let krChart = null;
let krCandleSeries = null;
let krVolumeSeries = null;
let krChartPeriod = '1y';

async function loadKrStockChart(sig, idx) {
    currentKrChartPick = sig;
    const ticker = sig.ticker;
    const name = sig.name || ticker;

    // Update header
    document.getElementById('kr-chart-ticker').textContent = `${name} (${ticker})`;
    document.getElementById('kr-chart-info').textContent = sig.market || '';

    // Highlight selected row
    document.querySelectorAll('#kr-dashboard-signal-list tr').forEach((row, i) => {
        row.classList.toggle('bg-white/10', i === idx);
    });

    // Load AI summary
    loadKrAISummary(ticker);

    // Create/update chart
    const container = document.getElementById('kr-stock-chart');
    container.innerHTML = '<div class="text-gray-500 text-xs"><i class="fas fa-spinner fa-spin mr-1"></i> 차트 로딩중...</div>';

    try {
        const res = await fetch(`/api/kr/stock-chart/${ticker}?period=${krChartPeriod}`);
        const data = await res.json();

        if (data.error || !data.candles || data.candles.length === 0) {
            container.innerHTML = '<div class="text-red-400 text-xs">차트 데이터 없음</div>';
            return;
        }

        container.innerHTML = '';

        // Create chart
        krChart = LightweightCharts.createChart(container, {
            width: container.clientWidth,
            height: 300,
            layout: {
                background: { type: 'solid', color: '#1c1c1e' },
                textColor: '#9ca3af',
            },
            grid: {
                vertLines: { color: 'rgba(255, 255, 255, 0.05)' },
                horzLines: { color: 'rgba(255, 255, 255, 0.05)' },
            },
            crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
            rightPriceScale: { borderColor: 'rgba(255, 255, 255, 0.1)' },
            timeScale: { borderColor: 'rgba(255, 255, 255, 0.1)', timeVisible: true },
        });

        // Candlestick series
        krCandleSeries = krChart.addCandlestickSeries({
            upColor: '#30d158',
            downColor: '#ff453a',
            borderDownColor: '#ff453a',
            borderUpColor: '#30d158',
            wickDownColor: '#ff453a',
            wickUpColor: '#30d158',
        });

        const candleData = data.candles.map(c => ({
            time: c.date,
            open: c.open,
            high: c.high,
            low: c.low,
            close: c.close,
        }));

        krCandleSeries.setData(candleData);
        krChart.timeScale().fitContent();

        // Update VCP info
        if (sig.contraction_ratio) {
            document.getElementById('kr-vcp-ratio').textContent = sig.contraction_ratio.toFixed(2);
        }

    } catch (e) {
        console.error('Chart load error:', e);
        container.innerHTML = '<div class="text-red-400 text-xs">차트 로드 실패</div>';
    }
}

function changeKrChartPeriod(period) {
    krChartPeriod = period;

    // Update button styles
    document.querySelectorAll('#kr-chart-period-btns button').forEach(btn => {
        if (btn.dataset.period === period) {
            btn.classList.add('bg-rose-600', 'text-white');
            btn.classList.remove('text-gray-400');
        } else {
            btn.classList.remove('bg-rose-600', 'text-white');
            btn.classList.add('text-gray-400');
        }
    });

    // Reload chart if a stock is selected
    if (currentKrChartPick) {
        loadKrStockChart(currentKrChartPick, 0);
    }
}
```

---

## 5. Market Gate Update

```javascript
async function updateMarketGate(market) {
    try {
        const res = await fetch(`/api/${market}/market-gate`);
        const data = await res.json();

        if (data.error) {
            console.log(`${market} gate error:`, data.error);
            return;
        }

        const score = data.score || 50;
        const gate = data.gate || 'YELLOW';

        // Update gauge (KR example)
        if (market === 'kr') {
            const progressEl = document.getElementById('kr-gate-progress');
            const scoreEl = document.getElementById('kr-gate-score-val');
            const labelEl = document.getElementById('kr-gate-label');

            if (progressEl) {
                // Calculate stroke-dashoffset (364.4 is full circle)
                const offset = 364.4 - (364.4 * score / 100);
                progressEl.style.strokeDashoffset = offset;
            }

            if (scoreEl) scoreEl.textContent = score;

            if (labelEl) {
                let labelText = 'Neutral';
                let labelClass = 'text-yellow-400 border-yellow-500/30 bg-yellow-500/10';

                if (gate === 'GREEN') {
                    labelText = 'Bullish';
                    labelClass = 'text-green-400 border-green-500/30 bg-green-500/10';
                } else if (gate === 'RED') {
                    labelText = 'Bearish';
                    labelClass = 'text-red-400 border-red-500/30 bg-red-500/10';
                }

                labelEl.textContent = labelText;
                labelEl.className = `mt-4 px-4 py-1 rounded-full border text-xs font-bold ${labelClass}`;
            }

            // Also update sector grid if available
            if (data.sectors) {
                updateKrSectorGrid(data.sectors);
            }
        }

        // Update Summary page gates
        updateSummaryGate(market, score, gate);

    } catch (e) {
        console.error(`${market} gate update failed:`, e);
    }
}

function updateSummaryGate(market, score, gate) {
    const scoreEl = document.getElementById(`summary-${market}-score`);
    const labelEl = document.getElementById(`summary-${market}-label`);

    if (scoreEl) scoreEl.textContent = score;

    if (labelEl) {
        let labelText = 'Neutral';
        let labelClass = 'text-yellow-400 border-yellow-500/30 bg-yellow-500/10';

        if (gate === 'GREEN') {
            labelText = 'Bullish';
            labelClass = 'text-green-400 border-green-500/30 bg-green-500/10';
        } else if (gate === 'RED') {
            labelText = 'Bearish';
            labelClass = 'text-red-400 border-red-500/30 bg-red-500/10';
        }

        labelEl.textContent = labelText;
        labelEl.className = `px-3 py-1 rounded-full text-[10px] font-bold border ${labelClass}`;
    }
}
```

---

## 6. Tab Navigation

```javascript
function switchMarketTab(element, tabName) {
    // Hide all content sections
    const contentSections = [
        'content-summary', 'content-kr-market', 'content-crypto',
        'content-us-market', 'content-economic-calendar', 'content-dividend', 'content-analysis'
    ];
    contentSections.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.classList.add('hidden');
    });

    // Show selected content
    let contentId = '';
    if (tabName.includes('Summary')) contentId = 'content-summary';
    else if (tabName.includes('KR')) contentId = 'content-kr-market';
    else if (tabName.includes('Crypto')) contentId = 'content-crypto';
    else if (tabName.includes('US')) contentId = 'content-us-market';
    else if (tabName.includes('Calendar')) contentId = 'content-economic-calendar';
    else if (tabName.includes('Dividend')) contentId = 'content-dividend';

    const targetEl = document.getElementById(contentId);
    if (targetEl) targetEl.classList.remove('hidden');

    // Update header
    document.getElementById('main-header-title').textContent = tabName;

    // Highlight active nav
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('bg-white/5', 'text-white', 'border-white/5');
        item.classList.add('text-gray-400', 'border-transparent');
    });
    if (element) {
        element.classList.add('bg-white/5', 'text-white', 'border-white/5');
        element.classList.remove('text-gray-400', 'border-transparent');
    }

    // Load data based on tab
    if (tabName.includes('KR')) {
        fetchKrSignalsForDashboard();
    } else if (tabName.includes('Summary')) {
        loadSummaryData();
    } else if (tabName.includes('Crypto')) {
        loadCryptoData();
    } else if (tabName.includes('US')) {
        loadUSMarketData();
    }
}

function toggleSidebar() {
    const sidebar = document.getElementById('main-sidebar');
    const brandText = document.getElementById('brand-text');
    const navTexts = document.querySelectorAll('.nav-text');

    sidebar.classList.toggle('w-64');
    sidebar.classList.toggle('w-16');

    if (sidebar.classList.contains('w-16')) {
        // Collapsed
        if (brandText) brandText.classList.add('hidden');
        navTexts.forEach(el => el.classList.add('hidden'));
    } else {
        // Expanded
        if (brandText) brandText.classList.remove('hidden');
        navTexts.forEach(el => el.classList.remove('hidden'));
    }
}
```

---

## 7. Initialization

```javascript
// --- Page Load ---
document.addEventListener('DOMContentLoaded', function() {
    // Load Summary tab by default
    const summaryNav = document.querySelector('.nav-item.active');
    if (summaryNav) {
        switchMarketTab(summaryNav, 'Portfolio Summary');
    }
});

// Resize handler for charts
window.addEventListener('resize', function() {
    if (krChart) {
        const container = document.getElementById('kr-stock-chart');
        krChart.resize(container.clientWidth, 300);
    }
});

// CSS Animation for fade-in
const style = document.createElement('style');
style.textContent = `
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
`;
document.head.appendChild(style);
```

---

## 8. Helper Functions

### 8.1 Number Formatting

```javascript
function formatNumber(num, precision = 2) {
    if (num === null || num === undefined) return '-';
    return num.toLocaleString('ko-KR', { maximumFractionDigits: precision });
}

function formatPercent(num, showSign = true) {
    if (num === null || num === undefined) return '-';
    const sign = showSign && num >= 0 ? '+' : '';
    return `${sign}${num.toFixed(2)}%`;
}

function formatCurrency(num, symbol = '₩') {
    if (num === null || num === undefined) return '-';
    return `${symbol}${num.toLocaleString()}`;
}
```

### 8.2 Color Helpers

```javascript
function getReturnColor(returnPct) {
    if (returnPct >= 0) return 'text-green-400';
    return 'text-red-400';
}

function getGateColor(gate) {
    if (gate === 'GREEN') return 'text-green-400';
    if (gate === 'RED') return 'text-red-400';
    return 'text-yellow-400';
}
```

---

## Next Steps

This completes the frontend documentation. For full source code, refer to:
- `templates/dashboard.html` (lines 655-5924)
- Continue to **[BLUEPRINT_07_FRONTEND_PARTIALS.md](./BLUEPRINT_07_FRONTEND_PARTIALS.md)** for HTML partials.
