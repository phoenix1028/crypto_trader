#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
重新分析EMA(50)和MACD为0的根本原因
不是降低标准，而是找到真正的问题
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from crypto_trader.services.redis_manager import redis_manager


def analyze_root_cause():
    print("=" * 80)
    print(" 重新分析EMA(50)和MACD为0的根本原因")
    print("=" * 80)

    # 1. 检查Redis中的真实情况
    print("\n[1] 检查当前Redis中的真实情况...")
    symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT', 'DOGEUSDT']

    for symbol in symbols:
        indicators = redis_manager.get_indicators(symbol)

        if indicators:
            ema_50 = indicators.get('ema_50', 0)
            macd_line = indicators.get('macd_line', 0)
            last_calc = indicators.get('last_calc', 'N/A')

            status = "[OK]" if ema_50 != 0 and macd_line != 0 else "[问题]"
            print(f"  {symbol}: {status}")
            print(f"    EMA(50): {ema_50}")
            print(f"    MACD: {macd_line}")
            print(f"    最后计算: {last_calc}")

            if ema_50 == 0:
                print(f"    [分析] EMA(50)为0是因为K线数据不足50根")
            if macd_line == 0:
                print(f"    [分析] MACD为0是因为K线数据不足26根")

    # 2. 分析真正的问题
    print("\n[2] 分析真正的问题...")

    print("\n  问题诊断:")
    print("    [正确] EMA(50)需要50根K线是合理的")
    print("    [正确] MACD需要26根K线是合理的")
    print("    [错误] 我之前的修复降低了标准，导致指标不准确")

    print("\n  真正的问题:")
    print("    1. K线数据收集不足")
    print("    2. 系统初始化时没有获取足够的初始K线数据")
    print("    3. WebSocket连接失败，无法持续接收新K线")

    # 3. 提供合理的解决方案
    print("\n[3] 提供合理的解决方案...")

    print("\n  方案A：改进K线数据收集")
    print("    - 系统启动时主动获取100根历史K线")
    print("    - 确保每个交易对都有足够的数据")
    print("    - 保持指标计算的标准不变")

    print("\n  方案B：渐进式指标计算")
    print("    - K线<14: 只计算RSI和ATR(7)")
    print("    - 14<=K线<26: 计算RSI、ATR(14)、部分MACD")
    print("    - 26<=K线<50: 计算RSI、ATR(14)、MACD、EMA(20)")
    print("    - K线>=50: 计算完整的指标")
    print("    - 标记指标的可信度")

    print("\n  方案C：明确的数据不足处理")
    print("    - 当K线不足时，指标字段设为None或特定标记")
    print("    - AI根据标记判断是否使用该指标")
    print("    - 提供数据充足的预计时间")

    # 4. 重新审视技术标准
    print("\n[4] 重新审视技术标准...")

    print("\n  合理的最小K线数量:")
    print("    RSI(7):  8根K线")
    print("    RSI(14): 15根K线")
    print("    EMA(20): 20根K线")
    print("    ATR(14): 15根K线")
    print("    MACD(12,26,9): 35根K线")
    print("    EMA(50): 50根K线")

    print("\n  我之前的错误:")
    print("    [错误] 降低EMA(50)到2根K线")
    print("    [错误] 降低MACD到2根K线")
    print("    [后果] 指标将不准确，可能误导AI决策")

    # 5. 建议的修复方案
    print("\n[5] 建议的修复方案...")

    print("\n  正确的方法:")
    print("    1. 保持指标计算的数学标准不变")
    print("    2. 改进数据收集，确保系统有足够K线")
    print("    3. 在数据不足时，使用None标记而不是0")
    print("    4. AI需要检查数据质量，根据可用指标做决策")

    # 6. 检查data_engine的K线收集逻辑
    print("\n[6] 检查data_engine的K线收集逻辑...")

    from crypto_trader.core.data_engine import DataEngine
    data_engine = DataEngine()

    print(f"\n  data_engine.klines_cache当前状态:")
    for symbol in symbols:
        cached_count = len(data_engine.klines_cache.get(symbol, []))
        print(f"    {symbol}: {cached_count} 根K线")

        if cached_count < 50:
            print(f"      [问题] K线数据不足，无法计算完整指标")

    # 7. 结论
    print("\n" + "=" * 80)
    print(" 结论和建议")
    print("=" * 80)

    print("\n  [我之前修复的错误]")
    print("    - 盲目降低了EMA和MACD的K线要求")
    print("    - 这会导致指标不准确")
    print("    - 可能误导AI做出错误决策")

    print("\n  [正确的做法]")
    print("    1. 保持数学标准：EMA(50)需要50根K线")
    print("    2. 改进数据收集：确保有足够K线")
    print("    3. 数据不足时返回None而不是0")
    print("    4. AI需要数据质量检查")

    print("\n  [用户问题的答案]")
    print("    - EMA(50)为0是因为K线数据不足50根")
    print("    - MACD为0是因为K线数据不足26根")
    print("    - 不是指标本身的问题，是数据收集的问题")
    print("    - 解决方案应该是改进数据收集，不是降低标准")


if __name__ == "__main__":
    analyze_root_cause()
