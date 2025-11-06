#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
增强的市场数据获取模块
包含资金费率、持仓量等期货特有数据
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from binance import Client
from dotenv import load_dotenv

load_dotenv()

@dataclass
class FundingRate:
    """资金费率数据"""
    symbol: str
    funding_rate: float
    funding_time: int  # 毫秒时间戳
    next_funding_time: int = 0

@dataclass
class OpenInterest:
    """持仓量数据"""
    symbol: str
    sum_open_interest: float
    sum_open_interest_value: float
    time: int = 0

@dataclass
class EnhancedTechnicalIndicators:
    """增强的技术指标"""
    ema_20: float
    macd: float

    ema_50: Optional[float] = None
    sma_20: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_histogram: Optional[float] = None
    rsi_7: Optional[float] = None
    rsi_14: Optional[float] = None
    rsi_21: Optional[float] = None
    atr_3: Optional[float] = None
    atr_14: Optional[float] = None
    volume_current: Optional[float] = None
    volume_average_20: Optional[float] = None
    volume_average_50: Optional[float] = None
    price_position: Optional[float] = None
    volatility_20: Optional[float] = None

@dataclass
class EnhancedMarketData:
    """增强的市场数据"""
    symbol: str
    timestamp: datetime
    current_price: float
    price_change_24h: float
    price_change_percent_24h: float
    indicators: EnhancedTechnicalIndicators

    price_change_1h: Optional[float] = None
    high_24h: Optional[float] = None
    low_24h: Optional[float] = None
    open_24h: Optional[float] = None
    funding_rate: Optional[FundingRate] = None
    open_interest: Optional[OpenInterest] = None
    order_book_spread: Optional[float] = None
    order_book_bid_depth: Optional[float] = None
    order_book_ask_depth: Optional[float] = None
    market_sentiment: Optional[str] = None

class EnhancedBinanceDataProvider:
    """增强的币安数据提供者"""

    def __init__(self):
        self.api_key = os.getenv('BINANCE_API_KEY')
        self.secret_key = os.getenv('BINANCE_SECRET_KEY')
        self.client = Client(self.api_key, self.secret_key)

    def get_funding_rate(self, symbol: str) -> Optional[FundingRate]:
        """获取资金费率"""
        try:
            response = self.client.futures_mark_price(symbol=symbol)
            funding_rate = float(response.get('lastFundingRate', 0))
            funding_time = int(response.get('lastFundingTime', 0))
            next_funding_time = int(response.get('nextFundingTime', 0))

            return FundingRate(
                symbol=symbol,
                funding_rate=funding_rate,
                funding_time=funding_time,
                next_funding_time=next_funding_time
            )
        except Exception as e:
            print(f"获取{symbol}资金费率失败: {e}")
            return None

    def get_open_interest(self, symbol: str) -> Optional[OpenInterest]:
        """获取持仓量"""
        try:
            # 获取当前持仓量
            response = self.client.futures_open_interest(symbol=symbol)

            # 按照官方币安API /fapi/v1/openInterest 响应字段：
            # {"symbol": "BTCUSDT", "openInterest": "150000.50000000", "time": 1678972799999}
            # 注意时间戳字段是 'time'，同时官方API不提供 openInterestValue 字段
            return OpenInterest(
                symbol=symbol,
                sum_open_interest=float(response['openInterest']),
                sum_open_interest_value=0.0,  # 官方API不提供此字段，设为0
                time=int(response['time'])    # 正确使用 'time' 字段，不是 'timestamp'
            )
        except Exception as e:
            print(f"获取{symbol}持仓量失败: {e}")
            return None

    def get_order_book_metrics(self, symbol: str, limit: int = 20) -> Dict[str, float]:
        """获取订单簿指标"""
        try:
            depth = self.client.get_order_book(symbol=symbol, limit=limit)

            best_bid = float(depth['bids'][0][0])
            best_ask = float(depth['asks'][0][0])
            spread = (best_ask - best_bid) / best_bid

            # 计算买卖盘深度
            bid_volume = sum(float(bid[1]) for bid in depth['bids'][:5])
            ask_volume = sum(float(ask[1]) for ask in depth['asks'][:5])

            return {
                'spread': spread,
                'bid_depth': bid_volume,
                'ask_depth': ask_volume,
                'bid_ask_ratio': bid_volume / ask_volume if ask_volume > 0 else 0
            }
        except Exception as e:
            print(f"获取{symbol}订单簿数据失败: {e}")
            return {}

    def calculate_enhanced_indicators(self, symbol: str, klines: List) -> EnhancedTechnicalIndicators:
        """计算增强的技术指标"""
        df = pd.DataFrame(klines, columns=[
            'open_time', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_asset_volume', 'number_of_trades',
            'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume',
            'ignore'
        ])

        # 转换数据类型
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col])

        indicators = {}

        # EMA
        indicators['ema_20'] = df['close'].ewm(span=20).mean().iloc[-1]
        indicators['ema_50'] = df['close'].ewm(span=50).mean().iloc[-1]

        # SMA
        indicators['sma_20'] = df['close'].rolling(20).mean().iloc[-1]

        # RSI (7, 14, 21)
        for period in [7, 14, 21]:
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs)).iloc[-1]
            indicators[f'rsi_{period}'] = float(rsi)

        # MACD
        exp1 = df['close'].ewm(span=12).mean()
        exp2 = df['close'].ewm(span=26).mean()
        macd_line = exp1 - exp2
        signal_line = macd_line.ewm(span=9).mean()
        macd_histogram = macd_line - signal_line

        indicators['macd'] = float(macd_line.iloc[-1])
        indicators['macd_signal'] = float(signal_line.iloc[-1])
        indicators['macd_histogram'] = float(macd_histogram.iloc[-1])

        # ATR (3, 14)
        for period in [3, 14]:
            high_low = df['high'] - df['low']
            high_close = abs(df['high'] - df['close'].shift())
            low_close = abs(df['low'] - df['close'].shift())
            tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            atr = tr.rolling(window=period).mean().iloc[-1]
            indicators[f'atr_{period}'] = float(atr)

        # 成交量指标
        indicators['volume_current'] = float(df['volume'].iloc[-1])
        indicators['volume_average_20'] = float(df['volume'].tail(20).mean())
        indicators['volume_average_50'] = float(df['volume'].tail(50).mean())

        # 价格位置 (在20周期高低点中的位置)
        high_20 = df['high'].rolling(20).max().iloc[-1]
        low_20 = df['low'].rolling(20).min().iloc[-1]
        current_price = float(df['close'].iloc[-1])
        price_position = (current_price - low_20) / (high_20 - low_20) if (high_20 - low_20) > 0 else 0.5
        indicators['price_position'] = float(price_position)

        # 波动率 (20周期标准差)
        indicators['volatility_20'] = float(df['close'].tail(20).std())

        return EnhancedTechnicalIndicators(**indicators)

    def analyze_market_sentiment(self, data: EnhancedMarketData) -> str:
        """分析市场情绪"""
        indicators = data.indicators
        sentiment_score = 0

        # 价格趋势
        if data.price_change_percent_24h > 2:
            sentiment_score += 2
        elif data.price_change_percent_24h > 0:
            sentiment_score += 1
        elif data.price_change_percent_24h < -2:
            sentiment_score -= 2
        elif data.price_change_percent_24h < 0:
            sentiment_score -= 1

        # RSI
        if indicators.rsi_7 and indicators.rsi_7 > 70:
            sentiment_score -= 1  # 超买
        elif indicators.rsi_7 and indicators.rsi_7 < 30:
            sentiment_score += 1  # 超卖

        # MACD
        if indicators.macd and indicators.macd > 0 and indicators.macd_histogram and indicators.macd_histogram > 0:
            sentiment_score += 1  # 多头
        elif indicators.macd and indicators.macd < 0 and indicators.macd_histogram and indicators.macd_histogram < 0:
            sentiment_score -= 1  # 空头

        # 价格位置
        if indicators.price_position and indicators.price_position > 0.8:
            sentiment_score -= 0.5  # 高位
        elif indicators.price_position and indicators.price_position < 0.2:
            sentiment_score += 0.5  # 低位

        if sentiment_score > 1:
            return "BULLISH"
        elif sentiment_score < -1:
            return "BEARISH"
        else:
            return "NEUTRAL"

    def get_enhanced_market_data(self, symbol: str) -> EnhancedMarketData:
        """获取增强的市场数据"""
        # 获取3分钟K线数据
        klines_3m = self.client.get_klines(
            symbol=symbol,
            interval='3m',
            limit=50  # 需要足够的K线数据
        )

        # 计算技术指标（基于3分钟K线）
        indicators = self.calculate_enhanced_indicators(symbol, klines_3m)

        # 获取价格数据
        ticker = self.client.get_ticker(symbol=symbol)
        current_price = float(ticker['lastPrice'])
        price_change_24h = float(ticker['priceChange'])
        price_change_percent_24h = float(ticker['priceChangePercent'])
        high_24h = float(ticker['highPrice'])
        low_24h = float(ticker['lowPrice'])
        open_24h = float(ticker['openPrice'])

        # 获取资金费率
        funding_rate = self.get_funding_rate(symbol)

        # 获取持仓量
        open_interest = self.get_open_interest(symbol)

        # 获取订单簿指标
        book_metrics = self.get_order_book_metrics(symbol)

        # 创建市场数据对象
        market_data = EnhancedMarketData(
            symbol=symbol,
            timestamp=datetime.now(),
            current_price=current_price,
            price_change_24h=price_change_24h,
            price_change_percent_24h=price_change_percent_24h,
            high_24h=high_24h,
            low_24h=low_24h,
            open_24h=open_24h,
            indicators=indicators,
            funding_rate=funding_rate,
            open_interest=open_interest,
            order_book_spread=book_metrics.get('spread'),
            order_book_bid_depth=book_metrics.get('bid_depth'),
            order_book_ask_depth=book_metrics.get('ask_depth')
        )

        # 分析市场情绪
        market_data.market_sentiment = self.analyze_market_sentiment(market_data)

        return market_data

    def batch_get_market_data(self, symbols: List[str]) -> Dict[str, EnhancedMarketData]:
        """批量获取市场数据"""
        results = {}
        for symbol in symbols:
            try:
                results[symbol] = self.get_enhanced_market_data(symbol)
            except Exception as e:
                print(f"获取{symbol}数据失败: {e}")
        return results

def test_enhanced_data_provider():
    """测试增强的数据提供者"""
    provider = EnhancedBinanceDataProvider()

    # 获取BTCUSDT的增强数据
    btc_data = provider.get_enhanced_market_data('BTCUSDT')

    print("=" * 60)
    print(f"BTCUSDT 增强市场数据 - {btc_data.timestamp}")
    print("=" * 60)

    print(f"\n价格信息:")
    print(f"  当前价格: ${btc_data.current_price:,.2f}")
    print(f"  24h涨跌: {btc_data.price_change_percent_24h:+.2f}%")
    print(f"  24h最高: ${btc_data.high_24h:,.2f}")
    print(f"  24h最低: ${btc_data.low_24h:,.2f}")

    print(f"\n技术指标:")
    print(f"  EMA20: ${btc_data.indicators.ema_20:,.2f}")
    print(f"  EMA50: ${btc_data.indicators.ema_50:,.2f}")
    print(f"  MACD: {btc_data.indicators.macd:.2f}")
    print(f"  RSI(7): {btc_data.indicators.rsi_7:.2f}")
    print(f"  RSI(14): {btc_data.indicators.rsi_14:.2f}")
    print(f"  ATR(14): ${btc_data.indicators.atr_14:.2f}")
    print(f"  价格位置: {btc_data.indicators.price_position:.2%}")

    print(f"\n期货数据:")
    if btc_data.funding_rate:
        print(f"  资金费率: {btc_data.funding_rate.funding_rate:.6f}")
    if btc_data.open_interest:
        print(f"  持仓量: {btc_data.open_interest.sum_open_interest:,.0f}")

    print(f"\n订单簿:")
    print(f"  买卖价差: {btc_data.order_book_spread:.6f}")

    print(f"\n市场情绪: {btc_data.market_sentiment}")

if __name__ == "__main__":
    test_enhanced_data_provider()
