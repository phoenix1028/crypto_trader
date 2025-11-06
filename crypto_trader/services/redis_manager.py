#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Redis管理器 - 事件驱动交易系统的数据存储
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import redis
import json
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
from redis.exceptions import RedisError, ConnectionError
from configs.config import Config, RedisKeys


class RedisManager:
    """Redis管理器 - 负责所有Redis数据操作"""

    def __init__(self, connection_url: Optional[str] = None):
        """
        初始化Redis连接

        Args:
            connection_url: Redis连接URL，如果为None则使用配置默认
        """
        self.connection_url = connection_url or Config.REDIS_URL
        self.redis_client = None
        self.connected = False

        # 连接池配置
        self.connection_pool = redis.ConnectionPool.from_url(
            self.connection_url,
            decode_responses=True,
            health_check_interval=30
        )

        self._connect()

    def _connect(self) -> bool:
        """连接到Redis服务器"""
        try:
            self.redis_client = redis.Redis(connection_pool=self.connection_pool)
            # 测试连接
            self.redis_client.ping()
            self.connected = True
            print(f"[REDIS] 连接成功: {self.connection_url}")
            return True
        except ConnectionError as e:
            print(f"[REDIS] 连接失败: {e}")
            self.connected = False
            return False
        except Exception as e:
            print(f"[REDIS] 连接异常: {e}")
            self.connected = False
            return False

    def reconnect(self) -> bool:
        """重新连接Redis"""
        print("[REDIS] 尝试重新连接...")
        return self._connect()

    def is_connected(self) -> bool:
        """检查Redis连接状态"""
        if not self.connected:
            return False
        try:
            self.redis_client.ping()
            return True
        except:
            self.connected = False
            return False

    # ==================== 市场数据操作 ====================

    def update_market_data(self, symbol: str, data: Dict[str, Any]) -> bool:
        """
        更新市场数据

        Args:
            symbol: 交易对
            data: 市场数据字典
                - price: 当前价格
                - open: 开盘价
                - high: 最高价
                - low: 最低价
                - volume: 成交量
                - interval: K线周期
                - close_time: 收盘时间
                - is_closed: 是否完成

        Returns:
            bool: 更新是否成功
        """
        if not self.is_connected():
            return False

        try:
            key = Config.get_market_data_key(symbol)

            # 添加时间戳
            data['update_time'] = datetime.now().isoformat()
            data['timestamp'] = time.time()

            # 转换布尔值为字符串（Redis不支持布尔值）
            if 'is_closed' in data:
                data['is_closed'] = str(data['is_closed'])

            # 使用pipeline批量更新
            pipe = self.redis_client.pipeline()

            # 更新主数据
            pipe.hset(key, mapping=data)

            # 更新价格提醒信息
            if 'price' in data:
                alerts_key = Config.get_price_alerts_key(symbol)
                pipe.hset(alerts_key, mapping={
                    "last_price": float(data['price']),
                    "last_update": data['update_time']
                })

            pipe.execute()
            return True

        except RedisError as e:
            print(f"[REDIS] 更新市场数据失败: {e}")
            return False

    def get_market_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        获取市场数据

        Args:
            symbol: 交易对

        Returns:
            Dict[str, Any]: 市场数据字典，如果失败返回None
        """
        if not self.is_connected():
            return None

        try:
            key = Config.get_market_data_key(symbol)
            data = self.redis_client.hgetall(key)

            # 转换数值类型
            numeric_fields = ['price', 'open', 'high', 'low', 'volume']
            for field in numeric_fields:
                if field in data:
                    try:
                        data[field] = float(data[field])
                    except (ValueError, TypeError):
                        pass

            return data if data else None

        except RedisError as e:
            print(f"[REDIS] 获取市场数据失败: {e}")
            return None

    def get_all_market_data(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        批量获取市场数据

        Args:
            symbols: 交易对列表

        Returns:
            Dict[str, Dict[str, Any]]: 所有市场数据
        """
        if not self.is_connected():
            return {}

        try:
            # 使用pipeline批量获取
            pipe = self.redis_client.pipeline()
            keys = [Config.get_market_data_key(symbol) for symbol in symbols]

            for key in keys:
                pipe.hgetall(key)

            results = pipe.execute()

            # 组合结果
            all_data = {}
            for i, symbol in enumerate(symbols):
                data = results[i]
                if data:
                    # 转换数值类型
                    numeric_fields = ['price', 'open', 'high', 'low', 'volume']
                    for field in numeric_fields:
                        if field in data:
                            try:
                                data[field] = float(data[field])
                            except (ValueError, TypeError):
                                pass
                    all_data[symbol] = data

            return all_data

        except RedisError as e:
            print(f"[REDIS] 批量获取市场数据失败: {e}")
            return {}

    # ==================== 技术指标操作 ====================

    def update_indicators(self, symbol: str, indicators: Dict[str, Any]) -> bool:
        """
        更新技术指标

        Args:
            symbol: 交易对
            indicators: 技术指标字典
                - rsi_7, rsi_14: RSI指标
                - ema_20, ema_50: EMA指标
                - macd_line, macd_signal, macd_histogram: MACD指标
                - atr_14: ATR指标

        Returns:
            bool: 更新是否成功
        """
        if not self.is_connected():
            return False

        try:
            key = Config.get_indicators_key(symbol)

            # 添加时间戳
            indicators['last_calc'] = datetime.now().isoformat()
            indicators['timestamp'] = time.time()

            self.redis_client.hset(key, mapping=indicators)
            return True

        except RedisError as e:
            print(f"[REDIS] 更新技术指标失败: {e}")
            return False

    def get_indicators(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        获取技术指标

        Args:
            symbol: 交易对

        Returns:
            Dict[str, Any]: 技术指标字典
        """
        if not self.is_connected():
            return None

        try:
            key = Config.get_indicators_key(symbol)
            data = self.redis_client.hgetall(key)

            # 转换数值类型
            numeric_fields = [
                'rsi_7', 'rsi_14', 'ema_20', 'ema_50',
                'macd_line', 'macd_signal', 'macd_histogram', 'atr_14'
            ]
            for field in numeric_fields:
                if field in data:
                    try:
                        data[field] = float(data[field])
                    except (ValueError, TypeError) as e:
                        # 提供更详细的错误信息
                        print(f"[REDIS] 警告：{field}值'{data[field]}'类型转换失败: {e}")
                        # 使用合理的默认值
                        if 'rsi' in field:
                            data[field] = 50.0  # RSI默认值
                        else:
                            data[field] = 0.0   # 其他指标默认值

            return data if data else None

        except RedisError as e:
            print(f"[REDIS] 获取技术指标失败: {e}")
            return None

    # ==================== 账户状态操作 ====================

    def update_account_status(self, account_info: Dict[str, Any]) -> bool:
        """
        更新账户状态

        Args:
            account_info: 账户信息字典
                - total_wallet_balance: 总资产
                - available_cash: 可用现金
                - total_unrealized_pnl: 总未实现盈亏

        Returns:
            bool: 更新是否成功
        """
        if not self.is_connected():
            return False

        try:
            key = Config.get_account_status_key()

            # 添加时间戳
            account_info['last_update'] = datetime.now().isoformat()
            account_info['timestamp'] = time.time()

            self.redis_client.hset(key, mapping=account_info)
            return True

        except RedisError as e:
            print(f"[REDIS] 更新账户状态失败: {e}")
            return False

    def get_account_status(self) -> Optional[Dict[str, Any]]:
        """
        获取账户状态

        Returns:
            Dict[str, Any]: 账户状态字典
        """
        if not self.is_connected():
            return None

        try:
            key = Config.get_account_status_key()
            data = self.redis_client.hgetall(key)

            # 转换数值类型
            numeric_fields = [
                'total_wallet_balance', 'available_cash', 'total_unrealized_pnl',
                'total_margin_balance', 'total_position_initial_margin'
            ]
            for field in numeric_fields:
                if field in data:
                    try:
                        data[field] = float(data[field])
                    except (ValueError, TypeError):
                        pass

            return data if data else None

        except RedisError as e:
            print(f"[REDIS] 获取账户状态失败: {e}")
            return None

    # ==================== 持仓信息操作 ====================

    def update_positions(self, positions: Dict[str, Any]) -> bool:
        """
        更新持仓信息

        Args:
            positions: 持仓信息字典 {symbol: {size, pnl, entry_price, ...}}

        Returns:
            bool: 更新是否成功
        """
        if not self.is_connected():
            return False

        try:
            key = Config.get_positions_key()

            # 将嵌套字典转换为JSON字符串存储
            positions_json = json.dumps(positions, ensure_ascii=False)
            self.redis_client.set(key, positions_json)
            return True

        except RedisError as e:
            print(f"[REDIS] 更新持仓信息失败: {e}")
            return False

    def get_positions(self) -> Optional[Dict[str, Any]]:
        """
        获取持仓信息

        Returns:
            Dict[str, Any]: 持仓信息字典
        """
        if not self.is_connected():
            return None

        try:
            key = Config.get_positions_key()
            positions_json = self.redis_client.get(key)

            if not positions_json:
                return {}

            return json.loads(positions_json)

        except RedisError as e:
            print(f"[REDIS] 获取持仓信息失败: {e}")
            return None

    # ==================== 系统状态操作 ====================

    def update_system_status(self, status: Dict[str, Any]) -> bool:
        """
        更新系统状态

        Args:
            status: 系统状态字典

        Returns:
            bool: 更新是否成功
        """
        if not self.is_connected():
            return False

        try:
            key = Config.get_system_status_key()

            # 添加时间戳
            status['last_heartbeat'] = datetime.now().isoformat()
            status['timestamp'] = time.time()

            self.redis_client.hset(key, mapping=status)
            return True

        except RedisError as e:
            print(f"[REDIS] 更新系统状态失败: {e}")
            return False

    def get_system_status(self) -> Optional[Dict[str, Any]]:
        """
        获取系统状态

        Returns:
            Dict[str, Any]: 系统状态字典
        """
        if not self.is_connected():
            return None

        try:
            key = Config.get_system_status_key()
            data = self.redis_client.hgetall(key)
            return data if data else None

        except RedisError as e:
            print(f"[REDIS] 获取系统状态失败: {e}")
            return None

    # ==================== AI调用统计 ====================

    def increment_ai_call_count(self) -> int:
        """增加AI调用次数（修复版：避免过期时间被重置）"""
        if not self.is_connected():
            return 0

        try:
            key = Config.get_ai_call_count_key()

            # 🔧 修复：检查key是否已存在，如果不存在才设置过期时间
            exists = self.redis_client.exists(key)
            count = self.redis_client.incr(key)

            # 只有第一次设置时才设置过期时间
            if not exists:
                self.redis_client.expire(key, 3600)  # 1小时 = 3600秒，自动重置
                print(f"[REDIS] AI调用计数开始，1小时后自动重置")

            return count

        except RedisError as e:
            print(f"[REDIS] 增加AI调用次数失败: {e}")
            return 0

    def get_ai_call_count(self) -> int:
        """获取AI调用次数"""
        if not self.is_connected():
            return 0

        try:
            key = Config.get_ai_call_count_key()
            count = self.redis_client.get(key)
            return int(count) if count else 0

        except RedisError as e:
            print(f"[REDIS] 获取AI调用次数失败: {e}")
            return 0

    def set_last_ai_call_time(self, timestamp: Optional[float] = None) -> bool:
        """设置上次AI调用时间"""
        if not self.is_connected():
            return False

        try:
            key = Config.get_last_trade_time_key()
            if timestamp is None:
                timestamp = time.time()
            self.redis_client.set(key, timestamp)
            return True

        except RedisError as e:
            print(f"[REDIS] 设置上次AI调用时间失败: {e}")
            return False

    def get_last_ai_call_time(self) -> Optional[float]:
        """获取上次AI调用时间"""
        if not self.is_connected():
            return None

        try:
            key = Config.get_last_trade_time_key()
            timestamp = self.redis_client.get(key)
            return float(timestamp) if timestamp else None

        except RedisError as e:
            print(f"[REDIS] 获取上次AI调用时间失败: {e}")
            return None

    # ==================== 价格提醒操作 ====================

    def update_price_alert(self, symbol: str, price: float) -> bool:
        """
        更新价格提醒

        Args:
            symbol: 交易对
            price: 当前价格

        Returns:
            bool: 更新是否成功
        """
        if not self.is_connected():
            return False

        try:
            key = Config.get_price_alerts_key(symbol)

            # 获取上次价格
            last_price = self.redis_client.hget(key, "last_triggered_price")
            last_price = float(last_price) if last_price else price

            # 计算价格变化
            price_change = abs(price - last_price) / last_price if last_price != 0 else 0

            data = {
                "last_triggered_price": price,
                "last_update": datetime.now().isoformat(),
                "price_change": price_change,
                "volatility_1m": 0.0,  # 将在数据引擎中计算
                "volatility_5m": 0.0   # 将在数据引擎中计算
            }

            self.redis_client.hset(key, mapping=data)
            return True

        except RedisError as e:
            print(f"[REDIS] 更新价格提醒失败: {e}")
            return False

    def get_price_alert(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        获取价格提醒

        Args:
            symbol: 交易对

        Returns:
            Dict[str, Any]: 价格提醒字典
        """
        if not self.is_connected():
            return None

        try:
            key = Config.get_price_alerts_key(symbol)
            data = self.redis_client.hgetall(key)

            # 转换数值类型
            numeric_fields = [
                "last_triggered_price", "price_change", "volatility_1m", "volatility_5m"
            ]
            for field in numeric_fields:
                if field in data:
                    try:
                        data[field] = float(data[field])
                    except (ValueError, TypeError):
                        pass

            return data if data else None

        except RedisError as e:
            print(f"[REDIS] 获取价格提醒失败: {e}")
            return None

    # ==================== 工具方法 ====================

    def cleanup_expired_data(self) -> None:
        """清理过期数据（可选实现）"""
        # 可以实现定期清理历史数据的逻辑
        pass

    def close(self) -> None:
        """关闭Redis连接"""
        if self.redis_client:
            self.redis_client.close()
            print("[REDIS] 连接已关闭")


# 全局Redis管理器实例
redis_manager = RedisManager()


if __name__ == "__main__":
    # 测试Redis管理器
    print("=== Redis管理器测试 ===")

    # 测试连接
    if redis_manager.is_connected():
        print("[OK] Redis连接正常")

        # 测试市场数据更新
        test_data = {
            "price": 107091.62,
            "open": 107000.00,
            "high": 107200.00,
            "low": 106900.00,
            "volume": 1234.56,
            "interval": "1m",
            "is_closed": True
        }

        if redis_manager.update_market_data("BTCUSDT", test_data):
            print("[OK] 市场数据更新成功")

        # 测试获取市场数据
        market_data = redis_manager.get_market_data("BTCUSDT")
        if market_data:
            print(f"[OK] 获取市场数据: {market_data}")

        # 测试AI调用统计
        count = redis_manager.increment_ai_call_count()
        print(f"[OK] AI调用次数: {count}")

        # 测试价格提醒
        redis_manager.update_price_alert("BTCUSDT", 107091.62)
        alert = redis_manager.get_price_alert("BTCUSDT")
        if alert:
            print(f"[OK] 价格提醒: {alert}")

    else:
        print("[ERROR] Redis连接失败，请检查Redis服务是否启动")

    # 关闭连接
    redis_manager.close()
