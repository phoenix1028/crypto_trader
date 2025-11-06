#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
切换到合约（期货）交易模式
AI交易工具应该使用合约数据，而不是现货数据
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


def switch_to_futures_config():
    print("=" * 80)
    print(" 重要配置修正：切换到合约（期货）交易模式")
    print("=" * 80)

    print("\n[问题识别]")
    print("  ❌ 当前配置使用现货(SPOT)数据")
    print("  ❌ AI交易工具应该使用合约(FUTURES)数据")
    print("  ❌ 现货不适合杠杆交易和自动化策略")

    print("\n[为什么需要合约数据]")
    print("  1. 合约支持杠杆交易（AI策略的关键特性）")
    print("  2. 合约有强制平仓机制（风险管理）")
    print("  3. 合约流动性更好（适合高频交易）")
    print("  4. 合约适合量化交易和AI策略")
    print("  5. 现货主要用于长期持有，不适合工具化交易")

    print("\n[需要修改的配置]")

    print("\n1. data_engine.py:")
    print("   修改前：")
    print("     client = Client(api_key, api_secret, testnet=True)")
    print("     klines = client.get_klines(symbol, interval, limit)")
    print()
    print("   修改后：")
    print("     client = Client(api_key, api_secret, testnet=True)")
    print("     # 使用期货API端点")
    print("     from binance.futures import FuturesClient")
    print("     futures_client = FuturesClient(api_key, api_secret, testnet=True)")
    print("     klines = futures_client.klines(symbol, interval, limit)")

    print("\n2. WebSocket订阅：")
    print("   修改前：")
    print("     stream = 'btcusdt@kline_1m'  # 现货流")
    print()
    print("   修改后：")
    print("     stream = 'btcusdt@kline_1m'  # 合约流（同一符号，不同端点）")

    print("\n3. API端点：")
    print("   现货: https://api.binance.com/api/v3")
    print("   合约: https://testnet.binancefuture.com  # 期货测试网")
    print("   合约: https://fapi.binance.com/fapi/v1  # 期货主网")

    print("\n4. 交易对符号：")
    print("   现货: BTCUSDT, ETHUSDT")
    print("   合约: BTCUSDT, ETHUSDT (相同符号，不同数据源)")

    print("\n[合约专用配置]")

    print("\n1. 杠杆设置：")
    print("   - 可以配置1x-125x杠杆")
    print("   - AI策略通常使用10x-20x杠杆")
    print("   - 需要风险管理设置")

    print("\n2. 合约类型：")
    print("   - USDT-Margined Contracts (USDT保证金)")
    print("   - COIN-Margined Contracts (币本位)")
    print("   - 推荐使用USDT-Margined（更稳定）")

    print("\n3. 风险控制：")
    print("   - 强制平仓价格")
    print("   - 保证金要求")
    print("   - 资金费率")

    print("\n[实现步骤]")

    print("\n步骤1：修改data_engine.py")
    print("  - 导入期货客户端")
    print("  - 使用期货API获取K线数据")
    print("  - 配置期货专用WebSocket")

    print("\n步骤2：修改config.py")
    print("  - 添加期货专用配置")
    print("  - 设置默认杠杆")
    print("  - 配置风险管理参数")

    print("\n步骤3：更新Redis存储")
    print("  - 使用合约价格数据")
    print("  - 包含杠杆信息")
    print("  - 添加强制平仓数据")

    print("\n[代码示例]")

    print("\n期货数据引擎配置:")
    print("""
# 期货客户端初始化
from binance.futures import FuturesClient

futures_client = FuturesClient(
    api_key=api_key,
    api_secret=api_secret,
    testnet=True  # 使用期货测试网
)

# 获取期货K线数据
klines = futures_client.klines(
    symbol='BTCUSDT',
    interval='1m',
    limit=100
)

# 期货WebSocket
stream = 'btcusdt@kline_1m'
# 同一流名称，但数据源是期货市场
""")

    print("\n[风险提示]")

    print("\n  ⚠️ 合约交易风险较高")
    print("  ⚠️ 可能快速亏损（杠杆放大风险）")
    print("  ⚠️ 需要严格的风险管理")
    print("  ⚠️ 建议先用测试网练习")

    print("\n[推荐配置]")

    print("\n  对于AI交易系统:")
    print("    - 数据源: 期货(FUTURES)")
    print("    - 杠杆: 10x-20x (保守)")
    print("    - 风险管理: 强制开启")
    print("    - 测试: 先用测试网")

    print("\n  当前错误配置:")
    print("    - 数据源: 现货(SPOT) ❌")
    print("    - 无杠杆 ❌")
    print("    - 不适合AI策略 ❌")

    print("\n[结论]")
    print("  ✅ 用户反馈正确")
    print("  ✅ 需要切换到合约模式")
    print("  ✅ 这是AI交易工具的正确配置")


if __name__ == "__main__":
    switch_to_futures_config()
