# KR Market AI Stock Analysis System - Blueprint Part 6: Frontend (HTML/CSS/JS)

> **Version**: 1.0  
> **Last Updated**: 2026-01-03  
> **File**: `templates/dashboard.html` (5,924 lines)

---

## 1. Overview

The frontend is a **single-page application** built with:
- **TailwindCSS** for utility-first styling
- **Vanilla JavaScript** for API interactions
- **Chart.js / ApexCharts / LightweightCharts** for data visualization
- **Font Awesome** for icons
- **Marked.js** for markdown rendering

### 1.1 Page Structure

```
dashboard.html
├── <head>
│   ├── TailwindCSS CDN
│   ├── Chart libraries (Chart.js, ApexCharts, LightweightCharts)
│   ├── Custom CSS variables (Apple Dark Mode)
│   └── Font Awesome icons
├── <body>
│   ├── Sidebar Navigation (apple-glass)
│   ├── Main Content Area
│   │   ├── Top Bar (search, notifications)
│   │   ├── Content Sections
│   │   │   ├── content-summary (Portfolio Summary)
│   │   │   ├── content-kr-market (Korean Market)
│   │   │   ├── content-crypto (Cryptocurrency)
│   │   │   ├── content-us-market (US Market)
│   │   │   └── content-economic-calendar
│   │   └── Modals
│   └── <script> (JavaScript logic)
└── Jinja2 Includes
    ├── partials/_summary.html
    ├── partials/_kr_market.html
    ├── partials/_crypto.html
    └── partials/_us_market.html
```

---

## 2. Design System (CSS Variables)

### 2.1 Apple Dark Mode Color Palette

```css
:root {
    /* Apple Dark Mode Palette */
    --bg-page: #000000;              /* True Black */
    --bg-surface: #1c1c1e;           /* System Gray 6 (Dark) */
    --bg-surface-hover: #2c2c2e;     /* System Gray 5 (Dark) */
    --bg-glass: rgba(28, 28, 30, 0.75);

    --border-color: rgba(255, 255, 255, 0.1);

    /* Text Colors */
    --text-primary: #f5f5f7;         /* Label Color (Primary) */
    --text-secondary: #86868b;       /* Label Color (Secondary) */
    --text-tertiary: #6e6e73;        /* Label Color (Tertiary) */

    /* Accents (Apple Human Interface Guidelines) */
    --accent: #2997ff;               /* System Blue */
    --status-success: #30d158;       /* System Green */
    --status-error: #ff453a;         /* System Red */
    --status-warning: #ff9f0a;       /* System Orange */
}
```

### 2.2 Typography

```css
body {
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", "Inter", sans-serif;
    background-color: var(--bg-page);
    color: var(--text-primary);
    font-size: 14px;
    line-height: 1.6;
    -webkit-font-smoothing: antialiased;
}
```

### 2.3 Glassmorphism Effect

```css
.apple-glass {
    background-color: rgba(28, 28, 30, 0.65);
    backdrop-filter: blur(20px) saturate(180%);
    -webkit-backdrop-filter: blur(20px) saturate(180%);
    border-right: 1px solid rgba(255, 255, 255, 0.08);
}
```

---

## 3. Key CSS Components

### 3.1 Modern Card Styling

```css
.bg-\[\#1a1a1a\] {
    background-color: var(--bg-surface) !important;
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 18px;                /* Classic Apple curvature */
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    transition: transform 0.2s ease, background-color 0.2s ease;
}

.bg-\[\#1a1a1a\]:hover {
    background-color: var(--bg-surface-hover) !important;
    transform: scale(1.005);            /* Subtle scale */
}
```

### 3.2 Premium AI Recommendation Badges

```css
.badge-premium {
    padding: 4px 12px;
    border-radius: 99px;
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    backdrop-filter: blur(8px);
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
    border: 1px solid rgba(255, 255, 255, 0.1);
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.badge-strong-buy {
    background: linear-gradient(135deg, rgba(16, 185, 129, 0.2), rgba(5, 150, 105, 0.4));
    color: #34d399;
    animation: pulse-glow 2s infinite;
}

.badge-buy {
    background: linear-gradient(135deg, rgba(37, 99, 235, 0.2), rgba(29, 78, 216, 0.4));
    color: #60a5fa;
}

.badge-neutral {
    background: linear-gradient(135deg, rgba(75, 85, 99, 0.2), rgba(55, 65, 81, 0.4));
    color: #9ca3af;
}
```

### 3.3 Pulse Glow Animation

```css
@keyframes pulse-glow {
    0% { box-shadow: 0 0 10px rgba(16, 185, 129, 0.1); }
    50% { box-shadow: 0 0 25px rgba(16, 185, 129, 0.3); }
    100% { box-shadow: 0 0 10px rgba(16, 185, 129, 0.1); }
}
```

---

## 4. Navigation Structure

### 4.1 Sidebar HTML

```html
<aside class="w-64 lg:w-56 apple-glass flex flex-col h-full shrink-0 transition-all z-50">
    <!-- Logo -->
    <div class="h-16 flex items-center gap-3 px-4 border-b border-[#27272a]">
        <i class="fas fa-chart-line text-2xl text-blue-500"></i>
        <span class="font-black text-xl text-white tracking-tight">Quantix</span>
    </div>
    
    <!-- Navigation Links -->
    <nav class="flex-1 py-4 px-3 space-y-1 overflow-y-auto">
        <a href="#" onclick="switchMarketTab(this, 'Summary')" class="nav-item...">
            <i class="fas fa-th-large"></i>
            <span>Summary</span>
        </a>
        <a href="#" onclick="switchMarketTab(this, 'KR Market')" class="nav-item...">
            <i class="fab fa-bitcoin"></i>
            <span>KR Market</span>
        </a>
        <!-- More nav items -->
    </nav>
    
    <!-- Profile -->
    <div class="p-4 border-t border-[#27272a]">
        <div class="flex items-center gap-3">
            <div class="w-8 h-8 rounded-full bg-gradient-to-tr from-indigo-500 to-purple-500"></div>
            <span class="text-xs font-bold text-white">Pro User</span>
        </div>
    </div>
</aside>
```

### 4.2 Tab Switching JavaScript

```javascript
function switchMarketTab(element, tabName) {
    // Hide all content sections
    const contentSections = [
        'content-summary', 'content-kr-market', 'content-crypto',
        'content-us-market', 'content-economic-calendar', 'content-dividend'
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
    // etc.
    
    const targetEl = document.getElementById(contentId);
    if (targetEl) targetEl.classList.remove('hidden');
    
    // Update header
    document.getElementById('main-header-title').textContent = tabName;
    
    // Highlight active nav
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('bg-white/10', 'text-white');
        item.classList.add('text-gray-400');
    });
    element.classList.add('bg-white/10', 'text-white');
    element.classList.remove('text-gray-400');
    
    // Load data based on tab
    if (tabName.includes('KR')) loadKrAiAnalysis();
    // etc.
}
```

---

## 5. KR Market Section

### 5.1 Load AI Analysis Function

```javascript
async function loadKrAiAnalysis() {
    const tableBody = document.getElementById('kr-dashboard-signal-list');
    const summaryEl = document.getElementById('kr-ai-summary');
    const indicesContainer = document.getElementById('kr-market-indices-container');
    
    // Show loading state
    tableBody.innerHTML = `
        <tr><td colspan="11" class="p-6 text-center text-gray-500">
            <i class="fas fa-spinner fa-spin mr-2"></i> AI 분석 로드 중...
        </td></tr>
    `;
    
    try {
        const res = await fetch('/api/kr/ai-analysis');
        const data = await res.json();
        
        if (data.error) {
            tableBody.innerHTML = `<tr><td colspan="11" class="p-6 text-center text-red-400">${data.error}</td></tr>`;
            return;
        }
        
        // Store data globally for click handling
        window.krAiData = data;
        
        // Render signals table
        const signals = data.signals || [];
        tableBody.innerHTML = signals.map((sig, idx) => {
            const gpt = sig.gpt_recommendation || {};
            const gemini = sig.gemini_recommendation || {};
            const returnPct = sig.return_pct || 0;
            
            return `
                <tr class="hover:bg-white/5 cursor-pointer" onclick="showKrAiDetail(${idx})">
                    <td class="p-3">
                        <span class="text-white font-bold">${sig.ticker}</span>
                        <span class="text-xs text-gray-500">${sig.name}</span>
                    </td>
                    <td class="p-3 text-center">${actionBadge(gpt)}</td>
                    <td class="p-3 text-center">${actionBadge(gemini)}</td>
                    <td class="p-3 text-right ${returnPct >= 0 ? 'text-green-400' : 'text-red-400'}">
                        ${returnPct >= 0 ? '+' : ''}${returnPct.toFixed(2)}%
                    </td>
                    <!-- More columns -->
                </tr>
            `;
        }).join('');
        
        // Render market indices
        if (data.market_indices) {
            renderMarketIndices(data.market_indices);
        }
        
    } catch (e) {
        console.error('KR AI Analysis load failed:', e);
    }
}
```

### 5.2 Action Badge Helper

```javascript
function actionBadge(rec) {
    if (!rec || !rec.action) return '<span class="text-gray-500">-</span>';
    
    const action = rec.action.toUpperCase();
    let bgClass, textClass, icon, label;
    
    if (action === 'BUY') {
        bgClass = 'bg-green-500/20';
        textClass = 'text-green-400';
        icon = '▲';
        label = '매수';
    } else if (action === 'SELL') {
        bgClass = 'bg-red-500/20';
        textClass = 'text-red-400';
        icon = '▼';
        label = '매도';
    } else {
        bgClass = 'bg-yellow-500/20';
        textClass = 'text-yellow-400';
        icon = '■';
        label = '관망';
    }
    
    return `
        <span class="px-1.5 py-0.5 rounded text-[9px] font-bold 
                     ${bgClass} ${textClass} border border-current/30">
            ${icon} ${label}
        </span>
    `;
}
```

### 5.3 Show AI Detail Modal

```javascript
function showKrAiDetail(idx) {
    const data = window.krAiData;
    if (!data || !data.signals || !data.signals[idx]) return;
    
    const sig = data.signals[idx];
    const gpt = sig.gpt_recommendation || {};
    const gemini = sig.gemini_recommendation || {};
    const news = sig.news || [];
    
    // Populate modal content
    document.getElementById('kr-ai-detail-title').innerHTML = `
        <span class="text-white">${sig.name}</span>
        <span class="text-gray-500 text-sm">(${sig.ticker})</span>
    `;
    
    document.getElementById('kr-ai-detail-body').innerHTML = `
        <div class="grid grid-cols-2 gap-4">
            <div class="bg-[#1a1a1a] rounded-lg p-4">
                <h4 class="text-sm font-bold text-green-400 mb-2">🤖 GPT-5.2</h4>
                <div class="text-xs">${actionBadge(gpt)} (${gpt.confidence || 0}%)</div>
                <p class="text-xs text-gray-400 mt-2">${gpt.reason || '-'}</p>
            </div>
            <div class="bg-[#1a1a1a] rounded-lg p-4">
                <h4 class="text-sm font-bold text-blue-400 mb-2">✨ Gemini 3.0</h4>
                <div class="text-xs">${actionBadge(gemini)} (${gemini.confidence || 0}%)</div>
                <p class="text-xs text-gray-400 mt-2">${gemini.reason || '-'}</p>
            </div>
        </div>
        
        <div class="mt-4">
            <h4 class="text-sm font-bold text-gray-300 mb-2">📰 관련 뉴스</h4>
            ${news.length > 0 ? news.map(n => `
                <div class="bg-[#1a1a1a] rounded-lg p-3 mb-2">
                    <a href="${n.url}" target="_blank" class="text-xs text-blue-400 hover:underline">
                        ${n.title}
                    </a>
                    <p class="text-xs text-gray-500 mt-1">${n.summary || ''}</p>
                </div>
            `).join('') : '<p class="text-xs text-gray-500">뉴스 없음</p>'}
        </div>
    `;
    
    // Show modal
    document.getElementById('kr-ai-detail-modal').classList.remove('hidden');
}
```

---

## 6. Chart Integration

### 6.1 Price Chart with LightweightCharts

```javascript
async function loadKrStockChart(ticker) {
    const chartContainer = document.getElementById('kr-chart-container');
    chartContainer.innerHTML = '';
    
    const chart = LightweightCharts.createChart(chartContainer, {
        width: chartContainer.clientWidth,
        height: 400,
        layout: {
            background: { type: 'solid', color: '#1a1a1a' },
            textColor: '#9ca3af',
        },
        grid: {
            vertLines: { color: 'rgba(255, 255, 255, 0.05)' },
            horzLines: { color: 'rgba(255, 255, 255, 0.05)' },
        },
        crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
        rightPriceScale: { borderColor: 'rgba(255, 255, 255, 0.1)' },
        timeScale: { borderColor: 'rgba(255, 255, 255, 0.1)' },
    });
    
    const candlestickSeries = chart.addCandlestickSeries({
        upColor: '#30d158',
        downColor: '#ff453a',
        borderDownColor: '#ff453a',
        borderUpColor: '#30d158',
        wickDownColor: '#ff453a',
        wickUpColor: '#30d158',
    });
    
    try {
        const res = await fetch(`/api/kr/stock-chart/${ticker}`);
        const data = await res.json();
        
        if (data.candles) {
            candlestickSeries.setData(data.candles.map(c => ({
                time: c.date,
                open: c.open,
                high: c.high,
                low: c.low,
                close: c.close,
            })));
        }
    } catch (e) {
        console.error('Chart load failed:', e);
    }
}
```

---

## 7. Responsive Design

### 7.1 Sidebar Collapse (Mobile)

```javascript
function toggleSidebar() {
    const sidebar = document.querySelector('aside');
    sidebar.classList.toggle('w-16');
    sidebar.classList.toggle('w-64');
    
    // Hide text labels when collapsed
    const navTexts = sidebar.querySelectorAll('.nav-text');
    navTexts.forEach(el => el.classList.toggle('hidden'));
}
```

### 7.2 TailwindCSS Breakpoints

```html
<!-- Responsive grid -->
<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
    <!-- Cards -->
</div>

<!-- Hide on mobile -->
<span class="hidden sm:inline-block">CMD+K</span>
```

---

## 8. Jinja2 Template Includes

```html
<!-- In dashboard.html -->
{% include 'partials/_summary.html' %}
{% include 'partials/_kr_market.html' %}
{% include 'partials/_crypto.html' %}
{% include 'partials/_us_market.html' %}
```

Each partial contains:
- HTML structure for that section
- Inline `<style>` if needed
- Inline `<script>` for section-specific logic

---

## 9. External Libraries

```html
<head>
    <!-- TailwindCSS -->
    <script src="https://cdn.tailwindcss.com"></script>
    
    <!-- Charts -->
    <script src="https://unpkg.com/lightweight-charts@3.8.0/dist/lightweight-charts.standalone.production.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/apexcharts"></script>
    
    <!-- Utilities -->
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
</head>
```

---

## Next Steps

This completes the frontend documentation. For the full source code, refer to:
- `templates/dashboard.html` (5,924 lines)
- `templates/partials/_kr_market.html`
- `templates/partials/_summary.html`

---

## Appendix: Quick Reference

### API Calls Used in Frontend

| Endpoint | Description |
|:---|:---|
| `/api/kr/ai-analysis` | KR AI recommendations |
| `/api/kr/ai-analysis?refresh=true` | Force refresh |
| `/api/kr/ai-history-dates` | Get history dates |
| `/api/kr/ai-history/<date>` | Get historical data |
| `/api/kr/stock-chart/<ticker>` | Get price chart |
| `/api/kr/market-gate` | Get market status |
