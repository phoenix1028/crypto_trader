#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
改进K线数据收集的方案
确保系统启动时有足够的K线数据计算EMA(50)和MACD
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from binance.client import Client
from crypto_trader.core.data_engine import DataEngine
from crypto_trader.services.redis_manager import redis_manager
from crypto_trader.configs.config import Config


def improve_kline_collection():
    """改进K线数据收集方案"""
    print("=" * 80)
    print(" 改进K线数据收集方案")
    print("=" * 80)

    # 1. 方案A：系统启动时预加载历史K线
    print("\n[方案A] 系统启动时预加载历史K线")
    print("-" * 40)

    client = Client()
    symbols = Config.TRADING_SYMBOLS

    print(f"  需要获取{len(symbols)}个交易对的K线数据")
    print(f"  每个交易对获取100根历史K线")

    # 为每个交易对获取足够的历史K线
    for symbol in symbols:
        try:
            # 获取100根K线（足够计算所有指标）
            klines = client.get_klines(
                symbol=symbol,
                interval=Client.KLINE_INTERVAL_1MINUTE,
                limit=100  # 100根K线足够计算EMA(50)和MACD
            )

            print(f"\n  {symbol}:")
            print(f"    获取到 {len(klines)} 根K线")

            # 转换为内部格式
            processed_klines = []
            for k in klines:
                kline_msg = {
                    's': symbol,
                    'k': {
                        't': k[0],
                        'T': k[6],
                        's': symbol,
                        'i': '1m',
                        'o': k[1],
                        'c': k[4],
                        'h': k[2],
                        'l': k[3],
                        'v': k[5],
                        'x': True
                    }
                }
                processed_klines.append(kline_msg)

            # 手动触发指标计算
            data_engine = DataEngine()
            data_engine.klines_cache[symbol] = processed_klines
            data_engine._calculate_and_update_indicators(symbol)

            # 验证结果
            indicators = redis_manager.get_indicators(symbol)
            if indicators:
                ema_50 = indicators.get('ema_50', 0)
                macd_line = indicators.get('macd_line', 0)

                print(f"    EMA(50): {ema_50:>10.2f} {'[OK]' if ema_50 != 0 else '[FAIL]'}")
                macd_status = '[OK]' if macd_line != 0 else '[FAIL]'
                print(f"    MACD: {macd_line:>10.2f} {macd_status}")

            print(f"    [OK] 数据加载完成")

        except Exception as e:
            print(f"    [ERROR] 获取{symbol} K线失败: {e}")

    # 2. 方案B：改进data_engine的初始化逻辑
    print("\n[方案B] 改进data_engine的初始化逻辑")
    print("-" * 40)

    print("""
  在data_engine.py的__init__方法中添加：

    def __init__(self):
        # 现有代码...
        self.symbols = Config.TRADING_SYMBOLS
        self.klines_cache = {}

        # 🔧 改进：预加载历史K线数据
        self._preload_historical_klines()

    def _preload_historical_klines(self):
        '''预加载历史K线数据'''
        print("[DATA_ENGINE] 预加载历史K线数据...")

        try:
            client = Client()
            for symbol in self.symbols:
                try:
                    # 获取100根历史K线
                    klines = client.get_klines(
                        symbol=symbol,
                        interval=Client.KLINE_INTERVAL_1MINUTE,
                        limit=100
                    )

                    # 转换为内部格式并缓存
                    processed_klines = []
                    for k in klines:
                        processed_klines.append({
                            's': symbol,
                            'k': {
                                't': k[0],
                                'T': k[6],
                                's': symbol,
                                'i': '1m',
                                'o': k[1],
                                'c': k[4],
                                'h': k[2],
                                'l': k[3],
                                'v': k[5],
                                'x': True
                            }
                        })

                    self.klines_cache[symbol] = processed_klines
                    print(f"[DATA_ENGINE] {symbol}: 预加载{len(processed_klines)}根K线")

                except Exception as e:
                    print(f"[DATA_ENGINE] {symbol} 预加载失败: {e}")

            print("[DATA_ENGINE] 历史K线数据预加载完成")

        except Exception as e:
            print(f"[DATA_ENGINE] 预加载历史K线失败: {e}")
    """)

    # 3. 方案C：WebSocket失败时的备用方案
    print("\n[方案C] WebSocket失败时的备用方案")
    print("-" * 40)

    print("""
  在start()方法中添加WebSocket状态检查：

    async def start(self):
        # 启动WebSocket
        success = self._start_websocket()

        if not success:
            print("[DATA_ENGINE] WebSocket启动失败，使用HTTP API模式")
            # 定期通过HTTP API获取数据
            self._start_http_fallback_mode()

    def _start_http_fallback_mode(self):
        '''HTTP API备用模式：定期获取K线数据'''
        def fetch_klines_periodically():
            while self.running:
                for symbol in self.symbols:
                    try:
                        # 获取最新K线
                        client = Client()
                        klines = client.get_klines(
                            symbol=symbol,
                            interval=Client.KLINE_INTERVAL_1MINUTE,
                            limit=1
                        )

                        if klines:
                            kline_msg = {
                                's': symbol,
                                'k': {
                                    't': klines[0][0],
                                    'T': klines[0][6],
                                    's': symbol,
                                    'i': '1m',
                                    'o': klines[0][1],
                                    'c': klines[0][4],
                                    'h': klines[0][2],
                                    'l': klines[0][3],
                                    'v': klines[0][5],
                                    'x': True
                                }
                            }

                            # 更新K线缓存
                            if symbol not in self.klines_cache:
                                self.klines_cache[symbol] = []
                            self.klines_cache[symbol].append(kline_msg)

                            # 保持缓存大小（最多100根）
                            if len(self.klines_cache[symbol]) > 100:
                                self.klines_cache[symbol] = self.klines_cache[symbol][-100:]

                    except Exception as e:
                        print(f"[DATA_ENGINE] 获取{symbol} K线失败: {e}")

                time.sleep(60)  # 每分钟获取一次

        # 在后台线程中运行
        import threading
        thread = threading.Thread(target=fetch_klines_periodically)
        thread.daemon = True
        thread.start()
    """)

    # 4. 验证当前数据收集效果
    print("\n[4] 验证当前数据收集效果")
    print("-" * 40)

    data_engine = DataEngine()

    print(f"  data_engine.klines_cache当前状态:")
    for symbol in symbols:
        cached_count = len(data_engine.klines_cache.get(symbol, []))
        indicators = redis_manager.get_indicators(symbol)

        ema_50 = indicators.get('ema_50', 0) if indicators else 0
        macd_line = indicators.get('macd_line', 0) if indicators else 0

        status = "[OK]" if ema_50 != 0 and macd_line != 0 else "[FAIL]"
        print(f"    {symbol}: {status}")
        print(f"      K线数量: {cached_count}")
        print(f"      EMA(50): {ema_50:>10.2f}")
        print(f"      MACD: {macd_line:>10.2f}")

        if cached_count < 50:
            print(f"      [问题] K线数据不足，无法计算完整指标")

    # 5. 推荐的最佳方案
    print("\n" + "=" * 80)
    print(" 推荐的最佳方案")
    print("=" * 80)

    print("""
  [方案1: 完整实现] - 推荐
    1. 修改data_engine.py的__init__方法，添加预加载历史K线逻辑
    2. 在start()方法中添加WebSocket状态检查
    3. 如果WebSocket失败，自动切换到HTTP API模式
    4. 保持指标计算的数学标准不变

  [方案2: 简化版]
    1. 在event_system启动前，预先为每个交易对获取100根K线
    2. 将K线数据加载到data_engine的klines_cache
    3. 手动触发指标计算
    4. 然后启动WebSocket

  [方案3: 紧急修复]
    1. 当前立即可用的方案
    2. 运行本脚本，手动预加载所有交易对的K线数据
    3. 这将立即解决EMA(50)和MACD为0的问题
    """)


if __name__ == "__main__":
    improve_kline_collection()
