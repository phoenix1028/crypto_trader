#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Alpha Arena数据格式化器
使用真实历史K线数据转换为Alpha Arena提示词所需格式
"""

from typing import Dict, Any, List
from datetime import datetime
import pandas as pd
import os
from binance import Client


class AlphaArenaFormatter:
    """Alpha Arena数据格式化器"""

    def __init__(self):
        self.supported_symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "DOGEUSDT"]
        # 初始化币安客户端
        self.api_key = os.getenv('BINANCE_API_KEY')
        self.secret_key = os.getenv('BINANCE_SECRET_KEY')
        self.client = Client(self.api_key, self.secret_key)

    def format_market_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        格式化市场数据为Alpha Arena格式（使用真实K线数据）

        Args:
            raw_data: 原始市场数据，格式为 {symbol: EnhancedMarketData}

        Returns:
            Alpha Arena格式的市场数据
        """
        formatted_data = {}

        for symbol in self.supported_symbols:
            if symbol in raw_data:
                try:
                    # 获取真实的K线数据
                    formatted_data[symbol] = self._format_single_symbol_data(raw_data[symbol], symbol)
                except Exception as e:
                    print(f"[ERROR] 格式化{symbol}数据失败: {e}")
                    # 即使失败也返回基本数据
                    formatted_data[symbol] = self._create_fallback_data(raw_data[symbol])

        return formatted_data

    def _format_single_symbol_data(self, data: Any, symbol: str) -> Dict[str, Any]:
        """格式化单个币种的数据（使用真实K线数据）"""
        # 统一处理字典和对象格式
        def safe_get(obj, key, default=None):
            """安全获取属性或字典值"""
            if isinstance(obj, dict):
                return obj.get(key, default)
            else:
                return getattr(obj, key, default)

        # 基本价格数据
        current_price = float(safe_get(data, 'current_price', 0))

        # 获取真实K线数据
        try:
            # 获取3分钟K线数据（用于日内序列）
            klines_3m = self.client.get_klines(
                symbol=symbol,
                interval='3m',
                limit=50
            )

            # 获取4小时K线数据（用于长期背景）
            klines_4h = self.client.get_klines(
                symbol=symbol,
                interval='4h',
                limit=20
            )

            # 计算真实的指标序列
            price_series_3m = [float(k[4]) for k in klines_3m[-10:]]  # 中间价（收盘价）
            ema20_series_3m = self._calculate_ema_series([float(k[4]) for k in klines_3m], 20)[-10:]
            macd_series_3m = self._calculate_macd_series([float(k[4]) for k in klines_3m])[-10:]
            rsi7_series_3m = self._calculate_rsi_series([float(k[4]) for k in klines_3m], 7)[-10:]
            rsi14_series_3m = self._calculate_rsi_series([float(k[4]) for k in klines_3m], 14)[-10:]

            # 计算4小时长期背景
            price_4h = [float(k[4]) for k in klines_4h[-10:]]
            ema20_4h = self._calculate_ema_series(price_4h, 20)
            ema50_4h = self._calculate_ema_series(price_4h, 50)
            macd_series_4h = self._calculate_macd_series(price_4h)[-10:]
            rsi14_series_4h = self._calculate_rsi_series(price_4h, 14)[-10:]

            # 计算ATR
            highs_4h = [float(k[2]) for k in klines_4h[-20:]]
            lows_4h = [float(k[3]) for k in klines_4h[-20:]]
            closes_4h = [float(k[4]) for k in klines_4h[-20:]]
            atr3_4h = self._calculate_atr(highs_4h, lows_4h, closes_4h, 3)
            atr14_4h = self._calculate_atr(highs_4h, lows_4h, closes_4h, 14)

            # 计算成交量
            volumes_4h = [float(k[5]) for k in klines_4h[-20:]]
            volume_current_4h = volumes_4h[-1] if volumes_4h else 0
            volume_average_4h = sum(volumes_4h) / len(volumes_4h) if volumes_4h else 0

            # 获取资金费率和未平仓合约
            funding_rate = 0.0
            try:
                mark_data = self.client.futures_mark_price(symbol=symbol)
                funding_rate = float(mark_data.get('lastFundingRate', 0))
            except:
                pass

            open_interest_latest = 0.0
            try:
                oi_data = self.client.futures_open_interest(symbol=symbol)
                open_interest_latest = float(oi_data.get('openInterest', 0))
            except:
                pass

            open_interest_avg = open_interest_latest  # 暂时使用最新值

            return {
                "current_price": current_price,
                "funding_rate": funding_rate,
                "open_interest_latest": open_interest_latest,
                "open_interest_avg": open_interest_avg,
                "price_series": price_series_3m,
                "ema20_series": ema20_series_3m,
                "macd_series": macd_series_3m,
                "rsi7_series": rsi7_series_3m,
                "rsi14_series": rsi14_series_3m,
                "long_term_4h": {
                    "ema_20_4h": ema20_4h[-1] if ema20_4h else 0,
                    "ema_50_4h": ema50_4h[-1] if ema50_4h else 0,
                    "atr_3_4h": atr3_4h if atr3_4h else 0,
                    "atr_14_4h": atr14_4h if atr14_4h else 0,
                    "volume_current_4h": volume_current_4h,
                    "volume_average_4h": volume_average_4h,
                    "macd_series_4h": macd_series_4h,
                    "rsi14_series_4h": rsi14_series_4h
                },
                "indicators": safe_get(data, 'indicators', {})
            }

        except Exception as e:
            print(f"[ERROR] 获取{symbol}真实K线数据失败: {e}")
            return self._create_fallback_data(data)

    def _create_fallback_data(self, data: Any) -> Dict[str, Any]:
        """创建备用数据（使用现有数据，不模拟）"""
        def safe_get(obj, key, default=None):
            if isinstance(obj, dict):
                return obj.get(key, default)
            else:
                return getattr(obj, key, default)

        current_price = float(safe_get(data, 'current_price', 0))
        indicators = safe_get(data, 'indicators', {})

        # 返回基本数据，不生成任何模拟序列
        return {
            "current_price": current_price,
            "funding_rate": 0.0,
            "open_interest_latest": 0.0,
            "open_interest_avg": 0.0,
            "price_series": [current_price] * 10,  # 只重复当前价格，不模拟变化
            "ema20_series": [current_price] * 10,
            "macd_series": [0.0] * 10,
            "rsi7_series": [50.0] * 10,
            "rsi14_series": [50.0] * 10,
            "long_term_4h": {
                "ema_20_4h": current_price,
                "ema_50_4h": current_price,
                "atr_3_4h": 0.0,
                "atr_14_4h": 0.0,
                "volume_current_4h": 0.0,
                "volume_average_4h": 0.0,
                "macd_series_4h": [0.0] * 10,
                "rsi14_series_4h": [50.0] * 10
            },
            "indicators": indicators
        }

    def _calculate_ema_series(self, prices: List[float], period: int) -> List[float]:
        """计算EMA序列"""
        if len(prices) < period:
            return prices

        df = pd.DataFrame({'close': prices})
        ema = df['close'].ewm(span=period, adjust=False).mean()
        return ema.tolist()

    def _calculate_macd_series(self, prices: List[float]) -> List[float]:
        """计算MACD序列"""
        if len(prices) < 26:
            return [0.0] * len(prices)

        df = pd.DataFrame({'close': prices})
        ema_12 = df['close'].ewm(span=12, adjust=False).mean()
        ema_26 = df['close'].ewm(span=26, adjust=False).mean()
        macd_line = ema_12 - ema_26
        return macd_line.tolist()

    def _calculate_rsi_series(self, prices: List[float], period: int) -> List[float]:
        """计算RSI序列"""
        if len(prices) < period + 1:
            return [50.0] * len(prices)

        df = pd.DataFrame({'close': prices})
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.tolist()

    def _calculate_atr(self, highs: List[float], lows: List[float], closes: List[float], period: int) -> float:
        """计算ATR"""
        if len(highs) < period + 1 or len(lows) < period + 1 or len(closes) < period + 1:
            return 0.0

        # 计算True Range
        high_low = [h - l for h, l in zip(highs[1:], lows[1:])]
        high_close = [abs(h - c) for h, c in zip(highs[1:], closes[:-1])]
        low_close = [abs(l - c) for l, c in zip(lows[1:], closes[:-1])]

        tr = [max(hl, hc, lc) for hl, hc, lc in zip(high_low, high_close, low_close)]

        # 计算ATR
        if len(tr) >= period:
            atr = sum(tr[:period]) / period
            return atr
        return 0.0

    def format_account_info(self, account_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        格式化账户信息

        Args:
            account_data: 原始账户数据

        Returns:
            Alpha Arena格式的账户信息
        """
        # 计算总回报率
        total_return_pct = 0.0
        if account_data.get('initial_balance') and account_data.get('current_balance'):
            initial = float(account_data['initial_balance'])
            current = float(account_data['current_balance'])
            total_return_pct = ((current - initial) / initial) * 100

        # 格式化持仓信息
        positions = account_data.get('positions', [])
        formatted_positions = []
        for pos in positions:
            if pos.get('quantity', 0) > 0:  # 只包含活跃仓位
                formatted_positions.append({
                    'symbol': pos.get('symbol', ''),
                    'quantity': float(pos.get('quantity', 0)),
                    'entry_price': float(pos.get('entry_price', 0)),
                    'current_price': float(pos.get('current_price', 0)),
                    'liquidation_price': float(pos.get('liquidation_price', 0)),
                    'unrealized_pnl': float(pos.get('unrealized_pnl', 0)),
                    'leverage': int(pos.get('leverage', 10)),
                    'exit_plan': pos.get('exit_plan', {}),
                    'confidence': float(pos.get('confidence', 0.8)),
                    'risk_usd': float(pos.get('risk_usd', 0)),
                    'sl_oid': pos.get('sl_oid', -1),
                    'tp_oid': pos.get('tp_oid', -1),
                    'wait_for_fill': pos.get('wait_for_fill', False),
                    'entry_oid': pos.get('entry_oid', -1),
                    'notional_usd': float(pos.get('notional_usd', 0))
                })

        return {
            'total_return_pct': total_return_pct,
            'available_cash': float(account_data.get('available_cash', 0)),
            'account_value': float(account_data.get('current_balance', 0)),
            'positions': formatted_positions
        }

    def format_runtime_stats(self, runtime_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        格式化运行统计信息

        Args:
            runtime_data: 原始运行数据

        Returns:
            Alpha Arena格式的运行统计
        """
        return {
            'start_time': runtime_data.get('start_time', datetime.now()),
            'call_count': runtime_data.get('call_count', 0)
        }
