#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
智能触发器 - 控制AI调用时机
基于事件驱动模式，只有在必要时才调用AI进行决策
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import numpy as np
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from configs.config import Config
from services.redis_manager import redis_manager


class SmartTrigger:
    """智能触发器 - 智能控制AI调用时机"""

    def __init__(self):
        """初始化智能触发器"""
        self.min_interval = Config.MIN_CALL_INTERVAL  # 最小调用间隔（秒）
        self.price_threshold = Config.PRICE_VOLATILITY_THRESHOLD  # 价格波动阈值
        self.fallback_interval = Config.FALLBACK_INTERVAL  # 兜底间隔（秒）

        # 价格历史缓存（内存缓存，用于快速计算）
        self.price_history: Dict[str, List[Tuple[float, float]]] = {}  # symbol: [(timestamp, price), ...]

        # 系统状态
        self.last_ai_call_time = self._get_last_ai_call_time()
        self.trigger_count = 0

        print(f"[SMART_TRIGGER] 智能触发器初始化完成")
        print(f"[SMART_TRIGGER] 最小调用间隔: {self.min_interval}秒")
        print(f"[SMART_TRIGGER] 价格波动阈值: {self.price_threshold * 100}%")
        print(f"[SMART_TRIGGER] 兜底间隔: {self.fallback_interval}秒")

    def should_trigger_decision(self, symbol: str, current_price: float) -> bool:
        """
        判断是否应该触发AI决策（修复版：先全局控制，再条件检查）

        Args:
            symbol: 交易对
            current_price: 当前价格

        Returns:
            bool: True=应该触发，False=不应该触发
        """
        now = time.time()

        # 🔧 修复：首先检查全局最小间隔（必须满足）
        if not self._check_min_interval(now):
            # 间隔未到，不触发任何交易对
            self._log_trigger(symbol, current_price, f"最小间隔未到({self.min_interval}秒)", False)
            return False

        # 🔧 修复：间隔已过，检查特定交易对的触发条件（AND关系）
        should_trigger = False
        trigger_reason = ""

        # 条件1：价格波动检查
        if self._check_price_volatility(symbol, current_price):
            should_trigger = True
            trigger_reason = "价格波动超过阈值"

        # 条件2：兜底机制
        elif self._check_fallback_interval(now):
            should_trigger = True
            trigger_reason = "兜底机制触发（长时间未调用）"

        # 条件3：系统状态异常
        elif self._check_system_status():
            should_trigger = True
            trigger_reason = "系统状态异常"

        # 记录触发结果
        if should_trigger:
            self._log_trigger(symbol, current_price, trigger_reason, True)
            return True
        else:
            self._log_trigger(symbol, current_price, "其他条件不满足", False)
            return False

    def _check_min_interval(self, now: float) -> bool:
        """检查最小间隔"""
        if self.last_ai_call_time is None:
            return True

        time_since_last = now - self.last_ai_call_time
        return time_since_last >= self.min_interval

    def _check_price_volatility(self, symbol: str, current_price: float) -> bool:
        """检查价格波动"""
        # 获取上次触发时的价格
        last_price = self._get_last_trigger_price(symbol)
        if last_price is None:
            # 第一次调用，允许触发
            self._update_price_history(symbol, current_price)
            return True

        # 计算价格变化百分比
        if last_price == 0:
            return False

        price_change = abs(current_price - last_price) / last_price

        # 记录价格变化到Redis（供数据分析）
        self._update_price_alert_in_redis(symbol, current_price, price_change)

        # 检查是否超过阈值
        if price_change >= self.price_threshold:
            self._update_price_history(symbol, current_price)
            return True

        return False

    def _check_fallback_interval(self, now: float) -> bool:
        """检查兜底机制"""
        if self.last_ai_call_time is None:
            return True

        time_since_last = now - self.last_ai_call_time
        return time_since_last >= self.fallback_interval

    def _check_system_status(self) -> bool:
        """检查系统状态"""
        try:
            # 检查Redis连接
            if not redis_manager.is_connected():
                print("[SMART_TRIGGER] Redis连接异常，触发决策")
                return True

            # 检查系统状态
            system_status = redis_manager.get_system_status()
            if system_status:
                websocket_status = system_status.get('websocket_status', '')
                if websocket_status != 'connected':
                    print("[SMART_TRIGGER] WebSocket连接异常，触发决策")
                    return True

            # 检查AI调用次数（防止过于频繁）
            ai_call_count = redis_manager.get_ai_call_count()
            if ai_call_count > 120:  # 1小时内超过120次调用（2次/分钟 × 60分钟）
                print(f"[SMART_TRIGGER] AI调用次数过多 ({ai_call_count})，暂停触发")
                print(f"[SMART_TRIGGER] 当前频率: {ai_call_count}次/小时，最大允许: 120次/小时")
                print(f"[SMART_TRIGGER] 等待1小时后Redis自动重置计数器...")
                return False

            return False

        except Exception as e:
            print(f"[SMART_TRIGGER] 系统状态检查失败: {e}")
            return False

    def _get_last_ai_call_time(self) -> Optional[float]:
        """获取上次AI调用时间"""
        return redis_manager.get_last_ai_call_time()

    def _get_last_trigger_price(self, symbol: str) -> Optional[float]:
        """获取上次触发价格"""
        # 先尝试从Redis获取
        price_alert = redis_manager.get_price_alert(symbol)
        if price_alert and 'last_triggered_price' in price_alert:
            return price_alert['last_triggered_price']

        # 如果Redis没有，从内存缓存获取
        if symbol in self.price_history and self.price_history[symbol]:
            return self.price_history[symbol][-1][1]

        return None

    def _update_price_history(self, symbol: str, price: float) -> None:
        """更新价格历史"""
        now = time.time()

        if symbol not in self.price_history:
            self.price_history[symbol] = []

        self.price_history[symbol].append((now, price))

        # 保持历史记录数量（最多保存100个）
        if len(self.price_history[symbol]) > 100:
            self.price_history[symbol] = self.price_history[symbol][-100:]

    def _update_price_alert_in_redis(self, symbol: str, price: float, change: float) -> None:
        """更新Redis中的价格提醒"""
        try:
            redis_manager.update_price_alert(symbol, price)
        except Exception as e:
            print(f"[SMART_TRIGGER] 更新价格提醒失败: {e}")

    def _log_trigger(self, symbol: str, price: float, reason: str, triggered: bool) -> None:
        """记录触发日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        action = "触发" if triggered else "跳过"
        print(f"[SMART_TRIGGER] [{timestamp}] {symbol} @ ${price:.2f} - {action} - {reason}")

    def update_last_ai_call(self) -> None:
        """更新上次AI调用时间"""
        now = time.time()
        self.last_ai_call_time = now

        # 同时更新Redis
        redis_manager.set_last_ai_call_time(now)

        # 更新Redis中的AI调用计数
        count = redis_manager.increment_ai_call_count()

        self.trigger_count += 1

        print(f"[SMART_TRIGGER] 记录AI调用 #{self.trigger_count}, 总调用次数: {count}")

    def get_trigger_statistics(self) -> Dict[str, Any]:
        """获取触发统计信息"""
        now = time.time()

        stats = {
            "total_triggers": self.trigger_count,
            "last_ai_call": self.last_ai_call_time,
            "time_since_last_call": now - self.last_ai_call_time if self.last_ai_call_time else None,
            "ai_call_count": redis_manager.get_ai_call_count(),
            "redis_connected": redis_manager.is_connected()
        }

        # 价格历史统计
        for symbol, history in self.price_history.items():
            if history:
                stats[f"{symbol}_last_price"] = history[-1][1]
                stats[f"{symbol}_price_count"] = len(history)

        return stats

    def reset_statistics(self) -> None:
        """重置统计信息"""
        self.trigger_count = 0
        self.price_history.clear()

        print("[SMART_TRIGGER] 统计信息已重置")

    def check_risk_event(self, event_type: str, event_data: Dict[str, Any]) -> bool:
        """
        检查风控事件（订单成交、止损触发等）

        Args:
            event_type: 事件类型 ('order_filled', 'stop_loss_triggered', etc.)
            event_data: 事件数据

        Returns:
            bool: 是否应该触发风控检查
        """
        # 订单成交事件
        if event_type == 'order_filled':
            symbol = event_data.get('symbol', '')
            side = event_data.get('side', '')
            pnl = event_data.get('pnl', 0)

            print(f"[SMART_TRIGGER] 风控事件: {symbol} {side} 成交, PnL: {pnl}")

            # 如果有重大盈亏，立即触发风控检查
            if abs(pnl) > 100:  # 盈亏超过100 USDT
                print("[SMART_TRIGGER] 重大盈亏，触发风控检查")
                return True

        # 止损触发事件
        elif event_type == 'stop_loss_triggered':
            symbol = event_data.get('symbol', '')
            loss = event_data.get('loss', 0)

            print(f"[SMART_TRIGGER] 风控事件: {symbol} 止损触发，亏损: {loss}")

            # 止损触发后立即检查风险
            return True

        # 账户余额异常
        elif event_type == 'balance_abnormal':
            print("[SMART_TRIGGER] 风控事件: 账户余额异常")
            return True

        return False


class PriceVolatilityAnalyzer:
    """价格波动率分析器"""

    def __init__(self):
        """初始化波动率分析器"""
        self.volatility_history: Dict[str, List[float]] = {}  # symbol: [volatility values]

    def calculate_volatility(self, symbol: str, prices: List[float], period: int = 20) -> float:
        """计算价格波动率（标准差）"""
        if len(prices) < period:
            return 0.0

        # 计算收益率
        returns = [(prices[i] - prices[i-1]) / prices[i-1] for i in range(1, len(prices))]

        if len(returns) < period:
            return 0.0

        # 计算标准差
        volatility = np.std(returns[-period:])
        return float(volatility)

    def update_volatility(self, symbol: str, current_price: float) -> float:
        """更新波动率计算"""
        if symbol not in self.volatility_history:
            self.volatility_history[symbol] = []

        # 添加当前价格到历史
        self.volatility_history[symbol].append(current_price)

        # 保持历史数量
        if len(self.volatility_history[symbol]) > 100:
            self.volatility_history[symbol] = self.volatility_history[symbol][-100:]

        # 计算当前波动率
        volatility = self.calculate_volatility(symbol, self.volatility_history[symbol])

        # 更新到Redis
        price_alert = redis_manager.get_price_alert(symbol)
        if price_alert is None:
            price_alert = {}

        price_alert['volatility_1m'] = volatility  # 简化处理，实际应该是1分钟窗口

        redis_manager.update_price_alert(symbol, current_price)

        return volatility

    def get_volatility(self, symbol: str) -> float:
        """获取当前波动率"""
        if symbol in self.volatility_history and len(self.volatility_history[symbol]) > 1:
            prices = self.volatility_history[symbol]
            return self.calculate_volatility(symbol, prices)
        return 0.0


# 创建全局智能触发器实例
smart_trigger = SmartTrigger()
volatility_analyzer = PriceVolatilityAnalyzer()


if __name__ == "__main__":
    import random

    # 测试智能触发器
    print("=== 智能触发器测试 ===")

    # 模拟价格数据
    test_symbol = "BTCUSDT"
    base_price = 107000.0

    print(f"\n模拟价格变化测试:")

    for i in range(20):
        # 模拟价格波动
        price_change = random.uniform(-0.01, 0.01)  # -1% 到 +1%
        current_price = base_price * (1 + price_change)
        base_price = current_price

        should_trigger = smart_trigger.should_trigger_decision(test_symbol, current_price)

        if should_trigger:
            print(f"  触发AI调用: ${current_price:.2f}")
            smart_trigger.update_last_ai_call()

        # 模拟波动率计算
        volatility = volatility_analyzer.update_volatility(test_symbol, current_price)

        time.sleep(0.1)

    print("\n=== 统计信息 ===")
    stats = smart_trigger.get_trigger_statistics()
    for key, value in stats.items():
        print(f"{key}: {value}")

    print(f"\n{test_symbol} 当前波动率: {volatility_analyzer.get_volatility(test_symbol):.6f}")
