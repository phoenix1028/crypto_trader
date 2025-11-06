#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Agent集成层 - 事件系统与LangGraph Agent的桥梁
负责数据格式转换和Agent调用
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import numpy as np
from datetime import datetime
from typing import Dict, Any, Optional

from configs.config import Config
from services.redis_manager import redis_manager


class AgentIntegration:
    """Agent集成类 - 事件系统与LangGraph Agent的集成层"""

    def __init__(self):
        """初始化Agent集成"""
        self.agent = None
        self.initialized = False
        self.tradeable_symbols = Config.TRADING_SYMBOLS

        print("[AGENT_INTEGRATION] Agent集成层初始化")

    async def initialize(self) -> bool:
        """初始化LangGraph Agent"""
        try:
            # 动态导入，避免循环依赖
            from agent.trading_agent import TradingAgentV3

            # 创建Agent实例
            self.agent = TradingAgentV3()
            self.initialized = True

            print("[AGENT_INTEGRATION] LangGraph Agent初始化成功")
            print(f"[AGENT_INTEGRATION] 支持交易对: {', '.join(self.tradeable_symbols)}")

            return True

        except Exception as e:
            print(f"[AGENT_INTEGRATION] Agent初始化失败: {e}")
            return False

    async def make_trading_decision(self, trigger_symbol: str = None, state_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        异步调用LangGraph Agent进行交易决策

        Args:
            trigger_symbol: 触发决策的交易对（可选）
            state_data: 准备好的状态数据，包含market_data和account_info

        Returns:
            Dict[str, Any]: 决策结果
        """
        if not self.initialized or not self.agent:
            return {
                "success": False,
                "error": "Agent未初始化"
            }

        try:
            print(f"\n[AGENT_INTEGRATION] 调用LangGraph Agent进行决策...")
            print(f"[AGENT_INTEGRATION] 触发交易对: {trigger_symbol or '全部'}")
            print(f"[AGENT_INTEGRATION] 数据状态: {'已准备' if state_data else '未准备'}")

            # 确定要决策的交易对
            decision_symbol = trigger_symbol
            if not decision_symbol and state_data and state_data.get('market_data'):
                decision_symbol = list(state_data['market_data'].keys())[0]

            # 运行Agent决策，传递状态数据
            result = await self.agent.make_trading_decision(decision_symbol, state_data)

            # TradingAgentV3已经返回了正确的格式，直接使用
            decision_result = result

            print(f"[AGENT_INTEGRATION] Agent决策完成，置信度阈值: {Config.CONFIDENCE_THRESHOLD}")

            return decision_result

        except Exception as e:
            print(f"[AGENT_INTEGRATION] Agent决策失败: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e)
            }

    def _convert_agent_result(self, agent_result: Dict[str, Any], trigger_symbol: str = None) -> Dict[str, Any]:
        """
        转换Agent结果为事件系统格式

        Args:
            agent_result: Agent原始结果
            trigger_symbol: 触发交易对

        Returns:
            Dict[str, Any]: 转换后的结果
        """
        try:
            trading_decisions = agent_result.get('trading_decisions', {})
            chain_of_thought = agent_result.get('chain_of_thought', '')
            account_info = agent_result.get('account_info', {})

            # 处理每个交易对的决策
            processed_decisions = {}
            high_confidence_decisions = []

            for symbol, decision in trading_decisions.items():
                signal = decision.get('signal', 'HOLD')
                confidence = float(decision.get('confidence', 0.0))
                quantity = decision.get('quantity', 0.0)
                reasoning = decision.get('reasoning', '')

                # 转换信号格式
                if signal.upper() in ['LONG', 'BUY']:
                    signal = 'BUY'
                elif signal.upper() in ['SHORT', 'SELL']:
                    signal = 'SELL'
                else:
                    signal = 'HOLD'

                processed_decisions[symbol] = {
                    "signal": signal,
                    "confidence": confidence,
                    "quantity": quantity,
                    "reasoning": reasoning,
                    "high_confidence": confidence >= Config.CONFIDENCE_THRESHOLD,
                    "timestamp": datetime.now().isoformat()
                }

                # 记录高置信度决策
                if confidence >= Config.CONFIDENCE_THRESHOLD and signal != 'HOLD':
                    high_confidence_decisions.append({
                        "symbol": symbol,
                        "signal": signal,
                        "confidence": confidence,
                        "quantity": quantity
                    })

            # 构建结果
            result = {
                "success": True,
                "timestamp": datetime.now().isoformat(),
                "trigger_symbol": trigger_symbol,
                "decisions": processed_decisions,
                "high_confidence_decisions": high_confidence_decisions,
                "account_info": {
                    "account_value": account_info.get('account_value', 0.0),
                    "available_cash": account_info.get('available_cash', 0.0)
                },
                "chain_of_thought": chain_of_thought,
                "total_decisions": len(processed_decisions),
                "high_confidence_count": len(high_confidence_decisions)
            }

            return result

        except Exception as e:
            print(f"[AGENT_INTEGRATION] 结果转换失败: {e}")
            return {
                "success": False,
                "error": f"结果转换失败: {e}"
            }

    async def execute_trading_signals(self, decisions: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行交易信号

        Args:
            decisions: 决策结果

        Returns:
            Dict[str, Any]: 执行结果
        """
        try:
            if not decisions.get("success"):
                return {
                    "success": False,
                    "error": "无效的决策结果"
                }

            high_confidence_decisions = decisions.get("high_confidence_decisions", [])
            if not high_confidence_decisions:
                return {
                    "success": True,
                    "message": "没有高置信度决策需要执行"
                }

            print(f"\n[AGENT_INTEGRATION] 执行 {len(high_confidence_decisions)} 个高置信度交易信号")

            # 这里将调用现有的MCP工具执行交易
            # 目前先记录交易信号
            execution_results = []

            for decision in high_confidence_decisions:
                symbol = decision['symbol']
                signal = decision['signal']
                confidence = decision['confidence']
                quantity = decision['quantity']

                print(f"[AGENT_INTEGRATION] 准备执行: {signal} {symbol} (置信度: {confidence:.2f})")

                # 模拟交易执行（实际项目中将调用MCP工具）
                execution_result = {
                    "symbol": symbol,
                    "signal": signal,
                    "confidence": confidence,
                    "quantity": quantity,
                    "status": "pending",  # pending, executed, failed
                    "timestamp": datetime.now().isoformat()
                }

                execution_results.append(execution_result)

            return {
                "success": True,
                "execution_results": execution_results,
                "total_executions": len(execution_results)
            }

        except Exception as e:
            print(f"[AGENT_INTEGRATION] 执行交易信号失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def get_agent_status(self) -> Dict[str, Any]:
        """获取Agent状态"""
        return {
            "initialized": self.initialized,
            "agent_available": self.agent is not None,
            "tradeable_symbols": self.tradeable_symbols,
            "confidence_threshold": Config.CONFIDENCE_THRESHOLD
        }


class DataFormatConverter:
    """数据格式转换器"""

    @staticmethod
    def redis_to_agent_state(redis_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        将Redis数据转换为Agent状态格式

        Args:
            redis_data: Redis中的数据

        Returns:
            Dict[str, Any]: Agent状态格式
        """
        try:
            # 提取市场数据
            market_data = {}
            account_info = {}

            # 处理每个交易对的数据
            for symbol in Config.TRADING_SYMBOLS:
                symbol_data = redis_data.get(f"MARKET_DATA:{symbol}", {})
                indicator_data = redis_data.get(f"INDICATORS:{symbol}", {})

                if symbol_data:
                    market_data[symbol] = {
                        "price": float(symbol_data.get('price', 0)),
                        "volume": float(symbol_data.get('volume', 0)),
                        "open": float(symbol_data.get('open', 0)),
                        "high": float(symbol_data.get('high', 0)),
                        "low": float(symbol_data.get('low', 0)),
                        "indicators": indicator_data
                    }

            # 处理账户信息
            account_data = redis_data.get("ACCOUNT_STATUS", {})
            if account_data:
                account_info = {
                    "account_value": float(account_data.get('total_wallet_balance', 10000)),
                    "available_cash": float(account_data.get('available_cash', 5000)),
                    "positions": redis_data.get("POSITIONS", {})
                }

            # 构建Agent状态
            agent_state = {
                "timestamp": datetime.now(),
                "market_data": market_data,
                "account_info": account_info,
                "trading_decisions": {},
                "chain_of_thought": "",
                "trading_decisions_output": ""
            }

            return agent_state

        except Exception as e:
            print(f"[FORMAT_CONVERTER] Redis到Agent状态转换失败: {e}")
            return {
                "timestamp": datetime.now(),
                "market_data": {},
                "account_info": {},
                "trading_decisions": {},
                "chain_of_thought": "",
                "trading_decisions_output": ""
            }


# 全局Agent集成实例（延迟初始化）
_agent_integration_instance = None

def get_agent_integration():
    """获取全局Agent集成实例（延迟初始化）"""
    global _agent_integration_instance
    if _agent_integration_instance is None:
        _agent_integration_instance = AgentIntegration()
        # 在这里不进行异步初始化，由外部手动调用
    return _agent_integration_instance

# 保持向后兼容
agent_integration = get_agent_integration()


if __name__ == "__main__":
    # 测试Agent集成
    async def test_agent_integration():
        print("=== Agent集成测试 ===")

        # 初始化Agent集成
        if await agent_integration.initialize():
            print("[OK] Agent集成初始化成功")

            # 获取Agent状态
            status = agent_integration.get_agent_status()
            print(f"[OK] Agent状态: {status}")

            # 测试数据转换
            redis_data = {
                "MARKET_DATA:BTCUSDT": {"price": "107091.62", "volume": "1234.56"},
                "INDICATORS:BTCUSDT": {"rsi_14": "45.2", "ema_20": "106800.00"},
                "ACCOUNT_STATUS": {"total_wallet_balance": "10000.00", "available_cash": "5000.00"}
            }

            agent_state = DataFormatConverter.redis_to_agent_state(redis_data)
            print(f"[OK] 数据转换: {len(agent_state['market_data'])} 个交易对")

            # 测试Agent调用
            print("\n测试Agent调用...")
            result = await agent_integration.make_trading_decision("BTCUSDT")

            if result.get("success"):
                print(f"[OK] Agent调用成功")
                print(f"  决策数量: {result['total_decisions']}")
                print(f"  高置信度决策: {result['high_confidence_count']}")
            else:
                print(f"[ERROR] Agent调用失败: {result.get('error')}")

        else:
            print("[ERROR] Agent集成初始化失败")

    # 运行测试
    asyncio.run(test_agent_integration())
