#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据引擎 - WebSocket数据监听和指标计算
负责实时监听币安数据流，计算技术指标，更新Redis
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import time
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
from binance import ThreadedWebsocketManager
from binance.enums import KLINE_INTERVAL_1MINUTE, KLINE_INTERVAL_3MINUTE
from configs.config import Config, WebSocketStreams
from services.redis_manager import redis_manager


class TechnicalIndicators:
    """技术指标计算工具类"""

    @staticmethod
    def calculate_rsi(prices: List[float], period: int = 14) -> float:
        """计算RSI指标"""
        if len(prices) < period + 1:
            return 50.0  # 默认中性值

        # 计算价格变化
        deltas = np.diff(prices)

        # 分离上涨和下跌
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        # 计算平均收益和损失
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    @staticmethod
    def calculate_ema(prices: List[float], period: int) -> float:
        """计算EMA指标"""
        if len(prices) < period:
            return 0.0  # 数据不足返回0.0，表示无法计算

        df = pd.DataFrame({'price': prices})
        ema = df['price'].ewm(span=period, adjust=False).mean().iloc[-1]
        return float(ema)

    @staticmethod
    def calculate_macd(prices: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> Dict[str, float]:
        """计算MACD指标"""
        if len(prices) < slow + signal:
            return {
                'macd_line': 0.0,
                'macd_signal': 0.0,
                'macd_histogram': 0.0
            }

        df = pd.DataFrame({'price': prices})
        ema_fast = df['price'].ewm(span=fast, adjust=False).mean()
        ema_slow = df['price'].ewm(span=slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        macd_signal = macd_line.ewm(span=signal, adjust=False).mean()
        macd_histogram = macd_line - macd_signal

        return {
            'macd_line': float(macd_line.iloc[-1]),
            'macd_signal': float(macd_signal.iloc[-1]),
            'macd_histogram': float(macd_histogram.iloc[-1])
        }

        df = pd.DataFrame({'price': prices})
        ema_fast = df['price'].ewm(span=fast, adjust=False).mean()
        ema_slow = df['price'].ewm(span=slow, adjust=False).mean()

        macd_line = ema_fast - ema_slow
        macd_signal = macd_line.ewm(span=signal, adjust=False).mean()
        macd_histogram = macd_line - macd_signal

        return {
            'macd_line': float(macd_line.iloc[-1]),
            'macd_signal': float(macd_signal.iloc[-1]),
            'macd_histogram': float(macd_histogram.iloc[-1])
        }

    @staticmethod
    def calculate_atr(klines: List[Dict], period: int = 14) -> float:
        """计算ATR指标（平均真实波幅）"""
        if len(klines) < period + 1:
            return 0.0

        # 计算真实波幅
        true_ranges = []
        for i in range(1, len(klines)):
            # 正确处理数据结构：klines[i]['k']['high']
            kline = klines[i]['k']
            prev_kline = klines[i-1]['k']

            high = float(kline['h'])
            low = float(kline['l'])
            prev_close = float(prev_kline['c'])

            tr1 = high - low
            tr2 = abs(high - prev_close)
            tr3 = abs(low - prev_close)

            true_range = max(tr1, tr2, tr3)
            true_ranges.append(true_range)

        # 计算ATR
        atr = np.mean(true_ranges[-period:])
        return float(atr)


class DataEngine:
    """数据引擎 - 负责WebSocket监听和数据处理"""

    def __init__(self):
        """初始化数据引擎"""
        self.twm = None
        self.running = False
        self.symbols = Config.TRADING_SYMBOLS
        self.intervals = Config.KLINE_INTERVALS

        # 数据缓存
        self.klines_cache: Dict[str, List[Dict]] = {}  # symbol: [kline_data]
        self.market_data_cache: Dict[str, Dict] = {}  # symbol: latest_data
        self.last_prices: Dict[str, float] = {}  # symbol: last_price

        # 指标计算器
        self.indicators = TechnicalIndicators()

        # 🔧 改进：预加载历史K线数据，确保有足够数据计算所有指标
        self._preload_historical_klines()

    def _preload_historical_klines(self):
        """预加载历史K线数据，确保有足够数据计算所有指标"""
        print("[DATA_ENGINE] 预加载历史K线数据...")

        try:
            # 🔧 使用期货客户端（AI交易工具应使用合约数据）
            from binance.client import Client
            client = Client(
                api_key=Config.get_binance_config()['api_key'],
                api_secret=Config.get_binance_config()['api_secret'],
                testnet=Config.BINANCE_TESTNET
            )

            if Config.USE_FUTURES:
                print(f"[DATA_ENGINE] 使用期货模式 (杠杆: {Config.DEFAULT_LEVERAGE}x)")
            else:
                print("[DATA_ENGINE] 使用现货模式")

            for symbol in self.symbols:
                try:
                    # 获取100根历史K线（足够计算EMA(50)和MACD）
                    if Config.USE_FUTURES:
                        # 期货API使用futures_klines方法
                        klines = client.futures_klines(
                            symbol=symbol,
                            interval=KLINE_INTERVAL_1MINUTE,
                            limit=100
                        )
                    else:
                        # 现货API使用get_klines方法
                        klines = client.get_klines(
                            symbol=symbol,
                            interval=KLINE_INTERVAL_1MINUTE,
                            limit=100
                        )

                    # 转换为内部格式并缓存
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

                    self.klines_cache[symbol] = processed_klines
                    print(f"[DATA_ENGINE] {symbol}: 预加载{len(processed_klines)}根K线")

                    # 立即计算技术指标
                    self._calculate_and_update_indicators(symbol)

                except Exception as e:
                    print(f"[DATA_ENGINE] {symbol} 预加载失败: {e}")
                    # 即使预加载失败，也初始化空缓存
                    self.klines_cache[symbol] = []

            print("[DATA_ENGINE] 历史K线数据预加载完成")

        except Exception as e:
            print(f"[DATA_ENGINE] 预加载历史K线失败: {e}")
            # 初始化空缓存
            for symbol in self.symbols:
                self.klines_cache[symbol] = []

        # 回调函数
        self.on_kline_callback: Optional[Callable] = None
        self.on_account_update_callback: Optional[Callable] = None
        self.on_order_update_callback: Optional[Callable] = None

        print(f"[DATA_ENGINE] 数据引擎初始化完成")
        print(f"[DATA_ENGINE] 监听交易对: {self.symbols}")
        print(f"[DATA_ENGINE] 监听周期: {self.intervals}")

    def start(self) -> bool:
        """启动数据引擎"""
        try:
            # 获取币安配置
            binance_config = Config.get_binance_config()

            # 初始化WebSocket管理器
            self.twm = ThreadedWebsocketManager(
                api_key=binance_config['api_key'],
                api_secret=binance_config['api_secret'],
                testnet=binance_config['testnet']
            )

            self.twm.start()
            self.running = True

            print("[DATA_ENGINE] WebSocket管理器启动成功")

            # 添加错误处理机制
            try:
                # 订阅市场数据流（带错误处理）
                self._subscribe_market_streams()

                # 订阅用户数据流
                self._subscribe_user_streams()

                print("[DATA_ENGINE] 所有数据流订阅完成")
            except Exception as e:
                print(f"[DATA_ENGINE] WebSocket订阅异常: {e}")
                # 继续运行，即使部分订阅失败

            return True

        except Exception as e:
            print(f"[DATA_ENGINE] 启动失败: {e}")
            return False

    def _subscribe_market_streams(self) -> None:
        """订阅市场数据流（带错误处理和重试机制）"""
        print(f"[DATA_ENGINE] 开始订阅 {len(self.symbols)} 个交易对...")

        # 为每个交易对订阅单独的K线流（更可靠）
        stream_count = 0
        failed_streams = []

        for symbol in self.symbols:
            for interval in self.intervals:
                try:
                    stream_name = f"{symbol.lower()}@kline_{interval}"
                    print(f"     订阅 {stream_name}")

                    # 启动单个K线流（带超时控制）
                    self.twm.start_kline_socket(
                        callback=self._handle_market_data,
                        symbol=symbol,
                        interval=interval
                    )
                    stream_count += 1

                except Exception as e:
                    error_msg = str(e)
                    if "ConnectionResetError" in error_msg:
                        print(f"     [重试] {symbol} {interval} 连接重置，正在重试...")
                        failed_streams.append((symbol, interval))
                    else:
                        print(f"     订阅 {symbol} {interval} 失败: {e}")

        print(f"[DATA_ENGINE] 成功订阅 {stream_count} 个K线数据流")

        # 也订阅一些价格流作为备用
        print(f"[DATA_ENGINE] 订阅价格数据流...")
        for symbol in self.symbols[:3]:  # 只订阅前3个避免过多连接
            try:
                stream_name = f"{symbol.lower()}@ticker"
                print(f"     订阅 {stream_name}")

                self.twm.start_symbol_ticker_socket(
                    callback=self._handle_ticker_data,
                    symbol=symbol
                )
                stream_count += 1

            except Exception as e:
                print(f"     订阅 {symbol} 价格流失败: {e}")

        print(f"[DATA_ENGINE] 总共订阅 {stream_count} 个数据流")

    def _subscribe_user_streams(self) -> None:
        """订阅用户数据流（需要API认证）"""
        try:
            print("[DATA_ENGINE] 订阅用户数据流")
            print("[INFO] 暂时跳过用户数据流订阅（非必需）")
            # ThreadedWebsocketManager没有user_socket方法，跳过此功能

        except Exception as e:
            print(f"[DATA_ENGINE] 订阅用户数据流失败: {e}")

    def _handle_market_data(self, msg: Dict[str, Any]) -> None:
        """处理市场数据消息（单个K线流）"""
        try:
            # 处理WebSocket错误消息
            if msg.get('e') == 'error':
                error_type = msg.get('type', '')
                error_message = msg.get('m', '')
                print(f"[DATA_ENGINE] WebSocket错误: {error_type} - {error_message}")

                # 根据官方文档，BinanceWebsocketClosed错误会自动重连，忽略它
                if error_type == 'BinanceWebsocketClosed':
                    print(f"[DATA_ENGINE] WebSocket连接已关闭，系统将自动重连...")
                    return
                else:
                    # 其他错误类型需要处理
                    print(f"[DATA_ENGINE] 未知错误类型: {error_type}")
                    return

            # 单个K线流的消息格式不同
            if 'e' in msg and msg['e'] == 'kline':
                # 处理K线数据
                self._handle_kline_data_single(msg)

        except Exception as e:
            print(f"[DATA_ENGINE] 处理市场数据失败: {e}")

    def _handle_ticker_data(self, msg: Dict[str, Any]) -> None:
        """处理ticker数据消息"""
        try:
            # 处理WebSocket错误消息
            if msg.get('e') == 'error':
                error_type = msg.get('type', '')
                error_message = msg.get('m', '')
                print(f"[DATA_ENGINE] WebSocket错误: {error_type} - {error_message}")

                # 根据官方文档，BinanceWebsocketClosed错误会自动重连，忽略它
                if error_type == 'BinanceWebsocketClosed':
                    print(f"[DATA_ENGINE] WebSocket连接已关闭，系统将自动重连...")
                    return
                else:
                    # 其他错误类型需要处理
                    print(f"[DATA_ENGINE] 未知错误类型: {error_type}")
                    return

            if 'e' in msg and msg['e'] == '24hrTicker':
                self._handle_ticker_data_single(msg)

        except Exception as e:
            print(f"[DATA_ENGINE] 处理ticker数据失败: {e}")

    def _handle_market_data_multiplex(self, msg: Dict[str, Any]) -> None:
        """处理多路复用流市场数据消息"""
        try:
            stream = msg.get('stream', '')
            data = msg.get('data', {})

            # 处理K线数据
            if 'kline' in data:
                self._handle_kline_data(data, stream)

            # 处理标记价格数据
            elif 'e' in data and data['e'] == 'markPriceUpdate':
                self._handle_mark_price_data(data, stream)

        except Exception as e:
            print(f"[DATA_ENGINE] 处理市场数据失败: {e}")

    def _handle_kline_data(self, data: Dict[str, Any], stream: str) -> None:
        """处理K线数据"""
        kline = data['k']
        symbol = data['s']
        interval = kline['i']
        is_closed = kline['x']

        # 解析symbol和interval
        stream_parts = stream.split('@')
        if len(stream_parts) == 2:
            stream_symbol = stream_parts[0].upper()
            stream_interval = stream_parts[1].replace('kline_', '')

            # 只处理完成的K线
            if is_closed:
                # 缓存K线数据
                if stream_symbol not in self.klines_cache:
                    self.klines_cache[stream_symbol] = []

                self.klines_cache[stream_symbol].append(kline)

                # 保持缓存大小（最多100根K线）
                if len(self.klines_cache[stream_symbol]) > 100:
                    self.klines_cache[stream_symbol] = self.klines_cache[stream_symbol][-100:]

                # 更新市场数据到Redis
                market_data = {
                    'symbol': stream_symbol,
                    'price': float(kline['c']),  # 收盘价
                    'open': float(kline['o']),
                    'high': float(kline['h']),
                    'low': float(kline['l']),
                    'volume': float(kline['v']),
                    'close_time': kline['T'],
                    'interval': stream_interval,
                    'is_closed': True,
                    'open_time': kline['t']
                }

                # 更新Redis
                if redis_manager.update_market_data(stream_symbol, market_data):
                    print(f"[DATA_ENGINE] 更新 {stream_symbol} 市场数据成功")

                # 更新价格缓存
                self.last_prices[stream_symbol] = float(kline['c'])

                # 计算并更新技术指标
                self._calculate_and_update_indicators(stream_symbol)

                # 触发K线回调（如果设置了）
                if self.on_kline_callback:
                    try:
                        self.on_kline_callback(stream_symbol, market_data)
                    except Exception as e:
                        print(f"[DATA_ENGINE] K线回调执行失败: {e}")

            else:
                # K线未完成，记录中间价格
                current_price = float(kline['c'])
                self.last_prices[stream_symbol] = current_price

    def _handle_kline_data_single(self, msg: Dict[str, Any]) -> None:
        """处理单个K线流数据（简化版）"""
        try:
            kline = msg['k']
            symbol = msg['s']
            is_closed = kline['x']

            # 缓存K线数据（无论是否完成）
            if symbol not in self.klines_cache:
                self.klines_cache[symbol] = []

            # 存储完整的K线数据
            self.klines_cache[symbol].append(msg)

            # 保持缓存大小（最多100根K线）
            if len(self.klines_cache[symbol]) > 100:
                self.klines_cache[symbol] = self.klines_cache[symbol][-100:]

            # 只处理完成的K线
            if is_closed:
                # 获取24h变化数据（从ticker缓存或Redis）
                price_change_24h = None
                if symbol in self.last_prices:
                    # 尝试从Redis获取最新的24h变化
                    redis_data = redis_manager.get_market_data(symbol)
                    if redis_data:
                        price_change_24h = redis_data.get('change_24h_pct') or redis_data.get('price_change_percent_24h')

                market_data = {
                    'symbol': symbol,
                    'price': float(kline['c']),  # 收盘价
                    'open': float(kline['o']),
                    'high': float(kline['h']),
                    'low': float(kline['l']),
                    'volume': float(kline['v']),
                    'interval': kline['i'],
                    'is_closed': True,
                    'open_time': kline['t'],
                    # 关键：添加24h变化数据（统一字段名）
                    'price_change_percent_24h': float(price_change_24h) if price_change_24h is not None else 0.0
                }

                # 更新Redis
                if redis_manager.update_market_data(symbol, market_data):
                    change_text = f", 24h: {market_data['price_change_percent_24h']:+.2f}%" if market_data['price_change_percent_24h'] != 0 else ""
                    print(f"[DATA_ENGINE] {symbol} K线完成: ${market_data['price']:,.2f}{change_text}")

                # 更新价格缓存
                self.last_prices[symbol] = float(kline['c'])

                # 计算并更新技术指标
                self._calculate_and_update_indicators(symbol)

                # 触发K线回调（如果设置了）
                if self.on_kline_callback:
                    try:
                        self.on_kline_callback(symbol, market_data)
                    except Exception as e:
                        print(f"[DATA_ENGINE] K线回调执行失败: {e}")
        except Exception as e:
            print(f"[DATA_ENGINE] 处理单个K线数据失败: {e}")
            import traceback
            traceback.print_exc()

    def _handle_ticker_data_single(self, msg: Dict[str, Any]) -> None:
        """处理单个ticker数据"""
        try:
            symbol = msg['s']
            price = float(msg['c'])  # 当前价格
            change_percent = float(msg['P'])  # 24h变化百分比
            volume = float(msg['v'])  # 成交量
            high_24h = float(msg['h'])  # 24h最高
            low_24h = float(msg['l'])  # 24h最低

            # 更新价格缓存
            self.last_prices[symbol] = price

            # 更新市场数据（使用统一字段名）
            market_data = {
                'symbol': symbol,
                'price': price,
                # 统一使用 price_change_percent_24h 字段名
                'price_change_percent_24h': change_percent,
                'volume': volume,
                'high_24h': high_24h,
                'low_24h': low_24h,
                'last_price_time': msg['E'],
                'is_closed': False,  # ticker数据持续更新
                'update_time': datetime.now().isoformat()
            }

            # 更新Redis
            redis_manager.update_market_data(symbol, market_data)

            # 显示价格变化（包含24h数据）
            if abs(change_percent) > 0.1:  # 变化超过0.1%
                print(f"[DATA_ENGINE] {symbol} 价格: ${price:,.2f}, 24h: {change_percent:+.2f}%")

            # 触发K线回调
            if self.on_kline_callback:
                try:
                    self.on_kline_callback(symbol, market_data)
                except Exception as e:
                    print(f"[DATA_ENGINE] Ticker回调执行失败: {e}")
        except Exception as e:
            print(f"[DATA_ENGINE] 处理单个ticker数据失败: {e}")
            import traceback
            traceback.print_exc()

    def _handle_mark_price_data(self, data: Dict[str, Any], stream: str) -> None:
        """处理标记价格数据"""
        symbol = data['s']
        mark_price = float(data['p'])
        funding_rate = float(data['r'])

        print(f"[DATA_ENGINE] {symbol} 标记价格: ${mark_price:.2f}, 资金费率: {funding_rate:.6f}")

        # 更新资金费率到Redis（用于Alpha Arena提示词）
        try:
            market_data = redis_manager.get_market_data(symbol) or {}
            market_data['funding_rate'] = funding_rate
            market_data['mark_price'] = mark_price
            redis_manager.store_market_data(symbol, market_data)
        except Exception as e:
            print(f"[DATA_ENGINE] 存储资金费率到Redis失败: {e}")

        # 这里可以更新资金费率到Redis或触发相关逻辑
        # 例如：资金费率异常时触发风控检查

    def _handle_user_data(self, msg: Dict[str, Any]) -> None:
        """处理用户数据消息"""
        event_type = msg.get('e')

        if event_type == 'executionReport':
            # 订单执行报告
            self._handle_order_execution(msg)

        elif event_type == 'outboundAccountPosition':
            # 账户或持仓更新
            self._handle_account_update(msg)

        elif event_type == 'balanceUpdate':
            # 余额更新
            self._handle_balance_update(msg)

    def _handle_order_execution(self, msg: Dict[str, Any]) -> None:
        """处理订单执行"""
        symbol = msg['s']
        order_status = msg['X']  # NEW, PARTIALLY_FILLED, FILLED, CANCELED
        side = msg['S']  # BUY, SELL
        quantity = float(msg['q'])
        price = float(msg['p'])

        print(f"[DATA_ENGINE] 订单执行: {symbol} {side} {quantity} @ {price} - {order_status}")

        # 如果订单成交，触发账户和持仓更新
        if order_status in ['PARTIALLY_FILLED', 'FILLED']:
            # 可以在这里触发风控检查
            if self.on_order_update_callback:
                try:
                    self.on_order_update_callback(symbol, msg)
                except Exception as e:
                    print(f"[DATA_ENGINE] 订单更新回调执行失败: {e}")

    def _handle_account_update(self, msg: Dict[str, Any]) -> None:
        """处理账户更新"""
        # 解析账户信息
        account_info = {}
        balances = msg.get('B', [])

        for balance in balances:
            asset = balance['a']
            free = float(balance['f'])
            locked = float(balance['l'])

            if free > 0 or locked > 0:
                account_info[asset] = {
                    'free': free,
                    'locked': locked,
                    'total': free + locked
                }

        print(f"[DATA_ENGINE] 账户更新: {len(account_info)} 个资产")

        # 更新Redis
        if redis_manager.update_account_status(account_info):
            print("[DATA_ENGINE] 账户状态更新成功")

        # 触发账户更新回调
        if self.on_account_update_callback:
            try:
                self.on_account_update_callback(account_info)
            except Exception as e:
                print(f"[DATA_ENGINE] 账户更新回调执行失败: {e}")

    def _handle_balance_update(self, msg: Dict[str, Any]) -> None:
        """处理余额更新"""
        asset = msg['a']
        delta = float(msg['d'])  # 余额变化
        event_time = msg['E']

        print(f"[DATA_ENGINE] 余额更新: {asset} 变化 {delta}")

    def _calculate_and_update_indicators(self, symbol: str) -> None:
        """计算并更新技术指标"""
        try:
            # 获取K线数据
            if symbol not in self.klines_cache or len(self.klines_cache[symbol]) < 7:
                return  # 至少需要7根K线计算基本指标

            klines = self.klines_cache[symbol]

            # 提取价格数据（正确的数据结构：kline['k']['c']）
            prices = [float(kline['k']['c']) for kline in klines]

            # 计算技术指标
            indicators = {}

            # RSI指标
            indicators['rsi_7'] = self.indicators.calculate_rsi(prices, period=7)
            indicators['rsi_14'] = self.indicators.calculate_rsi(prices, period=14)

            # EMA指标（需要足够数据）
            indicators['ema_20'] = self.indicators.calculate_ema(prices, period=20)
            indicators['ema_50'] = self.indicators.calculate_ema(prices, period=50)

            # MACD指标（需要足够数据）
            if len(prices) >= 35:  # MACD需要26+9=35根K线
                macd_data = self.indicators.calculate_macd(prices)
                indicators.update(macd_data)
            else:
                indicators.update({
                    'macd_line': 0.0,
                    'macd_signal': 0.0,
                    'macd_histogram': 0.0
                })

            # ATR指标（需要足够数据）
            if len(klines) >= 14:
                indicators['atr_14'] = self.indicators.calculate_atr(klines, period=14)
            else:
                indicators['atr_14'] = 0.0

            # 🔧 修复：转换numpy类型为Python原生类型（解决Redis存储问题）
            # 防止 numpy.float64 等类型被存储为字符串
            import numpy as np
            clean_indicators = {}
            for key, value in indicators.items():
                if hasattr(value, 'item'):  # numpy类型 (如 np.float64, np.int64)
                    # 调用.item()方法转换为Python原生类型
                    clean_indicators[key] = value.item()
                elif isinstance(value, (np.float64, np.float32, np.int64, np.int32)):
                    # 显式转换为Python float
                    clean_indicators[key] = float(value)
                else:
                    clean_indicators[key] = value

            # 更新Redis
            if redis_manager.update_indicators(symbol, clean_indicators):
                print(f"[DATA_ENGINE] {symbol} 技术指标更新成功: RSI={indicators['rsi_14']:.2f}, EMA20={indicators['ema_20']:.2f}")

        except Exception as e:
            print(f"[DATA_ENGINE] 计算技术指标失败: {e}")
            import traceback
            traceback.print_exc()

    def set_callbacks(self, on_kline: Optional[Callable] = None,
                     on_account: Optional[Callable] = None,
                     on_order: Optional[Callable] = None) -> None:
        """设置回调函数"""
        self.on_kline_callback = on_kline
        self.on_account_update_callback = on_account
        self.on_order_update_callback = on_order

    def get_latest_price(self, symbol: str) -> Optional[float]:
        """获取最新价格"""
        return self.last_prices.get(symbol)

    def get_klines_data(self, symbol: str, limit: int = 50) -> Optional[List[Dict]]:
        """获取K线数据"""
        if symbol in self.klines_cache:
            return self.klines_cache[symbol][-limit:]
        return None

    def stop(self) -> None:
        """停止数据引擎"""
        if self.twm:
            self.twm.stop()
            self.running = False
            print("[DATA_ENGINE] 数据引擎已停止")

    def join(self) -> None:
        """等待数据引擎完成（阻塞主线程）"""
        if self.twm:
            self.twm.join()


if __name__ == "__main__":
    # 测试数据引擎
    print("=== 数据引擎测试 ===")

    data_engine = DataEngine()

    # 设置回调函数
    def on_kline(symbol, data):
        print(f"[回调] K线完成: {symbol} 价格: ${data['price']:.2f}")

    def on_account(account_info):
        print(f"[回调] 账户更新: {len(account_info)} 个资产")

    def on_order(symbol, order_data):
        print(f"[回调] 订单更新: {symbol}")

    data_engine.set_callbacks(on_kline, on_account, on_order)

    # 启动数据引擎
    if data_engine.start():
        print("\n[INFO] 数据引擎运行中，按 Ctrl+C 停止...")

        try:
            # 保持运行
            data_engine.join()

        except KeyboardInterrupt:
            print("\n[INFO] 收到停止信号")

    # 停止数据引擎
    data_engine.stop()
    print("[INFO] 数据引擎测试结束")
