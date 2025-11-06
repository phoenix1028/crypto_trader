#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
事件驱动型AI量化交易系统 - 主协调器
与WebSocket数据流集成，调用LangGraph Agent
"""

import asyncio
import signal
import sys
import os
import concurrent.futures
from datetime import datetime
from typing import Dict, List, Any, Optional

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from configs.config import Config
from core.data_engine import DataEngine
from core.smart_trigger import smart_trigger, volatility_analyzer
from services.redis_manager import redis_manager
from utils.alpha_arena_formatter import AlphaArenaFormatter


class EventDrivenTradingSystem:
    """事件驱动型AI量化交易系统"""

    def __init__(self):
        """初始化事件系统"""
        self.running = False
        self.data_engine = None
        self.agent_integration = None

        # 初始化Alpha Arena格式化器
        self.formatter = AlphaArenaFormatter()

        # 系统状态跟踪
        self.system_status = {
            "start_time": None,
            "last_heartbeat": None,
            "websocket_status": "disconnected",
            "redis_status": "connected" if redis_manager.is_connected() else "disconnected",
            "ai_agent_status": "idle",
            "total_events_processed": 0,
            "ai_decisions_made": 0
        }

        print("=" * 60)
        print("事件驱动型AI量化交易系统")
        print("=" * 60)

    def initialize(self) -> bool:
        """初始化事件系统"""
        try:
            print("[EVENT_SYSTEM] 正在初始化...")

            # 设置系统启动时间
            self.system_status["start_time"] = datetime.now()

            # 1. 初始化数据引擎
            print("\n[1/3] 初始化数据引擎...")
            self.data_engine = DataEngine()
            self.data_engine.set_callbacks(
                on_kline=self._on_kline_update,
                on_account=self._on_account_update,
                on_order=self._on_order_update
            )

            # 2. 初始化Agent集成
            print("\n[2/3] 初始化Agent集成...")
            self._initialize_agent_integration()

            # 3. 初始化系统状态
            print("\n[3/3] 更新系统状态...")
            self._update_system_status()

            print("\n[OK] 事件系统初始化完成")
            return True

        except Exception as e:
            print(f"\n[ERROR] 事件系统初始化失败: {e}")
            return False

    def _initialize_agent_integration(self) -> None:
        """初始化Agent集成（使用线程池执行异步初始化）"""
        try:
            # 导入Agent集成模块
            from core.agent_integration import agent_integration

            # 设置为实例变量
            self.agent_integration = agent_integration

            # 检查是否已经初始化
            if self.agent_integration.initialized:
                print("[EVENT_SYSTEM] LangGraph Agent已初始化")
                return

            # 使用线程池执行异步初始化
            print("[EVENT_SYSTEM] 正在初始化LangGraph Agent...")
            import concurrent.futures

            def run_async_init():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    return loop.run_until_complete(self.agent_integration.initialize())
                finally:
                    loop.close()

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(run_async_init)
                success = future.result()

            if success:
                print("[EVENT_SYSTEM] LangGraph Agent初始化成功")
            else:
                print("[EVENT_SYSTEM] LangGraph Agent初始化失败")
                self.agent_integration = None

        except Exception as e:
            print(f"[EVENT_SYSTEM] Agent集成失败: {e}")
            self.agent_integration = None

    def start(self) -> bool:
        """启动事件系统"""
        try:
            if not self.initialize():
                return False

            print("\n" + "=" * 60)
            print("启动WebSocket数据流监听...")
            print("=" * 60)

            # 启动数据引擎
            if not self.data_engine.start():
                print("[ERROR] 数据引擎启动失败")
                return False

            self.running = True
            self.system_status["start_time"] = datetime.now()
            self.system_status["websocket_status"] = "connected"
            self._update_system_status()

            print("\n" + "=" * 60)
            print("[OK] 事件系统运行中...")
            print("=" * 60)
            print(f"交易对: {', '.join(Config.TRADING_SYMBOLS)}")
            print(f"时间周期: {', '.join(Config.KLINE_INTERVALS)}")
            print(f"最小间隔: {Config.MIN_CALL_INTERVAL}秒")
            print(f"价格波动阈值: {Config.PRICE_VOLATILITY_THRESHOLD * 100}%")
            print(f"兜底间隔: {Config.FALLBACK_INTERVAL}秒")
            print(f"置信度阈值: {Config.CONFIDENCE_THRESHOLD}")
            print("=" * 60)

            # 显示系统状态
            self._show_system_status()

            return True

        except Exception as e:
            print(f"\n[ERROR] 事件系统启动失败: {e}")
            return False

    def _on_kline_update(self, symbol: str, market_data: Dict[str, Any]) -> None:
        """同步处理K线更新（使用create_task启动异步AI调用）"""
        try:
            self.system_status["total_events_processed"] += 1

            # 获取当前价格
            current_price = market_data.get('price', 0)
            if current_price == 0:
                return

            # 更新波动率分析
            volatility = volatility_analyzer.update_volatility(symbol, current_price)

            # 智能触发AI - 使用create_task在后台运行，不await
            if smart_trigger.should_trigger_decision(symbol, current_price):
                task = asyncio.create_task(self._trigger_ai_decision_async(symbol))
                # 不await，让任务在后台运行

            # 显示价格更新
            self._show_price_update(symbol, current_price, market_data.get('volume', 0))

        except Exception as e:
            print(f"[EVENT_SYSTEM] K线更新处理失败: {e}")

    def _on_account_update(self, account_info: Dict[str, Any]) -> None:
        """处理账户更新"""
        try:
            self.system_status["total_events_processed"] += 1

            # 这里可以添加账户变化的处理逻辑

            # 检查风控阈值

        except Exception as e:
            print(f"[EVENT_SYSTEM] 账户更新处理失败: {e}")

    def _on_order_update(self, symbol: str, order_data: Dict[str, Any]) -> None:
        """处理订单更新"""
        try:
            self.system_status["total_events_processed"] += 1

            order_status = order_data.get('X', '')
            if order_status == 'FILLED':
                # 订单成交后触发风控检查
                self._check_risk_after_order(symbol, order_data)

        except Exception as e:
            print(f"[EVENT_SYSTEM] 订单更新处理失败: {e}")

    async def _trigger_ai_decision_async(self, symbol: str) -> None:
        """异步触发AI决策"""
        try:
            print(f"\n[AI决策] 触发AI分析: {symbol}")

            # 更新智能触发器
            smart_trigger.update_last_ai_call()

            # 更新系统状态
            self.system_status["ai_agent_status"] = "thinking"
            self.system_status["ai_decisions_made"] += 1

            # 调用LangGraph Agent
            await self._call_langgraph_agent_async(symbol)

        except Exception as e:
            print(f"[EVENT_SYSTEM] AI决策触发失败: {e}")
            self.system_status["ai_agent_status"] = "error"

    async def _call_langgraph_agent_async(self, symbol: str) -> None:
        """调用LangGraph Agent"""
        try:
            if not self.agent_integration:
                print("[EVENT_SYSTEM] Agent集成未初始化")
                self.system_status["ai_agent_status"] = "error"
                return

            print(f"[EVENT_SYSTEM] 调用LangGraph Agent {symbol}...")

            # 1. 准备数据（从Redis获取）
            state_data = await self._prepare_state_data(symbol)

            if not state_data or not state_data.get('market_data'):
                print("[EVENT_SYSTEM] 无法获取市场数据，跳过决策")
                self.system_status["ai_agent_status"] = "idle"
                return

            # 2. 传递准备好的数据给Agent
            decision_result = await self.agent_integration.make_trading_decision(symbol, state_data)

            if decision_result.get("success"):
                # 处理Agent决策结果（异步调用）
                await self._process_agent_decision(decision_result)
            else:
                print(f"[EVENT_SYSTEM] Agent调用失败: {decision_result.get('error')}")

            self.system_status["ai_agent_status"] = "idle"

        except Exception as e:
            print(f"[EVENT_SYSTEM] LangGraph Agent调用失败: {e}")
            self.system_status["ai_agent_status"] = "error"

    async def _prepare_state_data(self, symbol: str) -> Dict[str, Any]:
        """准备状态数据（从Redis和市场数据提供者获取）"""
        try:
            market_data = {}

            # 首先尝试从Redis获取市场数据
            for sym in Config.TRADING_SYMBOLS:
                price_data = redis_manager.get_market_data(sym)
                if price_data:
                    # 获取真实计算的技术指标（修复：不再硬编码）
                    indicators_data = redis_manager.get_indicators(sym) or {}

                    # 🔧 修复：字段名映射 - Redis使用'macd_line'，AI期望'macd'
                    market_data[sym] = {
                        "symbol": sym,
                        "current_price": price_data.get('price', 0),
                        "price_change_percent_24h": price_data.get('price_change_percent_24h', 0),
                        "high_24h": price_data.get('high', 0),
                        "low_24h": price_data.get('low', 0),
                        "volume": price_data.get('volume', 0),
                        "indicators": {
                            "rsi_14": indicators_data.get('rsi_14', 50.0),
                            "macd": indicators_data.get('macd_line', 0.0),  # AI期望'macd'，Redis存储为'macd_line'
                            "macd_line": indicators_data.get('macd_line', 0.0),  # 保持向后兼容
                            "ema_20": indicators_data.get('ema_20', 0.0),
                            "ema_50": indicators_data.get('ema_50', 0.0),
                            "atr_14": indicators_data.get('atr_14', 0.0),
                            "volume_current": price_data.get('volume', 0.0)
                        },
                        "market_sentiment": "NEUTRAL"
                    }

            # 如果Redis中没有数据，使用市场数据提供者获取实时数据
            if not market_data:
                print("[EVENT_SYSTEM] Redis中无数据，使用实时市场数据")
                try:
                    from utils.market_data import EnhancedBinanceDataProvider
                    data_provider = EnhancedBinanceDataProvider()

                    for sym in Config.TRADING_SYMBOLS:
                        try:
                            data = data_provider.get_enhanced_market_data(sym)

                            # 🔧 修复：字段名映射 - EnhancedBinanceDataProvider使用'macd'，AI也期望'macd'
                            market_data[sym] = {
                                "symbol": sym,
                                "current_price": data.current_price,
                                "price_change_percent_24h": data.price_change_percent_24h,
                                "high_24h": data.high_24h or 0,
                                "low_24h": data.low_24h or 0,
                                "volume": data.indicators.volume_current or 0,
                                "indicators": {
                                    "rsi_14": data.indicators.rsi_14,  # 移除or 50.0，字段是必需的
                                    "macd": data.indicators.macd,  # EnhancedBinanceDataProvider提供'macd'，AI也期望'macd'
                                    "macd_line": data.indicators.macd,  # 保持向后兼容
                                    "ema_20": data.indicators.ema_20,  # 移除or 0.0，字段是必需的
                                    "ema_50": data.indicators.ema_50 or 0.0,  # Optional字段，可以有or
                                    "atr_14": data.indicators.atr_14,  # 移除or 0.0，字段是必需的
                                    "volume_current": data.indicators.volume_current or 0.0
                                },
                                "market_sentiment": data.market_sentiment or "NEUTRAL"
                            }
                            print(f"  [OK] {sym}: ${data.current_price:,.2f}")
                        except Exception as e:
                            print(f"  [WARNING] 获取{sym}数据失败: {e}")
                            # 使用默认数据
                            market_data[sym] = {
                                "symbol": sym,
                                "current_price": 0,
                                "price_change_percent_24h": 0,
                                "high_24h": 0,
                                "low_24h": 0,
                                "volume": 0,
                                "indicators": {
                                    "rsi_14": 50.0,
                                    "macd": 0.0,
                                    "macd_line": 0.0,  # 统一字段名
                                    "ema_20": 0.0,
                                    "ema_50": 0.0,
                                    "atr_14": 0.0,
                                    "volume_current": 0.0
                                },
                                "market_sentiment": "NEUTRAL"
                            }
                except Exception as e:
                    print(f"  [ERROR] 初始化市场数据提供者失败: {e}")

            # 获取账户信息（从Redis或默认）
            try:
                account_data = redis_manager.get_account_status()
                if account_data:
                    raw_account_info = {
                        "initial_balance": 10000.0,  # 假设初始余额
                        "current_balance": float(account_data.get('total_wallet_balance', 10000)),
                        "available_cash": float(account_data.get('available_cash', 5000)),
                        "positions": account_data.get('positions', [])
                    }
                else:
                    raw_account_info = {
                        "initial_balance": 10000.0,
                        "current_balance": 10000.0,
                        "available_cash": 5000.0,
                        "positions": []
                    }
            except:
                raw_account_info = {
                    "initial_balance": 10000.0,
                    "current_balance": 10000.0,
                    "available_cash": 5000.0,
                    "positions": []
                }

            # 使用Alpha Arena格式化器格式化数据
            formatted_market_data = self.formatter.format_market_data(market_data)
            formatted_account_info = self.formatter.format_account_info(raw_account_info)

            # 生成运行统计（从系统启动时间计算）
            if self.system_status["start_time"]:
                runtime_stats = self.formatter.format_runtime_stats({
                    "start_time": self.system_status["start_time"],
                    "call_count": self.system_status["ai_decisions_made"] + 1
                })
            else:
                runtime_stats = self.formatter.format_runtime_stats({
                    "start_time": datetime.now(),
                    "call_count": 1
                })

            return {
                "market_data": formatted_market_data,
                "account_info": formatted_account_info,
                "runtime_stats": runtime_stats,
                "positions": formatted_account_info.get("positions", [])
            }

        except Exception as e:
            print(f"[EVENT_SYSTEM] 准备状态数据失败: {e}")
            import traceback
            traceback.print_exc()
            return {}

    async def _process_agent_decision(self, decision: Dict[str, Any]) -> None:
        """处理Agent决策结果（异步版本）"""
        try:
            decisions = decision.get('decisions', {})
            high_confidence_decisions = decision.get('high_confidence_decisions', [])
            chain_of_thought = decision.get('chain_of_thought', '')

            print(f"\n[AI决策结果]:")
            print(f"   总决策数: {decision.get('total_decisions', 0)}")
            print(f"   高置信度决策: {decision.get('high_confidence_count', 0)}")

            # 显示所有决策
            for symbol, decision_data in decisions.items():
                signal = decision_data['signal']
                confidence = decision_data['confidence']
                print(f"   {symbol}: {signal} (置信度: {confidence:.2f})")

            # 处理高置信度决策
            if high_confidence_decisions:
                print(f"\n[高置信度信号]:")
                for decision in high_confidence_decisions:
                    symbol = decision['symbol']
                    signal = decision['signal']
                    confidence = decision['confidence']
                    print(f"   {signal} {symbol} (置信度: {confidence:.2f})")

                # 执行交易信号（使用await而不是asyncio.run）
                if self.agent_integration:
                    execution_result = await self.agent_integration.execute_trading_signals(decision)

                    if execution_result.get("success"):
                        print(f"\n[交易执行] 执行成功")
                    else:
                        print(f"\n[交易执行] 执行失败: {execution_result.get('error')}")
            else:
                print(f"\n[暂停] 无高置信度决策信号")

            # 显示AI思考过程
            if chain_of_thought:
                print(f"\n[AI思考过程]:")
                print(chain_of_thought[:300] + "..." if len(chain_of_thought) > 300 else chain_of_thought)

        except Exception as e:
            print(f"[EVENT_SYSTEM] 处理Agent决策失败: {e}")

    def _execute_trading_signal(self, symbol: str, signal: str, confidence: float, decision: Dict[str, Any]) -> None:
        """执行交易信号（待实现MCP工具）"""
        try:
            print(f"[EVENT_SYSTEM] 执行交易: {signal} {symbol}")

            # 这里将调用MCP工具执行交易
            # 暂时跳过

            print(f"[EVENT_SYSTEM] 交易执行待实现")

        except Exception as e:
            print(f"[EVENT_SYSTEM] 交易执行失败: {e}")

    def _check_risk_after_order(self, symbol: str, order_data: Dict[str, Any]) -> None:
        """检查订单后的风险"""
        try:
            # 解析订单信息
            side = order_data.get('S', '')
            quantity = float(order_data.get('q', 0))
            price = float(order_data.get('p', 0))

            print(f"\n[风控检查] {symbol} {side} {quantity} @ {price}")

            # 这里可以添加风险检查逻辑

        except Exception as e:
            print(f"[EVENT_SYSTEM] 风控检查失败: {e}")

    def _update_system_status(self) -> None:
        """更新系统状态到Redis"""
        try:
            status = {
                "websocket_status": self.system_status.get("websocket_status", "disconnected"),
                "redis_status": "connected" if redis_manager.is_connected() else "disconnected",
                "ai_agent_status": self.system_status.get("ai_agent_status", "idle"),
                "total_events_processed": self.system_status.get("total_events_processed", 0),
                "ai_decisions_made": self.system_status.get("ai_decisions_made", 0),
                "system_uptime": self._get_uptime(),
                "last_update": datetime.now().isoformat()
            }

            redis_manager.update_system_status(status)

        except Exception as e:
            print(f"[EVENT_SYSTEM] 更新系统状态失败: {e}")

    def _get_uptime(self) -> str:
        """获取系统运行时间"""
        if not self.system_status.get("start_time"):
            return "0:00:00"

        uptime = datetime.now() - self.system_status["start_time"]
        hours, remainder = divmod(int(uptime.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours}:{minutes:02d}:{seconds:02d}"

    def _show_system_status(self) -> None:
        """显示系统状态"""
        print(f"\n[系统状态]:")
        print(f"   WebSocket: {self.system_status['websocket_status']}")
        print(f"   Redis: {self.system_status['redis_status']}")
        print(f"   AI Agent: {self.system_status['ai_agent_status']}")
        print(f"   运行时间: {self._get_uptime()}")
        print(f"   处理事件: {self.system_status['total_events_processed']}")
        print(f"   AI决策: {self.system_status['ai_decisions_made']}")

    def _show_price_update(self, symbol: str, price: float, volume: float) -> None:
        """显示价格更新"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f" [{timestamp}] {symbol}: ${price:,.2f} (Vol: {volume:,.0f})")

    def run(self) -> None:
        """运行事件系统主循环"""
        if not self.start():
            print("[ERROR] 事件系统启动失败")
            return

        # 注册信号处理
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        print("\n[WARNING] 按 Ctrl+C 停止系统")

        try:
            # 主循环
            while self.running:
                import time
                time.sleep(30)  # 30秒间隔

                # 更新系统状态
                self._update_system_status()

                # 显示系统状态
                if self.system_status["total_events_processed"] % 100 == 0:
                    self._show_system_status()

                # 兜底机制检查
                if self.system_status.get("start_time"):
                    uptime_seconds = (datetime.now() - self.system_status["start_time"]).total_seconds()

                    # 长时间无AI决策，强制触发
                    if uptime_seconds >= Config.FALLBACK_INTERVAL:
                        if self.system_status["ai_decisions_made"] == 0:
                            print("\n[SMART_TRIGGER] 兜底机制：长时间无AI决策，强制触发")
                            asyncio.create_task(self._trigger_ai_decision_async("BTCUSDT"))  # 默认交易对

                    # 数据流监控
                    elif uptime_seconds % Config.FALLBACK_INTERVAL < 30:  # 每5分钟检查一次
                        # 检查是否有市场数据流入
                        last_price_update = redis_manager.get_price_alert("BTCUSDT")
                        if not last_price_update or (uptime_seconds - last_price_update.get('timestamp', 0)) > 300:
                            # 5分钟内没有价格数据
                            symbol = Config.TRADING_SYMBOLS[0]  # 使用第一个交易对
                            print(f"\n[SMART_TRIGGER] 检测到数据流异常，强制触发AI决策: {symbol}")
                            asyncio.create_task(self._trigger_ai_decision_async(symbol))

        except KeyboardInterrupt:
            print("\n\n[WARNING] 收到停止信号")

        finally:
            self.stop()

    def _signal_handler(self, signum, frame) -> None:
        """信号处理器"""
        print(f"\n\n[停止信号] {signum}，正在关闭...")
        self.running = False

    def stop(self) -> None:
        """停止事件系统"""
        print("\n" + "=" * 60)
        print("正在停止事件系统...")
        print("=" * 60)

        self.running = False

        # 停止数据引擎
        if self.data_engine:
            self.data_engine.stop()
            print("[OK] 数据引擎已停止")

        # 更新系统状态
        self.system_status["websocket_status"] = "disconnected"
        self.system_status["ai_agent_status"] = "stopped"
        self._update_system_status()

        # 显示最终统计
        self._show_final_statistics()

        print("\n[OK] 事件系统已停止")

    def _show_final_statistics(self) -> None:
        """显示最终统计信息"""
        print(f"\n[系统统计]:")
        print(f"   运行时间: {self._get_uptime()}")
        print(f"   处理事件: {self.system_status['total_events_processed']}")
        print(f"   AI决策次数: {self.system_status['ai_decisions_made']}")
        print(f"   触发统计: {smart_trigger.get_trigger_statistics()}")

    def get_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        return {
            "running": self.running,
            "system_status": self.system_status,
            "data_engine_running": self.data_engine.running if self.data_engine else False,
            "redis_connected": redis_manager.is_connected()
        }


def main():
    """主函数"""
    # 创建事件系统
    trading_system = EventDrivenTradingSystem()

    # 运行事件系统
    trading_system.run()


if __name__ == "__main__":
    main()
