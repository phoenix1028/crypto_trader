#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
事件驱动交易系统配置管理
"""

import os
from typing import List, Dict, Any
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


class Config:
    """事件驱动交易系统配置类"""

    # === Redis配置 ===
    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")  # WSL环境中的Redis
    REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB = int(os.getenv("REDIS_DB", "0"))
    REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")
    REDIS_URL = os.getenv("REDIS_URL", f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}")

    # === 交易对配置 ===
    TRADING_SYMBOLS = [
        'BTCUSDT', 'ETHUSDT', 'SOLUSDT',
        'BNBUSDT', 'XRPUSDT', 'DOGEUSDT'
    ]

    # === K线周期配置 ===
    KLINE_INTERVALS = ['1m', '3m']

    # === WebSocket配置 ===
    BINANCE_TESTNET = True  # 始终使用测试网
    WEBSOCKET_TIMEOUT = 60
    RECONNECT_INTERVAL = 5

    # === 合约交易配置 ===
    USE_FUTURES = True  # 🔧 重要：AI交易工具使用合约（期货）数据
    FUTURES_TESTNET = True  # 使用期货测试网
    DEFAULT_LEVERAGE = 20  # 默认杠杆倍数
    MARGIN_TYPE = "ISOLATED"  # 保证金模式：ISOLATED（逐仓）或 CROSS（全仓）

    # === 智能触发器配置 ===
    MIN_CALL_INTERVAL = 30 # 最小调用间隔（秒）
    PRICE_VOLATILITY_THRESHOLD = 0.002  # 价格波动阈值（0.2%）
    FALLBACK_INTERVAL = 180 # 兜底间隔（3分钟）
    MAX_AI_CALLS_PER_HOUR = int(os.getenv("MAX_AI_CALLS_PER_HOUR", "1500"))  # 每小时最大AI调用次数（积极交易可适当提高）

    # === 交易策略配置 ===
    # 三层置信度系统 (Alpha Arena v2.0)
    HIGH_CONFIDENCE_THRESHOLD = float(os.getenv("HIGH_CONFIDENCE_THRESHOLD", "0.7"))  # 高置信度：2.5%风险单位
    MEDIUM_CONFIDENCE_THRESHOLD = float(os.getenv("MEDIUM_CONFIDENCE_THRESHOLD", "0.4"))  # 中置信度：1.75%风险单位
    LOW_CONFIDENCE_THRESHOLD = float(os.getenv("LOW_CONFIDENCE_THRESHOLD", "0.3"))  # 低置信度：1%风险单位
    VERY_LOW_CONFIDENCE_THRESHOLD = 0.3  # 极低置信度：无持仓

    MAX_POSITIONS = int(os.getenv("MAX_POSITIONS", "2"))
    LEVERAGE = int(os.getenv("LEVERAGE", "20"))
    STOP_LOSS_PCT = float(os.getenv("STOP_LOSS_PCT", "0.015"))

    # === 系统配置 ===
    AGENT_SIGNATURE = os.getenv("AGENT_SIGNATURE", "crypto_trader_001")
    ENABLE_REAL_TRADING = False  # 默认禁用真实交易
    ENABLE_TECHNICAL_INDICATORS = True
    ENABLE_RISK_MANAGEMENT = True
    ENABLE_NOTIFICATIONS = False

    # === Redis键名规范 ===
    @classmethod
    def get_market_data_key(cls, symbol: str) -> str:
        """获取市场数据Redis键名"""
        return f"MARKET_DATA:{symbol}"

    @classmethod
    def get_indicators_key(cls, symbol: str) -> str:
        """获取技术指标Redis键名"""
        return f"INDICATORS:{symbol}"

    @classmethod
    def get_account_status_key(cls) -> str:
        """获取账户状态Redis键名"""
        return "ACCOUNT_STATUS"

    @classmethod
    def get_positions_key(cls) -> str:
        """获取持仓信息Redis键名"""
        return "POSITIONS"

    @classmethod
    def get_last_trade_time_key(cls) -> str:
        """获取上次交易时间Redis键名"""
        return "LAST_TRADE_TIME"

    @classmethod
    def get_ai_call_count_key(cls) -> str:
        """获取AI调用次数Redis键名"""
        return "AI_CALL_COUNT"

    @classmethod
    def get_price_alerts_key(cls, symbol: str) -> str:
        """获取价格提醒Redis键名"""
        return f"PRICE_ALERTS:{symbol}"

    @classmethod
    def get_system_status_key(cls) -> str:
        """获取系统状态Redis键名"""
        return "SYSTEM:STATUS"

    # === API配置 ===
    @classmethod
    def get_binance_config(cls) -> Dict[str, Any]:
        """获取币安API配置"""
        return {
            "api_key": os.getenv("TESTNET_BINANCE_API_KEY"),
            "api_secret": os.getenv("TESTNET_BINANCE_SECRET_KEY"),
            "testnet": cls.BINANCE_TESTNET,
            "futures": cls.USE_FUTURES  # 🔧 区分现货和期货
        }

    @classmethod
    def get_futures_config(cls) -> Dict[str, Any]:
        """获取期货API配置"""
        return {
            "api_key": os.getenv("TESTNET_BINANCE_API_KEY"),
            "api_secret": os.getenv("TESTNET_BINANCE_SECRET_KEY"),
            "testnet": cls.FUTURES_TESTNET
        }

    @classmethod
    def get_llm_config(cls) -> Dict[str, Any]:
        """获取LLM配置"""
        return {
            "api_key": os.getenv("OPENAI_API_KEY"),
            "base_url": os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com"),
            "model": os.getenv("OPENAI_MODEL", "deepseek-chat")
        }


class RedisKeys:
    """Redis键名常量"""

    # 市场数据
    MARKET_DATA_PREFIX = "MARKET_DATA:"
    INDICATORS_PREFIX = "INDICATORS:"

    # 账户数据
    ACCOUNT_STATUS = "ACCOUNT_STATUS"
    POSITIONS = "POSITIONS"

    # 系统状态
    LAST_TRADE_TIME = "LAST_TRADE_TIME"
    AI_CALL_COUNT = "AI_CALL_COUNT"
    SYSTEM_STATUS = "SYSTEM:STATUS"

    # 价格提醒
    PRICE_ALERTS_PREFIX = "PRICE_ALERTS:"

    @staticmethod
    def get_market_data_key(symbol: str) -> str:
        return f"{RedisKeys.MARKET_DATA_PREFIX}{symbol}"

    @staticmethod
    def get_indicators_key(symbol: str) -> str:
        return f"{RedisKeys.INDICATORS_PREFIX}{symbol}"

    @staticmethod
    def get_price_alerts_key(symbol: str) -> str:
        return f"{RedisKeys.PRICE_ALERTS_PREFIX}{symbol}"


class WebSocketStreams:
    """WebSocket流配置"""

    @classmethod
    def get_kline_streams(cls, symbols: List[str], intervals: List[str]) -> List[str]:
        """获取K线流列表"""
        streams = []
        for symbol in symbols:
            for interval in intervals:
                streams.append(f"{symbol.lower()}@kline_{interval}")
        return streams

    @classmethod
    def get_mark_price_streams(cls, symbols: List[str]) -> List[str]:
        """获取标记价格流列表"""
        return [f"mark@{symbol.lower()}" for symbol in symbols]

    @classmethod
    def get_all_market_streams(cls, symbols: List[str], intervals: List[str]) -> List[str]:
        """获取所有市场数据流"""
        return (
            cls.get_kline_streams(symbols, intervals) +
            cls.get_mark_price_streams(symbols)
        )


if __name__ == "__main__":
    # 测试配置
    print("=== 事件驱动交易系统配置 ===")
    print(f"Redis地址: {Config.REDIS_URL}")
    print(f"交易对: {Config.TRADING_SYMBOLS}")
    print(f"K线周期: {Config.KLINE_INTERVALS}")
    print(f"最小调用间隔: {Config.MIN_CALL_INTERVAL}秒")
    print(f"价格波动阈值: {Config.PRICE_VOLATILITY_THRESHOLD * 100}%")
    print(f"兜底间隔: {Config.FALLBACK_INTERVAL}秒")
    print(f"每小时最大AI调用: {Config.MAX_AI_CALLS_PER_HOUR}次")
    print(f"积极交易置信度: 高>{Config.HIGH_CONFIDENCE_THRESHOLD} 中>{Config.MEDIUM_CONFIDENCE_THRESHOLD} 低>{Config.LOW_CONFIDENCE_THRESHOLD} 极低<{Config.LOW_CONFIDENCE_THRESHOLD}")
    print(f"最大持仓: {Config.MAX_POSITIONS}")
    print(f"杠杆倍数: {Config.LEVERAGE}x")
    print(f"测试网模式: {Config.BINANCE_TESTNET}")

    # 测试WebSocket流
    print("\n=== WebSocket流配置 ===")
    market_streams = WebSocketStreams.get_all_market_streams(
        Config.TRADING_SYMBOLS[:3], Config.KLINE_INTERVALS
    )
    print(f"市场数据流: {market_streams}")

    print("\n=== Redis键名规范 ===")
    print(f"BTCUSDT市场数据: {Config.get_market_data_key('BTCUSDT')}")
    print(f"BTCUSDT技术指标: {Config.get_indicators_key('BTCUSDT')}")
    print(f"账户状态: {Config.get_account_status_key()}")
    print(f"持仓信息: {Config.get_positions_key()}")
