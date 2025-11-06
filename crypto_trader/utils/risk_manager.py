#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
动态风险管理模块
基于市场条件动态调整止盈止损和置信度
参考Alpha Arena AI交易项目
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import math
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from utils.market_data import EnhancedMarketData

@dataclass
class RiskMetrics:
    """风险指标"""
    volatility: float
    atr_percentile: float  # ATR在历史中的百分位
    volume_ratio: float  # 当前成交量/平均成交量
    price_momentum: float  # 价格动量
    trend_strength: float  # 趋势强度 0-1
    sentiment_score: float  # 市场情绪评分 0-1

class RiskLevel(Enum):
    """风险等级"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    EXTREME = 4

@dataclass
class TradeSetup:
    """交易设置"""
    symbol: str
    side: str  # LONG or SHORT
    entry_price: float
    quantity: float
    leverage: int
    confidence: float
    risk_usd: float
    profit_target: float
    stop_loss: float
    trailing_stop: Optional[float] = None
    invalidation_condition: str = ""
    risk_level: RiskLevel = RiskLevel.MEDIUM

class RiskManager:
    """动态风险管理器"""

    def __init__(self, account_value: float):
        self.account_value = account_value
        self.max_risk_percent = 0.05  # 最大单笔风险5%
        self.max_positions = 2  # 最大持仓数
        self.leverage_range = (5, 40)  # 杠杆范围

    def calculate_risk_metrics(self, market_data: EnhancedMarketData) -> RiskMetrics:
        """计算风险指标"""
        indicators = market_data.indicators

        # 波动率 (基于价格标准差)
        volatility = indicators.volatility_20 or 0.02

        # ATR百分位 (简化版，使用当前ATR与历史均值比较)
        atr_ratio = indicators.atr_14 / market_data.current_price
        atr_percentile = min(atr_ratio * 100, 100)  # 简化计算

        # 成交量比率
        volume_ratio = 1.0
        if indicators.volume_average_20:
            volume_ratio = indicators.volume_current / indicators.volume_average_20

        # 价格动量 (基于MACD)
        momentum = 0.5  # 默认中性
        if indicators.macd and indicators.macd_histogram:
            # MACD柱状图为正且增大 → 看涨动量
            if indicators.macd_histogram > 0:
                momentum = min(indicators.macd_histogram * 2, 1.0)
            else:
                momentum = max(1 + indicators.macd_histogram * 2, 0)

        # 趋势强度 (基于价格与EMA的关系)
        trend_strength = 0.5  # 默认中性
        if indicators.ema_20 and indicators.ema_50:
            price_above_ema20 = market_data.current_price / indicators.ema_20 - 1
            price_above_ema50 = market_data.current_price / indicators.ema_50 - 1

            # 价格在均线之上且均线向上，趋势强
            if price_above_ema20 > 0 and price_above_ema50 > 0:
                trend_strength = min(0.7 + (price_above_ema20 + price_above_ema50) / 2, 1.0)
            # 价格在均线之下且均线向下，趋势强
            elif price_above_ema20 < 0 and price_above_ema50 < 0:
                trend_strength = min(0.7 + abs((price_above_ema20 + price_above_ema50)) / 2, 1.0)

        # 市场情绪评分
        sentiment_score = 0.5
        if market_data.market_sentiment == "BULLISH":
            sentiment_score = 0.7
        elif market_data.market_sentiment == "BEARISH":
            sentiment_score = 0.3

        # 结合资金费率
        if market_data.funding_rate:
            funding_rate = market_data.funding_rate.funding_rate
            if funding_rate > 0.0001:  # 高资金费率做多成本高
                sentiment_score *= 0.8

        return RiskMetrics(
            volatility=volatility,
            atr_percentile=atr_percentile,
            volume_ratio=volume_ratio,
            price_momentum=momentum,
            trend_strength=trend_strength,
            sentiment_score=sentiment_score
        )

    def calculate_dynamic_confidence(self, market_data: EnhancedMarketData, trade_direction: str) -> float:
        """动态计算置信度"""
        metrics = self.calculate_risk_metrics(market_data)
        base_confidence = 0.5

        # 基于RSI调整
        rsi = market_data.indicators.rsi_7 or 50
        rsi_factor = 0.5
        if trade_direction == "LONG":
            # 做多: RSI中等(30-70)置信度高
            if 30 <= rsi <= 70:
                rsi_factor = 0.8 + (50 - abs(rsi - 50)) / 50 * 0.2
            else:
                rsi_factor = 0.4
        else:
            # 做空: RSI中等(30-70)置信度高
            if 30 <= rsi <= 70:
                rsi_factor = 0.8 + (50 - abs(rsi - 50)) / 50 * 0.2
            else:
                rsi_factor = 0.4

        # 基于价格位置调整
        position = market_data.indicators.price_position or 0.5
        position_factor = 0.5
        if 0.2 <= position <= 0.8:
            # 价格在中间区域，置信度高
            position_factor = 0.8

        # 基于趋势强度调整
        trend_factor = metrics.trend_strength

        # 基于成交量调整
        volume_factor = 0.5
        if metrics.volume_ratio > 1.2:
            volume_factor = 0.8  # 高成交量
        elif metrics.volume_ratio < 0.8:
            volume_factor = 0.6  # 低成交量

        # 基于市场情绪调整
        sentiment_factor = metrics.sentiment_score

        # 综合计算置信度
        confidence = (
            base_confidence * 0.2 +
            rsi_factor * 0.3 +
            position_factor * 0.2 +
            trend_factor * 0.1 +
            volume_factor * 0.1 +
            sentiment_factor * 0.1
        )

        # 应用波动率惩罚
        if metrics.volatility > 0.05:  # 高波动率
            confidence *= 0.9
        elif metrics.volatility < 0.02:  # 低波动率
            confidence *= 1.1

        # 限制在合理范围内
        return max(0.1, min(0.95, confidence))

    def calculate_position_size(self, market_data: EnhancedMarketData, leverage: int, confidence: float, risk_per_trade: float) -> float:
        """计算仓位大小"""
        # 风险金额
        risk_amount = self.account_value * risk_per_trade

        # 基于置信度调整风险
        risk_multiplier = confidence
        adjusted_risk = risk_amount * risk_multiplier

        # 计算止损距离
        atr = market_data.indicators.atr_14 or (market_data.current_price * 0.02)
        stop_distance = atr * 1.5  # 1.5倍ATR作为止损距离

        # 计算仓位大小
        # 风险金额 = 仓位大小 * 止损距离 * 杠杆
        position_size = adjusted_risk / (stop_distance * leverage)

        # 返回数量
        quantity = position_size / market_data.current_price
        return min(quantity, self.account_value / market_data.current_price * 0.1)  # 限制最大10%

    def calculate_stop_loss(self, market_data: EnhancedMarketData, entry_price: float, side: str, quantity: float, leverage: int) -> float:
        """计算止损价格"""
        atr = market_data.indicators.atr_14 or (entry_price * 0.02)

        # 基于ATR计算止损距离
        stop_distance = atr * 1.5

        if side == "LONG":
            stop_price = entry_price - stop_distance
        else:
            stop_price = entry_price + stop_distance

        # 确保止损在合理范围
        max_loss_percent = 0.015  # 最大损失1.5%
        max_stop_distance = entry_price * max_loss_percent
        final_stop_distance = min(stop_distance, max_stop_distance)

        if side == "LONG":
            return entry_price - final_stop_distance
        else:
            return entry_price + final_stop_distance

    def calculate_profit_target(self, market_data: EnhancedMarketData, entry_price: float, side: str, stop_loss: float) -> float:
        """计算止盈价格"""
        # 风险回报比 1:3
        risk = abs(entry_price - stop_loss)

        if side == "LONG":
            return entry_price + risk * 3
        else:
            return entry_price - risk * 3

    def generate_invalidation_condition(self, market_data: EnhancedMarketData, side: str, entry_price: float) -> str:
        """生成失效条件"""
        indicators = market_data.indicators

        if side == "LONG":
            # 多头失效条件
            invalidation_base = entry_price * 0.03  # 3%

            if indicators.rsi_7 and indicators.rsi_7 < 30:
                # RSI超卖时，失效条件放宽
                return f"close_price < {entry_price - invalidation_base * 0.5:.2f}"
            else:
                return f"close_price < {entry_price - invalidation_base:.2f}"
        else:
            # 空头失效条件
            invalidation_base = entry_price * 0.03

            if indicators.rsi_7 and indicators.rsi_7 > 70:
                # RSI超买时，失效条件放宽
                return f"close_price > {entry_price + invalidation_base * 0.5:.2f}"
            else:
                return f"close_price > {entry_price + invalidation_base:.2f}"

    def calculate_dynamic_leverage(self, market_data: EnhancedMarketData, confidence: float, risk_level: RiskLevel) -> int:
        """动态杠杆计算"""
        base_leverage = 20  # 基础杠杆

        # 基于置信度调整
        if confidence > 0.8:
            leverage = min(base_leverage * 1.2, 40)
        elif confidence < 0.5:
            leverage = max(base_leverage * 0.8, 5)
        else:
            leverage = base_leverage

        # 基于波动率调整
        volatility = market_data.indicators.volatility_20 or 0.02
        if volatility > 0.05:  # 高波动率
            leverage *= 0.7
        elif volatility < 0.02:  # 低波动率
            leverage *= 1.2

        # 基于风险等级调整
        if risk_level == RiskLevel.HIGH:
            leverage *= 0.8
        elif risk_level == RiskLevel.LOW:
            leverage *= 1.1

        return int(max(self.leverage_range[0], min(self.leverage_range[1], leverage)))

    def create_trade_setup(self, market_data: EnhancedMarketData, side: str, target_confidence: float = 0.7) -> TradeSetup:
        """创建交易设置"""
        current_price = market_data.current_price

        # 动态置信度
        confidence = self.calculate_dynamic_confidence(market_data, side)

        # 风险等级
        if confidence > 0.8:
            risk_level = RiskLevel.LOW
        elif confidence > 0.6:
            risk_level = RiskLevel.MEDIUM
        elif confidence > 0.4:
            risk_level = RiskLevel.HIGH
        else:
            risk_level = RiskLevel.EXTREME

        # 动态杠杆
        leverage = self.calculate_dynamic_leverage(market_data, confidence, risk_level)

        # 仓位大小
        position_size = self.calculate_position_size(
            market_data, leverage, confidence, self.max_risk_percent
        )

        # 计算交易金额
        trade_value = position_size * current_price

        # 风险金额
        risk_usd = min(
            self.account_value * self.max_risk_percent,
            self.account_value * 0.02  # 保守上限2%
        )

        # 止损止盈
        stop_loss = self.calculate_stop_loss(market_data, current_price, side, position_size, leverage)
        profit_target = self.calculate_profit_target(market_data, current_price, side, stop_loss)

        # 失效条件
        invalidation_condition = self.generate_invalidation_condition(market_data, side, current_price)

        return TradeSetup(
            symbol=market_data.symbol,
            side=side,
            entry_price=current_price,
            quantity=position_size,
            leverage=leverage,
            confidence=confidence,
            risk_usd=risk_usd,
            profit_target=profit_target,
            stop_loss=stop_loss,
            invalidation_condition=invalidation_condition,
            risk_level=risk_level
        )

    def evaluate_existing_position(self, market_data: EnhancedMarketData, position_size: float, entry_price: float) -> Dict[str, Any]:
        """评估现有持仓"""
        current_price = market_data.current_price
        side = "LONG" if position_size > 0 else "SHORT"

        # 持仓盈亏
        pnl = (current_price - entry_price) * position_size
        pnl_percent = pnl / (abs(position_size) * entry_price) * 100

        # 检查失效条件
        invalidation_triggered = False
        atr = market_data.indicators.atr_14 or (entry_price * 0.02)

        if side == "LONG":
            if current_price < entry_price * 0.97:  # 跌破3%
                invalidation_triggered = True
        else:
            if current_price > entry_price * 1.03:  # 涨超3%
                invalidation_triggered = True

        # 是否需要减仓
        should_reduce = False
        reduce_reason = ""

        if pnl_percent < -3:  # 亏损超过3%
            should_reduce = True
            reduce_reason = "亏损超过3%"

        if side == "LONG" and market_data.indicators.rsi_7 and market_data.indicators.rsi_7 > 80:
            should_reduce = True
            reduce_reason = "RSI超买"

        if side == "SHORT" and market_data.indicators.rsi_7 and market_data.indicators.rsi_7 < 20:
            should_reduce = True
            reduce_reason = "RSI超卖"

        return {
            "side": side,
            "pnl": pnl,
            "pnl_percent": pnl_percent,
            "invalidation_triggered": invalidation_triggered,
            "should_reduce": should_reduce,
            "reduce_reason": reduce_reason,
            "recommendation": "HOLD" if not invalidation_triggered and not should_reduce else "REDUCE_OR_CLOSE"
        }

def test_risk_manager():
    """测试风险管理器"""
    # 这里需要模拟市场数据
    # 在实际使用时，应该从BinanceDataProvider获取真实数据
    print("RiskManager测试需要在实际市场数据上运行")

if __name__ == "__main__":
    test_risk_manager()
