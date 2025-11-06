#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
现货 vs 合约数据识别指南
"""

def identify_spot_vs_futures():
    print("=" * 80)
    print(" 现货 vs 合约数据识别指南")
    print("=" * 80)

    print("\n[1] 通过API端点判断]")
    print("  现货API:")
    print("    - REST: https://api.binance.com/api/v3/...")
    print("    - WebSocket: wss://stream.binance.com:9443/ws/...")
    print("    - 客户端: Client(testnet=False)")
    print()
    print("  合约API:")
    print("    - REST: https://fapi.binance.com/fapi/v1/...")
    print("    - WebSocket: wss://fstream.binance.com/ws/...")
    print("    - 客户端: Client(testnet=False, futures=True)")

    print("\n[2] 通过WebSocket流名称判断]")
    print("  现货K线流:")
    print("    btcusdt@kline_1m")
    print()
    print("  合约K线流:")
    print("    btcusdt@kline_1m@100ms")  # 合约可能有100ms延迟标识")

    print("\n[3] 通过价格特征判断]")
    print("  现货价格特征:")
    print("    - BTC现货通常在$90,000-$110,000区间")
    print("    - 价格整数部分通常较大")
    print("    - 成交量反映真实买卖")
    print()
    print("  合约价格特征:")
    print("    - 价格与现货基本一致")
    print("    - 可能有微小差异（资金费率影响）")
    print("    - 成交量可能更高（杠杆交易）")

    print("\n[4] 通过交易规则判断]")
    print("  现货交易规则:")
    print("    - 权限: ['SPOT']")
    print("    - 价格过滤器: 正常范围")
    print("    - 批量大小: 支持多种规格")
    print()
    print("  合约交易规则:")
    print("    - 权限: ['FUTURES', 'DERIVATIVES']")
    print("    - 价格过滤器: 可能更严格")
    print("    - 批量大小: 有最小/最大限制")
    print("    - 强制平仓规则")

    print("\n[5] 当前系统配置]")
    print("  ✅ 配置: 使用现货市场数据")
    print("  ✅ API端点: /api (现货)")
    print("  ✅ WebSocket: 现货流")
    print("  ✅ 价格: $101,378.53 (现货价格)")
    print("  ✅ K线数据: 现货K线")

    print("\n[6] 如果要切换到合约数据]")
    print("  需要修改:")
    print("    1. API配置: 使用 /fapi 端点")
    print("    2. WebSocket: 使用 fstream.binance.com")
    print("    3. 客户端: Client(futures=True)")
    print("    4. 符号: 可能需要不同的符号格式")
    print("    5. 杠杆设置: 需要配置杠杆倍数")

    print("\n[7] 推荐做法]")
    print("  对于AI交易系统:")
    print("    - 现货: 更稳定，适合长期投资")
    print("    - 合约: 高风险高收益，适合短期交易")
    print("    - 建议: 新手先用现货练习")


if __name__ == "__main__":
    identify_spot_vs_futures()
