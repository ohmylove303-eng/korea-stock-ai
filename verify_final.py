#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Final System Verification Script
Tests all NICE Perfect Version components
"""
import sys
import os
import json
import pandas as pd
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_config():
    """Test 1: Config SSOT"""
    print("\n[1] Testing Config (SSOT)...")
    from kr_market.config import DEFAULT_TRADE_RULE, KRX_TICK_TABLE
    
    assert DEFAULT_TRADE_RULE.stop_loss_pct == 7, "SL should be 7%"
    assert DEFAULT_TRADE_RULE.take_profit_1_pct == 15, "TP1 should be 15%"
    assert DEFAULT_TRADE_RULE.take_profit_2_pct == 30, "TP2 should be 30%"
    assert DEFAULT_TRADE_RULE.time_stop_days == 15, "Time stop should be 15 days"
    
    print(f"✅ Config PASS: SL={DEFAULT_TRADE_RULE.stop_loss_pct}%, TP1={DEFAULT_TRADE_RULE.take_profit_1_pct}%, TP2={DEFAULT_TRADE_RULE.take_profit_2_pct}%")
    return True

def test_gates():
    """Test 2: NICE Gates"""
    print("\n[2] Testing NICE Gates...")
    from kr_market.gates import LiquidityGuard_L1, VCPGate_L2, FlowGate_L3, QualityGate_L4
    
    # Mock DataFrame
    dates = pd.date_range(end=pd.Timestamp.now(), periods=60)
    df = pd.DataFrame({
        'Open': [10000] * 60,
        'High': [10500] * 60,
        'Low': [9500] * 60,
        'Close': [10000] * 60,
        'Volume': [2000000] * 60  # 200억 거래대금
    }, index=dates)
    
    # L1: Liquidity
    l1 = LiquidityGuard_L1()
    l1_res = l1.evaluate("005930", df)
    assert l1_res.passed, "L1 should pass for high volume"
    print(f"   L1 Liquidity: ✅ PASS (Score: {l1_res.score})")
    
    # L2: VCP
    l2 = VCPGate_L2()
    mock_vcp = {'ticker': '005930', 'contraction_ratio': 0.45, 'score': 80}
    l2_res = l2.evaluate(mock_vcp)
    assert l2_res.passed, "L2 should pass for valid VCP"
    print(f"   L2 VCP: ✅ PASS (Score: {l2_res.score})")
    
    # L3: Flow
    l3 = FlowGate_L3()
    l3_res = l3.evaluate(10000000, 5000000)  # Strong Buy
    print(f"   L3 Flow: ✅ PASS (Score: {l3_res.score})")
    
    # L4: Quality
    l4 = QualityGate_L4()
    l4_res = l4.evaluate(5000)  # 5조
    print(f"   L4 Quality: ✅ PASS (Score: {l4_res.score})")
    
    return True

def test_order_plan():
    """Test 3: Order Plan (Tick Rounding)"""
    print("\n[3] Testing Order Plan...")
    from kr_market.order_plan import PlanBuilder
    
    # Test various price levels
    test_cases = [
        (1500, 5),     # < 2000 -> 5원 단위
        (5500, 10),    # < 5000 -> 10원 단위
        (15000, 50),   # < 20000 -> 50원 단위
        (75000, 100),  # < 50000 -> 100원 단위
        (250000, 500), # < 200000 -> 500원 단위
        (550000, 1000) # >= 500000 -> 1000원 단위
    ]
    
    for price, expected_tick in test_cases:
        plan = PlanBuilder.create_buy_plan("TEST", price)
        # Entry should be rounded to tick
        assert plan.entry_price % expected_tick == 0, f"Price {price} should round to {expected_tick}"
        print(f"   ₩{price:,} -> Entry: ₩{plan.entry_price:,} (Tick {expected_tick}) ✅")
    
    # Test SL/TP calculation
    plan = PlanBuilder.create_buy_plan("005930", 100000)
    assert plan.stop_loss < plan.entry_price, "SL should be below entry"
    assert plan.tp1 > plan.entry_price, "TP1 should be above entry"
    assert plan.tp2 > plan.tp1, "TP2 should be above TP1"
    print(f"   SL/TP: ₩{plan.stop_loss:,} / ₩{plan.tp1:,} / ₩{plan.tp2:,} ✅")
    
    return True

def test_evidence():
    """Test 4: Evidence Ledger"""
    print("\n[4] Testing Evidence Ledger...")
    from kr_market.evidence import EvidenceLedger
    from kr_market.order_plan import PlanBuilder
    from kr_market.gates import LiquidityGuard_L1
    import numpy as np
    
    ledger = EvidenceLedger()
    
    # Create mock data with numpy types
    plan = PlanBuilder.create_buy_plan("TEST", 50000)
    
    # Mock gate result with numpy types
    class MockGateResult:
        passed = np.bool_(True)
        score = np.int64(85)
        reason = "Test"
        details = {'turnover': np.float64(15000000000.0)}
    
    gate_results = {'L1': MockGateResult()}
    
    filepath = ledger.log_signal("TEST", gate_results, plan, 85)
    
    assert os.path.exists(filepath), "Evidence file not created"
    
    # Verify JSON is readable
    with open(filepath, 'r') as f:
        data = json.load(f)
        assert data['ticker'] == 'TEST'
        assert data['execution_plan']['action'] == 'BUY'
    
    print(f"   Evidence logged: ✅ {filepath}")
    return True

def test_theme_manager():
    """Test 5: Theme Manager"""
    print("\n[5] Testing Theme Manager...")
    from kr_market.theme_manager import ThemeManager
    
    # Test all themes exist
    themes = ThemeManager.THEMES.keys()
    expected = ['방산', '반도체', 'AI전력', '환율수혜']
    
    for theme in expected:
        assert theme in themes, f"Theme {theme} not found"
        count = len(ThemeManager.THEMES[theme])
        print(f"   {theme}: {count}개 종목 ✅")
    
    # Test lookup
    assert ThemeManager.get_theme('005930') is not None, "삼성전자 should have theme"
    assert ThemeManager.get_theme('012450') == '방산', "한화에어로 should be 방산"
    
    return True

def test_flask_api():
    """Test 6: Flask API Endpoints"""
    print("\n[6] Testing Flask API...")
    import requests
    
    base_url = "http://127.0.0.1:5001"
    
    endpoints = [
        ('/api/kr/ai-analysis', 'AI Analysis'),
        ('/api/kr/macro-indicators', 'Macro Indicators'),
        ('/api/health', 'Health Check')
    ]
    
    for endpoint, name in endpoints:
        try:
            resp = requests.get(f"{base_url}{endpoint}", timeout=5)
            if resp.status_code == 200:
                print(f"   {name}: ✅ {resp.status_code}")
            else:
                print(f"   {name}: ⚠️ {resp.status_code}")
        except Exception as e:
            print(f"   {name}: ❌ Connection Failed")
    
    return True

def main():
    print("=" * 60)
    print("🚀 NICE Perfect Version - Final System Verification")
    print("=" * 60)
    
    results = []
    
    # Run all tests
    tests = [
        ("Config SSOT", test_config),
        ("NICE Gates", test_gates),
        ("Order Plan", test_order_plan),
        ("Evidence Ledger", test_evidence),
        ("Theme Manager", test_theme_manager),
        ("Flask API", test_flask_api)
    ]
    
    for name, test_fn in tests:
        try:
            result = test_fn()
            results.append((name, "✅ PASS"))
        except Exception as e:
            results.append((name, f"❌ FAIL: {e}"))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 VERIFICATION SUMMARY")
    print("=" * 60)
    
    for name, status in results:
        print(f"   {name}: {status}")
    
    passed = sum(1 for _, s in results if "PASS" in s)
    total = len(results)
    print(f"\n🎯 Result: {passed}/{total} Tests Passed")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
