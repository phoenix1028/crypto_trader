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

        # 初始化币安客户端 - 双重架构
        # 1. 测试环境客户端：用于交易相关操作
        self.trade_client = Client(
            os.getenv('TESTNET_BINANCE_API_KEY'),
            os.getenv('TESTNET_BINANCE_SECRET_KEY'),
            testnet=True
        )

        # 2. 正式环境客户端：用于市场数据获取（历史K线）
        self.data_client = Client(
            os.getenv('BINANCE_API_KEY'),
            os.getenv('BINANCE_SECRET_KEY'),
            testnet=False
        )

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
            # 使用测试环境：用于最新价格趋势
            klines_3m = self.trade_client.get_klines(
                symbol=symbol,
                interval='3m',
                limit=100  # 测试网实际限制，获取100个点
            )

            # 获取4小时K线数据（用于长期背景）
            # 使用生产环境：获取充足历史数据（过去30天）
            try:
                # 生产环境：获取30天4小时数据（足够所有长期指标计算）
                # 30天 * 6个4小时/天 = 180个4小时K线
                klines_4h = self.data_client.get_historical_klines(
                    symbol,
                    Client.KLINE_INTERVAL_4HOUR,
                    "30 days ago UTC"
                )
                print(f"[INFO] {symbol}: 使用生产环境获取{len(klines_4h)}个4小时K线")
            except Exception as e:
                # 降级到测试环境15分钟数据
                print(f"[WARNING] {symbol}: 生产环境4小时数据获取失败，使用测试环境15分钟数据: {e}")
                klines_4h = self.trade_client.get_klines(
                    symbol=symbol,
                    interval='15m',
                    limit=100  # 测试网实际有64个点
                )

            # 计算真实的指标序列
            price_series_3m = [float(k[4]) for k in klines_3m[-10:]]  # 中间价（收盘价）
            ema20_series_3m = self._calculate_ema_series([float(k[4]) for k in klines_3m], 20)[-10:]
            macd_series_3m = self._calculate_macd_series([float(k[4]) for k in klines_3m])[-10:]
            rsi7_series_3m = self._calculate_rsi_series([float(k[4]) for k in klines_3m], 7)[-10:]
            rsi14_series_3m = self._calculate_rsi_series([float(k[4]) for k in klines_3m], 14)[-10:]

            # 计算4小时长期背景（使用全部数据，而不是最后10个点）
            price_4h = [float(k[4]) for k in klines_4h]
            ema20_4h = self._calculate_ema_series(price_4h, 20)
            ema50_4h = self._calculate_ema_series(price_4h, 50)
            macd_series_4h = self._calculate_macd_series(price_4h)[-10:]  # 只返回最后10个给提示词
            rsi14_series_4h = self._calculate_rsi_series(price_4h, 14)[-10:]  # 只返回最后10个

            # 计算ATR（使用全部4小时数据）
            highs_4h = [float(k[2]) for k in klines_4h]
            lows_4h = [float(k[3]) for k in klines_4h]
            closes_4h = [float(k[4]) for k in klines_4h]
            atr3_4h = self._calculate_atr(highs_4h, lows_4h, closes_4h, 3)
            atr14_4h = self._calculate_atr(highs_4h, lows_4h, closes_4h, 14)

            # 计算成交量（使用全部4小时数据）
            volumes_4h = [float(k[5]) for k in klines_4h]
            volume_current_4h = volumes_4h[-1] if volumes_4h else 0
            volume_average_4h = sum(volumes_4h) / len(volumes_4h) if volumes_4h else 0

            # 获取资金费率和未平仓合约
            # 使用测试环境（交易相关数据）
            funding_rate = 0.0
            try:
                mark_data = self.trade_client.futures_mark_price(symbol=symbol)
                funding_rate = float(mark_data.get('lastFundingRate', 0))
            except:
                pass

            open_interest_latest = 0.0
            try:
                oi_data = self.trade_client.futures_open_interest(symbol=symbol)
                open_interest_latest = float(oi_data.get('openInterest', 0))
            except:
                pass

            open_interest_avg = open_interest_latest  # 暂时使用最新值

            # 构建返回数据
            result = {
                "current_price": current_price,
                "funding_rate": funding_rate,
                "open_interest_latest": open_interest_latest,
                "open_interest_avg": open_interest_avg,
                "price_series": price_series_3m,
                "ema20_series": ema20_series_3m,
                "macd_series": macd_series_3m,
                "rsi7_series": rsi7_series_3m,
                "rsi14_series": rsi14_series_3m,
                # 添加当前指标值（从序列提取最后一个有效值）
                "current_ema20": ema20_series_3m[-1] if ema20_series_3m and ema20_series_3m[-1] != 0 else current_price,
                "current_macd": macd_series_3m[-1] if macd_series_3m else 0.0,
                "current_rsi7": rsi7_series_3m[-1] if rsi7_series_3m else 50.0,
                "indicators": safe_get(data, 'indicators', {})
            }

            # 只有当4小时数据充足时才包含长期背景
            # 生产环境：30天数据通常有180个4小时K线（充足）
            # 测试环境：仅5个K线（严重不足）
            if len(klines_4h) >= 20:
                result["long_term_4h"] = {
                    "ema_20_4h": ema20_4h[-1] if ema20_4h else 0,
                    "ema_50_4h": ema50_4h[-1] if ema50_4h else 0,
                    "atr_3_4h": atr3_4h if atr3_4h else 0,
                    "atr_14_4h": atr14_4h if atr14_4h else 0,
                    "volume_current_4h": volume_current_4h,
                    "volume_average_4h": volume_average_4h,
                    "macd_series_4h": macd_series_4h,
                    "rsi14_series_4h": rsi14_series_4h
                }
                data_source = "生产环境" if len(klines_4h) >= 50 else "测试环境"
                print(f"[INFO] {data_source}包含长期背景数据: {len(klines_4h)}个4小时K线")
            else:
                print(f"[INFO] 跳过长期背景数据: 仅{len(klines_4h)}个4小时K线（需要>=20个）")

            return result

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

        # 返回基本数据，不生成任何模拟序列或长期背景
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
            # 添加当前指标值
            "current_ema20": current_price,
            "current_macd": 0.0,
            "current_rsi7": 50.0,
            "indicators": indicators
            # 注意：不包含long_term_1h字段（避免误导AI）
        }

    def _calculate_ema_series(self, prices: List[float], period: int) -> List[float]:
        """计算EMA序列（需要足够的历史数据）"""
        if len(prices) == 0:
            return []

        if len(prices) < period:
            # 数据不足时，返回空列表并记录警告，不使用填充数据
            print(f"[WARNING] EMA计算需要至少{period}个数据点，但只有{len(prices)}个数据，建议增加历史数据获取量")
            return [0.0] * len(prices)  # 返回0值数组，明确表示数据不足

        df = pd.DataFrame({'close': prices})
        ema = df['close'].ewm(span=period, adjust=False).mean()
        return ema.tolist()

    def _calculate_macd_series(self, prices: List[float]) -> List[float]:
        """计算MACD序列（需要足够的历史数据）"""
        if len(prices) == 0:
            return []

        # MACD需要26个数据点
        if len(prices) < 26:
            print(f"[WARNING] MACD计算需要至少26个数据点，但只有{len(prices)}个数据，建议增加历史数据获取量")
            return [0.0] * len(prices)

        df = pd.DataFrame({'close': prices})
        ema_12 = df['close'].ewm(span=12, adjust=False).mean()
        ema_26 = df['close'].ewm(span=26, adjust=False).mean()
        macd_line = ema_12 - ema_26
        return macd_line.tolist()

    def _calculate_rsi_series(self, prices: List[float], period: int) -> List[float]:
        """计算RSI序列（需要足够的历史数据）"""
        if len(prices) == 0:
            return []

        # RSI需要period+1个数据点
        if len(prices) < period + 1:
            print(f"[WARNING] RSI计算需要至少{period+1}个数据点，但只有{len(prices)}个数据，建议增加历史数据获取量")
            return [50.0] * len(prices)  # 返回中性值

        df = pd.DataFrame({'close': prices})
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        # 处理除零情况
        rs = gain / (loss.replace(0, 1e-10))
        rsi = 100 - (100 / (1 + rs))

        # 处理无效值
        rsi = rsi.fillna(50.0).replace([float('inf'), float('-inf')], 50.0)
        return rsi.tolist()

    def _calculate_atr(self, highs: List[float], lows: List[float], closes: List[float], period: int) -> float:
        """计算ATR（修复版本：数据不足时也计算合理ATR）"""
        if len(highs) == 0 or len(lows) == 0 or len(closes) == 0:
            return 0.0

        # 如果数据不足，扩展到period+1个点
        if len(highs) < period + 1 or len(lows) < period + 1 or len(closes) < period + 1:
            # 找到最大的列表长度
            max_len = max(len(highs), len(lows), len(closes))
            target_len = period + 1

            # 用最后一个有效值填充缺失的数据
            extended_highs = highs + [highs[-1] if highs else 0] * (target_len - len(highs))
            extended_lows = lows + [lows[-1] if lows else 0] * (target_len - len(lows))
            extended_closes = closes + [closes[-1] if closes else 0] * (target_len - len(closes))
        else:
            extended_highs = highs
            extended_lows = lows
            extended_closes = closes

        # 计算True Range（使用扩展后的数据）
        high_low = [h - l for h, l in zip(extended_highs[1:], extended_lows[1:])]
        high_close = [abs(h - c) for h, c in zip(extended_highs[1:], extended_closes[:-1])]
        low_close = [abs(l - c) for l, c in zip(extended_lows[1:], extended_closes[:-1])]

        tr = [max(hl, hc, lc) for hl, hc, lc in zip(high_low, high_close, low_close)]

        # 计算ATR（确保有足够的数据）
        if len(tr) >= period:
            atr = sum(tr[:period]) / period
            return atr
        elif len(tr) > 0:
            # 即使数据不足，也返回可用的平均值
            return sum(tr) / len(tr)
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
