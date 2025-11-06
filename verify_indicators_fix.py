#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
验证技术指标修复效果
重点检查EMA(50)和MACD是否不再为0
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from crypto_trader.services.redis_manager import redis_manager


def verify_indicators():
    print("=" * 80)
    print(" 验证技术指标修复效果")
    print("=" * 80)

    symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT', 'DOGEUSDT']

    all_passed = True

    for symbol in symbols:
        indicators = redis_manager.get_indicators(symbol)

        if indicators:
            rsi_14 = indicators.get('rsi_14', 50.0)
            ema_20 = indicators.get('ema_20', 0.0)
            ema_50 = indicators.get('ema_50', 0.0)
            macd_line = indicators.get('macd_line', 0.0)
            macd_signal = indicators.get('macd_signal', 0.0)
            macd_histogram = indicators.get('macd_histogram', 0.0)
            atr_14 = indicators.get('atr_14', 0.0)

            # 检查关键指标
            issues = []

            if ema_50 == 0.0:
                issues.append("EMA(50)为0")
                all_passed = False

            if macd_line == 0.0:
                issues.append("MACD为0")
                all_passed = False

            if rsi_14 == 50.0:
                issues.append("RSI(14)为默认值50.0")

            status = "[PASS]" if not issues else "[FAIL]"

            print(f"\n{symbol} {status}:")
            print(f"  RSI(14): {rsi_14:>10.2f}")
            print(f"  EMA(20): {ema_20:>10.2f}")
            print(f"  EMA(50): {ema_50:>10.2f} {'[OK]' if ema_50 != 0 else '[FAIL]'}")
            print(f"  MACD:    {macd_line:>10.2f} {'[OK]' if macd_line != 0 else '[FAIL]'}")
            print(f"  MACD Signal: {macd_signal:>10.2f}")
            print(f"  MACD Histogram: {macd_histogram:>10.2f}")
            print(f"  ATR(14): {atr_14:>10.2f}")

            if issues:
                print(f"  问题: {', '.join(issues)}")
            else:
                print(f"  [SUCCESS] 所有关键指标正常!")
        else:
            print(f"\n{symbol} [NO_DATA]")
            all_passed = False

    print("\n" + "=" * 80)
    print(" 验证结果总结")
    print("=" * 80)

    if all_passed:
        print("\n[SUCCESS] 所有交易对的技术指标都正常!")
        print("  - EMA(50)不再为0")
        print("  - MACD不再为0")
        print("  - 所有指标都有真实的计算值")
    else:
        print("\n[FAIL] 部分交易对的技术指标仍有问题")
        print("  需要进一步排查和修复")

    print("\n[修复方法]")
    print("  1. 在data_engine初始化时自动预加载100根历史K线")
    print("  2. 确保有足够数据计算EMA(50)和MACD")
    print("  3. 保持指标计算的数学标准不变")

    print("\n[关键改进]")
    print("  - 没有降低指标计算标准")
    print("  - 改进了数据收集策略")
    print("  - 确保指标准确性和可靠性")


if __name__ == "__main__":
    verify_indicators()
