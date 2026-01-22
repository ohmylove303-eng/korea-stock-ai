# KR Market AI Stock Analysis System - Blueprint Part 7: Frontend Partials

> **Version**: 1.0  
> **Last Updated**: 2026-01-04  
> **Files**: `templates/partials/*.html` (5 files, ~100KB total)

---

## 1. Partials Overview

| File | Lines | Description |
|:---|---:|:---|
| `_summary.html` | 242 | Portfolio Summary 탭 |
| `_kr_market.html` | 265 | KR Market 탭 (VCP, AI 분석) |
| `_crypto.html` | ~280 | Crypto Market 탭 |
| `_us_market.html` | ~580 | US Market 탭 |
| `_dividend.html` | ~500 | Dividend Optimizer |

---

## 2. _summary.html (Portfolio Summary)

```html
<!-- Summary Content (Avant-Garde / Ultrathink Design) -->
<div id="content-summary">
    <!-- Header Section -->
    <div class="mb-8">
        <div
            class="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-purple-500/20 bg-purple-500/5 text-xs text-purple-400 font-medium mb-4">
            <span class="w-1.5 h-1.5 rounded-full bg-purple-500 animate-ping"></span>
            Portfolio Alpha v3.0
        </div>
        <h2 class="text-4xl md:text-5xl font-bold tracking-tighter text-white leading-tight mb-2">
            Investment <span
                class="text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-indigo-400">Intelligence</span>
        </h2>
        <p class="text-gray-400 text-lg">전체 시장 현황 및 포트폴리오 성과 요약</p>
    </div>

    <!-- Hero Card: US/KR Portfolio Performance Side by Side -->
    <section class="mb-8">
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <!-- US Total Return Alpha -->
            <div class="relative overflow-hidden group">
                <div
                    class="absolute inset-0 bg-gradient-to-br from-purple-600/20 via-indigo-600/10 to-transparent blur-3xl rounded-3xl -z-10 group-hover:from-purple-600/30 transition-all duration-700">
                </div>
                <div
                    class="bg-[#1c1c1e]/80 backdrop-blur-xl rounded-3xl p-6 border border-white/10 relative overflow-hidden h-full">
                    <div class="flex items-center justify-between mb-4">
                        <div>
                            <h3 class="text-sm font-bold text-purple-400 uppercase tracking-widest mb-1">🇺🇸 US Alpha
                            </h3>
                            <p class="text-xs text-gray-400">$1,000 per stock</p>
                        </div>
                        <div class="text-right">
                            <p class="text-xs text-mono text-purple-400 font-bold" id="summary-generated-at">Loading...
                            </p>
                        </div>
                    </div>
                    <div class="flex flex-col items-center md:items-start py-2">
                        <h1 class="text-5xl md:text-6xl font-black text-white tracking-tighter mb-2"
                            id="summary-total-return">--%</h1>
                        <div class="flex items-center gap-3 justify-center md:justify-start">
                            <p class="text-gray-400 font-mono text-sm" id="summary-value-change">$-- → $--</p>
                        </div>
                    </div>
                </div>
            </div>

            <!-- KR VCP Cumulative Return -->
            <div class="relative overflow-hidden group">
                <div
                    class="absolute inset-0 bg-gradient-to-br from-rose-600/20 via-amber-600/10 to-transparent blur-3xl rounded-3xl -z-10 group-hover:from-rose-600/30 transition-all duration-700">
                </div>
                <div
                    class="bg-[#1c1c1e]/80 backdrop-blur-xl rounded-3xl p-6 border border-white/10 relative overflow-hidden h-full">
                    <div class="flex items-center justify-between mb-4">
                        <div>
                            <h3 class="text-sm font-bold text-rose-400 uppercase tracking-widest mb-1">🇰🇷 KR VCP Alpha
                            </h3>
                            <p class="text-xs text-gray-400">₩1,000,000 per stock</p>
                        </div>
                        <div class="text-right">
                            <p class="text-xs text-mono text-rose-400 font-bold" id="kr-summary-generated-at">Loading...
                            </p>
                        </div>
                    </div>
                    <div class="flex flex-col items-center md:items-start py-2">
                        <h1 class="text-5xl md:text-6xl font-black text-white tracking-tighter mb-2"
                            id="kr-summary-total-return">--%</h1>
                        <div class="flex items-center gap-3 justify-center md:justify-start">
                            <p class="text-gray-400 font-mono text-sm" id="kr-summary-value-change">₩-- → ₩--</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </section>

    <!-- Market Gate Summary Section (Grid style) -->
    <section class="mb-8">
        <div class="flex items-center justify-between mb-4">
            <h3 class="text-sm font-bold text-gray-400 uppercase tracking-widest flex items-center gap-2">
                Market Health Index
            </h3>
        </div>
        <div id="summary-gate-container" class="grid grid-cols-1 md:grid-cols-3 gap-4">
            <!-- US Gate Card -->
            <div
                class="p-6 rounded-2xl bg-[#1c1c1e] border border-white/10 hover:border-blue-500/30 transition-all duration-300 relative overflow-hidden group">
                <div
                    class="absolute top-0 right-0 p-4 opacity-5 group-hover:opacity-10 transition-opacity text-blue-500">
                    <i class="fas fa-flag-usa text-3xl"></i>
                </div>
                <div class="text-[10px] font-bold text-gray-500 uppercase tracking-widest mb-3">US Market Gate</div>
                <div class="flex items-center justify-between">
                    <div>
                        <p id="summary-us-score" class="text-4xl font-black text-white">--</p>
                        <p class="text-[9px] text-gray-500 mt-1 uppercase">Score (0-100)</p>
                    </div>
                    <div class="flex flex-col items-end gap-2">
                        <span id="summary-us-label"
                            class="px-3 py-1 rounded-full text-[10px] font-bold bg-white/5 border border-white/10">-</span>
                    </div>
                </div>
            </div>

            <!-- KR Gate Card -->
            <div
                class="p-6 rounded-2xl bg-[#1c1c1e] border border-white/10 hover:border-rose-500/30 transition-all duration-300 relative overflow-hidden group">
                <div
                    class="absolute top-0 right-0 p-4 opacity-5 group-hover:opacity-10 transition-opacity text-rose-500">
                    <i class="fas fa-chart-line text-3xl"></i>
                </div>
                <div class="text-[10px] font-bold text-gray-500 uppercase tracking-widest mb-3">KR Market Gate</div>
                <div class="flex items-center justify-between">
                    <div>
                        <p id="summary-kr-score" class="text-4xl font-black text-white">--</p>
                        <p class="text-[9px] text-gray-500 mt-1 uppercase">Score (0-100)</p>
                    </div>
                    <div class="flex flex-col items-end gap-2">
                        <span id="summary-kr-label"
                            class="px-3 py-1 rounded-full text-[10px] font-bold bg-white/5 border border-white/10">-</span>
                    </div>
                </div>
            </div>

            <!-- Crypto Gate Card -->
            <div
                class="p-6 rounded-2xl bg-[#1c1c1e] border border-white/10 hover:border-amber-500/30 transition-all duration-300 relative overflow-hidden group">
                <div
                    class="absolute top-0 right-0 p-4 opacity-5 group-hover:opacity-10 transition-opacity text-amber-500">
                    <i class="fab fa-bitcoin text-3xl"></i>
                </div>
                <div class="text-[10px] font-bold text-gray-500 uppercase tracking-widest mb-3">Crypto Market Gate</div>
                <div class="flex items-center justify-between">
                    <div>
                        <p id="summary-crypto-score" class="text-4xl font-black text-white">--</p>
                        <p class="text-[9px] text-gray-500 mt-1 uppercase">Score (0-100)</p>
                    </div>
                    <div class="flex flex-col items-end gap-2">
                        <span id="summary-crypto-label"
                            class="px-3 py-1 rounded-full text-[10px] font-bold bg-white/5 border border-white/10">-</span>
                    </div>
                </div>
            </div>
        </div>
    </section>

    <!-- Portfolio Performance Section -->
    <section class="mb-8">
        <div class="flex items-center justify-between mb-4">
            <h3 class="text-sm font-bold text-gray-400 uppercase tracking-widest flex items-center gap-2">
                Portfolio Performance Tracker
            </h3>
        </div>

        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <!-- US Portfolio Card -->
            <div class="rounded-2xl bg-[#1c1c1e] border border-white/10 overflow-hidden">
                <div
                    class="p-4 border-b border-white/5 flex justify-between items-center bg-gradient-to-r from-blue-600/10 to-transparent">
                    <h4 class="text-base font-bold text-white flex items-center gap-2">
                        <span class="w-1 h-5 bg-blue-500 rounded-full"></span>
                        🇺🇸 US Market
                    </h4>
                    <span class="text-[10px] text-blue-400 font-mono uppercase" id="us-perf-updated">Loading...</span>
                </div>
                <div class="p-5">
                    <div class="grid grid-cols-3 gap-4 mb-4">
                        <div class="text-center">
                            <p class="text-3xl font-black text-green-400" id="us-perf-winrate">--%</p>
                            <p class="text-[10px] text-gray-500 uppercase">Win Rate</p>
                        </div>
                        <div class="text-center">
                            <p class="text-3xl font-black text-white" id="us-perf-return">--%</p>
                            <p class="text-[10px] text-gray-500 uppercase">Avg Return</p>
                        </div>
                        <div class="text-center">
                            <p class="text-3xl font-black text-blue-400" id="us-perf-picks">--</p>
                            <p class="text-[10px] text-gray-500 uppercase">Total Picks</p>
                        </div>
                    </div>
                    <div class="border-t border-white/5 pt-3">
                        <p class="text-[10px] text-gray-500 mb-2 uppercase">Recent Picks</p>
                        <div id="us-perf-table" class="space-y-2 max-h-48 overflow-y-auto">
                            <p class="text-gray-500 text-xs">Loading...</p>
                        </div>
                    </div>
                </div>
            </div>

            <!-- KR Portfolio Card -->
            <div class="rounded-2xl bg-[#1c1c1e] border border-white/10 overflow-hidden">
                <div
                    class="p-4 border-b border-white/5 flex justify-between items-center bg-gradient-to-r from-rose-600/10 to-transparent">
                    <h4 class="text-base font-bold text-white flex items-center gap-2">
                        <span class="w-1 h-5 bg-rose-500 rounded-full"></span>
                        🇰🇷 KR Market
                    </h4>
                    <span class="text-[10px] text-rose-400 font-mono uppercase" id="kr-perf-updated">Loading...</span>
                </div>
                <div class="p-5">
                    <div class="grid grid-cols-3 gap-4 mb-4">
                        <div class="text-center">
                            <p class="text-3xl font-black text-green-400" id="kr-perf-winrate">--%</p>
                            <p class="text-[10px] text-gray-500 uppercase">Win Rate</p>
                        </div>
                        <div class="text-center">
                            <p class="text-3xl font-black text-white" id="kr-perf-return">--%</p>
                            <p class="text-[10px] text-gray-500 uppercase">Avg Return</p>
                        </div>
                        <div class="text-center">
                            <p class="text-3xl font-black text-rose-400" id="kr-perf-picks">--</p>
                            <p class="text-[10px] text-gray-500 uppercase">Total Picks</p>
                        </div>
                    </div>
                    <div class="border-t border-white/5 pt-3">
                        <p class="text-[10px] text-gray-500 mb-2 uppercase">Recent Picks</p>
                        <div id="kr-perf-table" class="space-y-2 max-h-48 overflow-y-auto">
                            <p class="text-gray-500 text-xs">Loading...</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </section>

</div>
```

---

## 3. _kr_market.html (KR Market Tab)

```html
<!-- KR Market Content (Avant-Garde / Ultrathink Design) -->
<div id="content-kr-market" class="hidden">
    <!-- Header Section -->
    <div class="mb-8">
        <div
            class="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-rose-500/20 bg-rose-500/5 text-xs text-rose-400 font-medium mb-4">
            <span class="w-1.5 h-1.5 rounded-full bg-rose-500 animate-ping"></span>
            KR Market Alpha
        </div>
        <h2 class="text-4xl md:text-5xl font-bold tracking-tighter text-white leading-tight mb-2">
            Smart Money <span
                class="text-transparent bg-clip-text bg-gradient-to-r from-rose-400 to-amber-400">Footprints</span>
        </h2>
        <p class="text-gray-400 text-lg">VCP 패턴 & 기관/외국인 수급 추적</p>
    </div>

    <!-- Market Gate Analysis Section -->
    <section class="mb-8">
        <div class="grid grid-cols-1 lg:grid-cols-4 gap-4">
            <!-- Main Gate Card (KOSPI) -->
            <div
                class="lg:col-span-1 p-6 rounded-2xl bg-[#1c1c1e] border border-white/10 relative overflow-hidden group">
                <div
                    class="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity text-rose-500">
                    <i class="fas fa-chart-line text-4xl"></i>
                </div>
                <h3 class="text-sm font-bold text-gray-400 mb-4 flex items-center gap-2">
                    KR Market Gate
                    <span class="w-1.5 h-1.5 rounded-full bg-rose-500 animate-pulse"></span>
                </h3>
                <div class="flex flex-col items-center justify-center py-2">
                    <div id="kr-gate-gauge" class="relative w-32 h-32 flex items-center justify-center">
                        <svg class="w-full h-full -rotate-90">
                            <circle cx="64" cy="64" r="58" stroke="currentColor" stroke-width="8" fill="transparent"
                                class="text-white/5" />
                            <circle id="kr-gate-progress" cx="64" cy="64" r="58" stroke="currentColor" stroke-width="8"
                                fill="transparent" stroke-dasharray="364.4" stroke-dashoffset="364.4"
                                class="text-rose-500 transition-all duration-1000 ease-out" />
                        </svg>
                        <div class="absolute inset-0 flex flex-col items-center justify-center">
                            <span id="kr-gate-score-val" class="text-3xl font-black text-white">--</span>
                            <span class="text-[10px] text-gray-500 font-bold uppercase tracking-widest">Score</span>
                        </div>
                    </div>
                    <div id="kr-gate-label"
                        class="mt-4 px-4 py-1 rounded-full bg-white/5 border border-white/10 text-xs font-bold text-gray-400">
                        Analyzing...
                    </div>
                </div>
            </div>

            <!-- Sector Grid -->
            <div class="lg:col-span-3 p-6 rounded-2xl bg-[#1c1c1e] border border-white/10">
                <div class="flex items-center justify-between mb-4">
                    <h3 class="text-sm font-bold text-gray-400">KOSPI 200 Sector Index</h3>
                    <div class="flex items-center gap-4 text-[10px] font-bold text-gray-500 uppercase tracking-tighter">
                        <span class="flex items-center gap-1"><span class="w-2 h-2 rounded-full bg-green-500"></span>
                            Bullish</span>
                        <span class="flex items-center gap-1"><span class="w-2 h-2 rounded-full bg-yellow-500"></span>
                            Neutral</span>
                        <span class="flex items-center gap-1"><span class="w-2 h-2 rounded-full bg-red-500"></span>
                            Bearish</span>
                    </div>
                </div>
                <div id="kr-sector-grid" class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-4 gap-3">
                    <!-- Sector Cards will be injected by JS -->
                    <div class="h-16 rounded-xl bg-white/5 animate-pulse border border-white/5"></div>
                    <div class="h-16 rounded-xl bg-white/5 animate-pulse border border-white/5"></div>
                    <div class="h-16 rounded-xl bg-white/5 animate-pulse border border-white/5"></div>
                    <div class="h-16 rounded-xl bg-white/5 animate-pulse border border-white/5"></div>
                </div>
            </div>
        </div>
    </section>

    <!-- KPI Cards -->
    <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <!-- Card 1: Signal Count -->
        <div
            class="p-5 rounded-2xl bg-[#1c1c1e] border border-white/10 relative overflow-hidden group hover:border-rose-500/30 transition-all duration-300">
            <div
                class="absolute top-0 right-0 w-20 h-20 bg-rose-500/10 rounded-full blur-[25px] -translate-y-1/2 translate-x-1/2">
            </div>
            <div class="text-[10px] font-bold text-gray-500 uppercase tracking-widest mb-1">Today's Signals</div>
            <div class="text-3xl font-black text-white group-hover:text-rose-400 transition-colors" id="kr-dash-count">
                --</div>
            <div class="mt-2 text-xs text-gray-500">VCP + 외국인 순매수</div>
        </div>

        <!-- Card 2: Win Rate -->
        <div
            class="p-5 rounded-2xl bg-[#1c1c1e] border border-white/10 relative overflow-hidden group hover:border-amber-500/30 transition-all duration-300">
            <div
                class="absolute top-0 right-0 w-20 h-20 bg-amber-500/10 rounded-full blur-[25px] -translate-y-1/2 translate-x-1/2">
            </div>
            <div class="text-[10px] font-bold text-gray-500 uppercase tracking-widest mb-1">Backtest Win Rate</div>
            <div class="text-3xl font-black text-white group-hover:text-amber-400 transition-colors">66.7<span
                    class="text-base text-gray-600">%</span></div>
            <div class="mt-2 text-xs text-gray-500">60일 히스토리 기반</div>
        </div>

        <!-- Card 3: Profit Factor -->
        <div
            class="p-5 rounded-2xl bg-[#1c1c1e] border border-white/10 relative overflow-hidden group hover:border-emerald-500/30 transition-all duration-300">
            <div
                class="absolute top-0 right-0 w-20 h-20 bg-emerald-500/10 rounded-full blur-[25px] -translate-y-1/2 translate-x-1/2">
            </div>
            <div class="text-[10px] font-bold text-gray-500 uppercase tracking-widest mb-1">Profit Factor</div>
            <div class="text-3xl font-black text-white group-hover:text-emerald-400 transition-colors">3.38</div>
            <div class="mt-2 text-xs text-gray-500">Risk/Reward Ratio</div>
        </div>

        <!-- Card 4: Refresh Action -->
        <div class="p-5 rounded-2xl bg-[#1c1c1e] border border-white/10 flex flex-col justify-center items-center gap-2 cursor-pointer hover:bg-white/5 transition-all duration-300 group"
            onclick="fetchKrSignalsForDashboard()">
            <div
                class="w-10 h-10 rounded-full bg-[#27272a] flex items-center justify-center text-white group-hover:rotate-180 transition-transform duration-500">
                <i class="fas fa-sync-alt" id="kr-dash-refresh-icon"></i>
            </div>
            <div class="text-center">
                <div class="text-sm font-bold text-white">Update Signals</div>
                <div class="text-[10px] text-gray-500">Last: <span id="kr-dash-last-updated">-</span></div>
            </div>
        </div>
    </div>

    <!-- Market Indices Section -->
    <section class="mb-6">
        <div class="flex items-center justify-between mb-3">
            <h3 class="text-base font-bold text-white flex items-center gap-2">
                <span class="w-1 h-5 bg-rose-500 rounded-full"></span>
                Market Indices
            </h3>
            <span class="text-[10px] text-gray-500 font-mono uppercase tracking-wider">KOSPI / KOSDAQ</span>
        </div>
        <div id="kr-market-indices-container" class="grid grid-cols-2 md:grid-cols-2 gap-4">
            <!-- Populated by JS -->
            <div
                class="p-4 rounded-2xl bg-[#1c1c1e] border border-white/10 flex flex-col items-center justify-center h-20 animate-pulse">
                <div class="h-3 w-16 bg-white/5 rounded mb-2"></div>
                <div class="h-4 w-20 bg-white/5 rounded"></div>
            </div>
        </div>
    </section>

    <!-- Chart & AI Analysis Grid -->
    <section class="mb-6">
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <!-- Chart Container -->
            <div class="lg:col-span-2 rounded-2xl bg-[#1c1c1e] border border-white/10 p-5">
                <div class="flex items-center justify-between mb-4">
                    <div>
                        <h2 id="kr-chart-ticker" class="text-xl font-bold text-white">Select a stock</h2>
                        <span id="kr-chart-info" class="text-xs text-gray-500">표에서 종목을 클릭하세요</span>
                    </div>
                    <div class="flex items-center gap-3">
                        <div id="kr-chart-period-btns"
                            class="flex gap-1 bg-white/5 p-1 rounded-lg border border-white/10">
                            <button data-period="1mo" onclick="changeKrChartPeriod('1mo')"
                                class="px-2.5 py-1 text-xs rounded font-medium text-gray-400 hover:text-white hover:bg-white/10 transition-colors">1M</button>
                            <button data-period="3mo" onclick="changeKrChartPeriod('3mo')"
                                class="px-2.5 py-1 text-xs rounded font-medium text-gray-400 hover:text-white hover:bg-white/10 transition-colors">3M</button>
                            <button data-period="6mo" onclick="changeKrChartPeriod('6mo')"
                                class="px-2.5 py-1 text-xs rounded font-medium text-gray-400 hover:text-white hover:bg-white/10 transition-colors">6M</button>
                            <button data-period="1y" onclick="changeKrChartPeriod('1y')"
                                class="px-2.5 py-1 text-xs rounded font-medium bg-rose-600 text-white">1Y</button>
                        </div>
                    </div>
                </div>
                <div id="kr-stock-chart" class="h-[300px] flex items-center justify-center text-gray-600">
                    <i class="fas fa-chart-line text-4xl"></i>
                </div>
                <!-- VCP Pattern Visualization -->
                <div class="flex items-center justify-between mt-4 pt-4 border-t border-white/5">
                    <div class="flex items-center gap-2">
                        <span class="text-[10px] text-gray-500 uppercase tracking-wider font-bold">VCP 패턴:</span>
                        <button id="kr-toggle-vcp" onclick="toggleKrVcpVisualization()"
                            class="px-2.5 py-1 text-xs rounded-lg bg-rose-500/20 text-rose-400 transition-colors border border-rose-500/30 font-bold flex items-center gap-1">
                            📊 VCP 범위 표시
                        </button>
                    </div>
                    <div id="kr-vcp-info" class="flex items-center gap-3 text-[10px]">
                        <span class="text-gray-500">VCP Ratio: <span id="kr-vcp-ratio"
                                class="text-emerald-400 font-bold">-</span></span>
                        <span class="text-gray-500">전반부 범위: <span id="kr-vcp-range1"
                                class="text-purple-400 font-bold">-</span></span>
                        <span class="text-gray-500">후반부 범위: <span id="kr-vcp-range2"
                                class="text-cyan-400 font-bold">-</span></span>
                    </div>
                </div>
            </div>

            <!-- AI Summary Section -->
            <div class="rounded-2xl bg-gradient-to-r from-rose-900/20 to-amber-900/20 border border-rose-500/20 p-5">
                <div class="flex items-center justify-between mb-3">
                    <h3 class="text-sm font-bold text-rose-400 flex items-center gap-2">
                        <span class="text-lg">🤖</span>
                        <span>AI 상세 분석</span>
                    </h3>
                </div>
                <div id="kr-ai-summary"
                    class="text-sm text-gray-300 leading-relaxed overflow-y-auto max-h-[300px] custom-scrollbar">
                    <div class="text-gray-500"><i class="fas fa-spinner fa-spin mr-2"></i> AI 분석 준비 중... (Top 10 종목 분석
                        완료 시 즉시 표시됩니다)</div>
                </div>
            </div>
        </div>
    </section>

    <!-- Signal Grid -->
    <div class="rounded-2xl bg-[#1c1c1e] border border-white/10 overflow-hidden">
        <div class="p-4 border-b border-white/5 flex justify-between items-center bg-black/30">
            <h3 class="text-base font-bold text-white flex items-center gap-2">
                <span class="w-1 h-5 bg-rose-500 rounded-full"></span>
                <span id="kr-signals-title">Live VCP Signals</span>
            </h3>
            <!-- History Date Picker -->
            <div class="flex items-center gap-2">
                <button id="kr-signals-latest-btn" onclick="loadLatestKrSignals()"
                    class="px-2 py-1 text-[10px] font-bold rounded bg-rose-600 text-white hover:bg-rose-500 transition-colors">
                    최신
                </button>
                <div class="relative">
                    <button id="kr-signals-history-btn" onclick="toggleKrSignalsHistoryDropdown()"
                        class="px-2 py-1 text-[10px] font-bold rounded bg-white/10 text-gray-300 hover:bg-white/20 transition-colors flex items-center gap-1">
                        <i class="fas fa-calendar-alt"></i>
                        <span id="kr-signals-selected-date">과거</span>
                        <i class="fas fa-chevron-down text-[8px]"></i>
                    </button>
                    <div id="kr-signals-history-dropdown"
                        class="hidden absolute right-0 top-full mt-1 w-40 bg-[#1c1c1e] border border-white/10 rounded-lg shadow-xl z-50 max-h-48 overflow-y-auto custom-scrollbar">
                        <!-- Dates populated by JS -->
                    </div>
                </div>
            </div>
        </div>

        <div class="overflow-x-auto">
            <table class="w-full text-left">
                <thead>
                    <tr
                        class="text-[10px] text-gray-500 border-b border-white/5 uppercase tracking-wider bg-white/[0.02]">
                        <th class="p-3 font-semibold">Ticker</th>
                        <th class="p-3 font-semibold">Signal Date</th>
                        <th class="p-3 font-semibold text-right">외국인 (5D)</th>
                        <th class="p-3 font-semibold text-right">기관 (5D)</th>
                        <th class="p-3 font-semibold text-center">Score</th>
                        <th class="p-3 font-semibold text-center">VCP Ratio</th>
                        <th class="p-3 font-semibold text-right">Entry</th>
                        <th class="p-3 font-semibold text-right">Current</th>
                        <th class="p-3 font-semibold text-right">Return</th>
                        <th class="p-3 font-semibold text-center">🤖 GPT</th>
                        <th class="p-3 font-semibold text-center">♊ Gemini</th>
                    </tr>
                </thead>
                <tbody id="kr-dashboard-signal-list" class="divide-y divide-white/5 text-sm text-gray-300">
                    <tr>
                        <td colspan="11" class="p-6 text-center text-gray-500">
                            <i class="fas fa-spinner fa-spin mr-2"></i> 시그널 로딩 중...
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>
    </div>
</div>
```

---

## 4. Key Design Patterns

### 4.1 Header Section Pattern

```html
<div class="mb-8">
    <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-{color}-500/20 bg-{color}-500/5 text-xs text-{color}-400 font-medium mb-4">
        <span class="w-1.5 h-1.5 rounded-full bg-{color}-500 animate-ping"></span>
        {Badge Text}
    </div>
    <h2 class="text-4xl md:text-5xl font-bold tracking-tighter text-white leading-tight mb-2">
        {Title} <span class="text-transparent bg-clip-text bg-gradient-to-r from-{color1}-400 to-{color2}-400">{Highlighted}</span>
    </h2>
    <p class="text-gray-400 text-lg">{Subtitle}</p>
</div>
```

### 4.2 Card Pattern

```html
<div class="p-5 rounded-2xl bg-[#1c1c1e] border border-white/10 relative overflow-hidden group hover:border-{color}-500/30 transition-all duration-300">
    <div class="absolute top-0 right-0 w-20 h-20 bg-{color}-500/10 rounded-full blur-[25px] -translate-y-1/2 translate-x-1/2"></div>
    <div class="text-[10px] font-bold text-gray-500 uppercase tracking-widest mb-1">{Label}</div>
    <div class="text-3xl font-black text-white group-hover:text-{color}-400 transition-colors" id="{id}">{Value}</div>
    <div class="mt-2 text-xs text-gray-500">{Description}</div>
</div>
```

### 4.3 Gate Gauge Pattern

```html
<div id="{id}-gauge" class="relative w-32 h-32 flex items-center justify-center">
    <svg class="w-full h-full -rotate-90">
        <circle cx="64" cy="64" r="58" stroke="currentColor" stroke-width="8" fill="transparent" class="text-white/5" />
        <circle id="{id}-progress" cx="64" cy="64" r="58" stroke="currentColor" stroke-width="8"
            fill="transparent" stroke-dasharray="364.4" stroke-dashoffset="364.4"
            class="text-{color}-500 transition-all duration-1000 ease-out" />
    </svg>
    <div class="absolute inset-0 flex flex-col items-center justify-center">
        <span id="{id}-score-val" class="text-3xl font-black text-white">--</span>
        <span class="text-[10px] text-gray-500 font-bold uppercase tracking-widest">Score</span>
    </div>
</div>
```

---

## Next Steps

Continue to **[BLUEPRINT_08_FRONTEND_JAVASCRIPT.md](./BLUEPRINT_08_FRONTEND_JAVASCRIPT.md)** for JavaScript logic.
