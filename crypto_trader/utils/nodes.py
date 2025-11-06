#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Graph Node Functions
按照LangChain/LangGraph文档规范组织
集成专业的AlphaArena提示词系统
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, Any, List
from .state import TradingState
# from .tools import BinanceFuturesMCPTools  # 暂时注释，因为不需要
# from prompts.trading_prompts import AlphaArenaPrompt, DeepSeekStrategy, ConfidenceAssessment  # 暂时注释


class TradingNodes:
    """交易节点函数类"""

    def __init__(self, tradeable_symbols: List[str]):
        """初始化节点"""
        self.tradeable_symbols = tradeable_symbols
        self.risk_manager = None
        self.mcp_tools = None

    async def prepare_data(self, state: TradingState) -> TradingState:
        """
        节点1: 准备数据 - 获取所有必要的市场和账户数据
        """
        print("[prepare_data] 准备市场数据...")

        # 初始化MCP工具（暂时跳过）
        # if not self.mcp_tools:
        #     try:
        #         self.mcp_tools = BinanceFuturesMCPTools()
        #         print("  [INFO] MCP工具初始化成功")
        #     except ValueError as e:
        #         print(f"  [WARNING] MCP工具初始化失败: {e}")
        #         self.mcp_tools = None

        # 导入市场数据提供者
        from utils.market_data import EnhancedBinanceDataProvider

        data_provider = EnhancedBinanceDataProvider()

        # 获取所有币种的市场数据（转换为可序列化格式）
        market_data = {}
        for symbol in self.tradeable_symbols:
            try:
                data = data_provider.get_enhanced_market_data(symbol)
                market_data[symbol] = self._serialize_market_data(data)
                print(f"  [OK] {symbol}: ${data.current_price:,.2f}")
            except Exception as e:
                print(f"  [ERROR] {symbol}: {e}")

        # 获取账户信息 (简化版)
        account_info = {
            'account_value': 10000,
            'available_cash': 5000,
            'total_return': 31.34,
            'positions': {}
        }

        print("[prepare_data] 数据准备完成")

        return {
            "timestamp": state.get("timestamp", datetime.now()),
            "market_data": market_data,
            "account_info": account_info,
            "trading_decisions": {},
            "chain_of_thought": "",
            "trading_decisions_output": ""
        }

    def _serialize_market_data(self, data) -> Dict[str, Any]:
        """将EnhancedMarketData对象转换为可序列化的字典格式"""
        serialized = {
            'symbol': data.symbol,
            'timestamp': data.timestamp.isoformat() if isinstance(data.timestamp, datetime) else data.timestamp,
            'current_price': data.current_price,
            'price_change_24h': data.price_change_24h,
            'price_change_percent_24h': data.price_change_percent_24h,
            'price_change_1h': data.price_change_1h,
            'high_24h': data.high_24h,
            'low_24h': data.low_24h,
            'open_24h': data.open_24h,
            'order_book_spread': data.order_book_spread,
            'order_book_bid_depth': data.order_book_bid_depth,
            'order_book_ask_depth': data.order_book_ask_depth,
            'market_sentiment': data.market_sentiment,
        }

        # 处理技术指标
        if data.indicators:
            serialized['indicators'] = {
                'ema_20': data.indicators.ema_20,
                'macd': data.indicators.macd,
                'ema_50': data.indicators.ema_50,
                'sma_20': data.indicators.sma_20,
                'macd_signal': data.indicators.macd_signal,
                'macd_histogram': data.indicators.macd_histogram,
                'rsi_7': data.indicators.rsi_7,
                'rsi_14': data.indicators.rsi_14,
                'rsi_21': data.indicators.rsi_21,
                'atr_3': data.indicators.atr_3,
                'atr_14': data.indicators.atr_14,
                'volume_current': data.indicators.volume_current,
                'volume_average_20': data.indicators.volume_average_20,
                'volume_average_50': data.indicators.volume_average_50,
                'price_position': data.indicators.price_position,
                'volatility_20': data.indicators.volatility_20,
            }

        # 处理资金费率
        if data.funding_rate:
            serialized['funding_rate'] = {
                'symbol': data.funding_rate.symbol,
                'funding_rate': data.funding_rate.funding_rate,
                'funding_time': data.funding_rate.funding_time,
                'next_funding_time': data.funding_rate.next_funding_time,
            }

        # 处理持仓量
        if data.open_interest:
            serialized['open_interest'] = {
                'symbol': data.open_interest.symbol,
                'sum_open_interest': data.open_interest.sum_open_interest,
                'sum_open_interest_value': data.open_interest.sum_open_interest_value,
                'time': data.open_interest.time,
            }

        return serialized

    async def make_decisions(
        self,
        state: TradingState,
        llm=None
    ) -> TradingState:
        """
        节点2: AI决策 - 基于完整数据做交易决策
        """
        print("[make_decisions] 生成AI交易决策...")

        if not llm:
            return {
                "timestamp": state["timestamp"],
                "market_data": state["market_data"],
                "account_info": state["account_info"],
                "trading_decisions": {},
                "chain_of_thought": "需要配置API密钥",
                "trading_decisions_output": "SKIP - 需要API密钥"
            }

        # 初始化变量
        trading_decisions = {}
        chain_of_thought = ""
        decisions_part = ""

        try:
            # 构建提示词
            system_prompt = self._build_system_prompt(state)
            user_prompt = self._get_user_prompt()

            # 调用AI进行决策
            from langchain_core.messages import HumanMessage, SystemMessage

            # 使用AlphaArenaPrompt生成风险警告
            formatted_state = self._format_state_for_prompts(state)
            risk_warning = AlphaArenaPrompt.get_risk_warning_prompt(formatted_state)
            print(f"\n{risk_warning}\n")

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            response = llm.invoke(messages)

            # 解析响应
            content = response.content

            # 分离CHAIN_OF_THOUGHT和TRADING_DECISIONS
            if ">>TRADING_DECISIONS" in content:
                parts = content.split(">>TRADING_DECISIONS", 1)
                chain_of_thought = parts[0].replace("CHAIN_OF_THOUGHT", "").strip()
                decisions_part = parts[1].strip() if len(parts) > 1 else ""
            else:
                chain_of_thought = content[:500]
                decisions_part = content[500:]

            # 使用ConfidenceAssessment计算置信度
            ai_confidence = self._calculate_confidence_with_assessment(state)

            # 尝试解析JSON决策
            try:
                json_start = content.find('{')
                json_end = content.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_content = content[json_start:json_end]
                    if json_content.startswith("```json"):
                        json_content = json_content[7:]
                    if json_content.endswith("```"):
                        json_content = json_content[:-3]

                    trading_decisions = json.loads(json_content)
                    print(f"  [OK] AI决策完成，生成{len(trading_decisions)}个决策")

                    # 使用ConfidenceAssessment增强决策质量
                    print(f"  [INFO] 置信度评估: {ai_confidence:.2f} - {ConfidenceAssessment.get_confidence_breakdown(ai_confidence)}")

                    # 通过MCP工具执行交易决策
                    if self.mcp_tools and trading_decisions:
                        print(f"  [INFO] 通过MCP工具执行{len(trading_decisions)}个交易决策...")
                        execution_results = await self._execute_trading_decisions(trading_decisions, state)
                        print(f"  [OK] MCP交易执行完成: {execution_results.get('summary', 'N/A')}")
                else:
                    print("  [WARNING] 未找到JSON决策格式")
            except Exception as e:
                print(f"  [WARNING] JSON解析失败: {e}")

        except Exception as e:
            print(f"  [ERROR] AI决策失败: {e}")
            chain_of_thought = f"决策失败: {e}"
            decisions_part = "ERROR"

        return {
            "timestamp": state["timestamp"],
            "market_data": state["market_data"],
            "account_info": state["account_info"],
            "trading_decisions": trading_decisions,
            "chain_of_thought": chain_of_thought,
            "trading_decisions_output": decisions_part
        }

    def _build_system_prompt(self, state: TradingState) -> str:
        """构建系统提示词 - 使用AlphaArena专业框架"""
        # 准备状态数据
        formatted_state = self._format_state_for_prompts(state)

        # 使用AlphaArenaPrompt生成专业提示词
        prompt = AlphaArenaPrompt.get_decision_prompt(formatted_state)

        return prompt

    def _get_user_prompt(self) -> str:
        """获取用户提示词"""
        return """请基于上述市场数据和账户信息，做交易决策。

输出要求:
1. 先输出>>TRADING_DECISIONS部分的符号决策
2. 然后输出完整的JSON格式决策

JSON格式示例:
{
  "BTCUSDT": {
    "signal": "HOLD",
    "quantity": 0.1,
    "confidence": 0.75,
    "reasoning": "价格接近目标，MACD改善"
  }
}

注意:
- 已有持仓只能选择HOLD或CLOSE
- 无持仓可以开新仓
- 必须基于技术指标和市场数据做决策
- 置信度0-1之间
"""

    def _format_market_data_section(self, state: TradingState) -> str:
        """格式化市场数据部分"""
        sections = []

        for symbol, data in state["market_data"].items():
            indicators = data.get('indicators', {})

            funding_info = ""
            if data.get('funding_rate'):
                funding_info = f"资金费率: {data['funding_rate']['funding_rate']:.6f}"
            else:
                funding_info = "资金费率: N/A"

            oi_info = ""
            if data.get('open_interest'):
                oi_info = f"持仓量: {data['open_interest']['sum_open_interest']:,.0f}"
            else:
                oi_info = "持仓量: N/A"

            current_section = f"""
{symbol}:
  当前价格: ${data['current_price']:,.2f}
  当前EMA20: ${indicators.get('ema_20', 0):,.2f}
  当前MACD: {indicators.get('macd', 0):.2f}
  当前RSI (7期): {indicators.get('rsi_7', 0):.1f}
  {funding_info}
  {oi_info}"""

            sections.append(current_section)

        return "\n".join(sections)

    def _format_account_info_section(self, state: TradingState) -> str:
        """格式化账户信息部分"""
        return f"""
=== 账户信息 ===
总回报: {state["account_info"].get('total_return', 0):.2f}%
可用现金: ${state["account_info"].get('available_cash', 0):,.2f}
当前账户价值: ${state["account_info"].get('account_value', 0):,.2f}

=== 当前持仓 ===
无持仓"""

    def _format_state_for_prompts(self, state: TradingState) -> Dict[str, Any]:
        """将TradingState转换为AlphaArenaPrompt期望的格式"""
        # 转换市场数据
        formatted_market_data = {}
        for symbol, data in state.get("market_data", {}).items():
            indicators = data.get('indicators', {})
            formatted_market_data[symbol] = {
                "price": data.get('current_price', 0),
                "change_pct_24h": data.get('price_change_percent_24h', 0),
                "indicators": {
                    "rsi": indicators.get('rsi_7', 50),
                    "macd": indicators.get('macd', 0),
                    "trend": data.get('market_sentiment', 'NEUTRAL')
                }
            }

        # 转换持仓数据
        formatted_positions = {
            "CASH": state.get("account_info", {}).get('available_cash', 10000),
            # 可以添加更多持仓信息
        }

        # 配置信息
        config = {
            "confidence_threshold": 0.8,
            "max_positions": 2,
            "leverage": 20,
            "stop_loss_pct": 0.015
        }

        return {
            "market_data": formatted_market_data,
            "positions": formatted_positions,
            "config": config
        }

    def _calculate_confidence_with_assessment(self, state: TradingState) -> float:
        """使用ConfidenceAssessment计算置信度"""
        market_data = {}
        technical_indicators = {}

        # 提取第一个币种的数据作为示例
        if state.get("market_data"):
            first_symbol = list(state["market_data"].keys())[0]
            data = state["market_data"][first_symbol]

            market_data[first_symbol] = {
                "price": data.get('current_price', 0),
                "change_pct_24h": data.get('price_change_percent_24h', 0)
            }

            indicators = data.get('indicators', {})
            technical_indicators = {
                "rsi": indicators.get('rsi_7', 50),
                "macd": indicators.get('macd', 0),
                "trend": data.get('market_sentiment', 'NEUTRAL')
            }

        return ConfidenceAssessment.calculate_confidence(market_data, technical_indicators)

    def _generate_position_analysis(self, state: TradingState) -> str:
        """生成持仓分析文本"""
        if not state["account_info"].get('positions'):
            return "当前无持仓"
        return "当前持仓信息详见账户部分"

    async def _execute_trading_decisions(
        self,
        trading_decisions: Dict[str, Any],
        state: TradingState
    ) -> Dict[str, Any]:
        """
        通过MCP工具执行交易决策
        """
        if not self.mcp_tools:
            return {
                "success": False,
                "summary": "MCP工具未初始化",
                "executed_count": 0,
                "errors": ["MCP工具未初始化"]
            }

        execution_summary = {
            "success": True,
            "summary": "",
            "executed_count": 0,
            "skipped_count": 0,
            "errors": [],
            "details": {}
        }

        try:
            # 使用ConfidenceAssessment进行全局置信度评估
            global_confidence = self._calculate_confidence_with_assessment(state)
            confidence_threshold = 0.8  # Alpha Arena标准

            for symbol, decision in trading_decisions.items():
                signal = decision.get('signal', '').upper()
                quantity = decision.get('quantity', 0)
                ai_confidence = decision.get('confidence', 0)

                # 跳过置信度低的决策 - 使用Alpha Arena标准
                if ai_confidence < confidence_threshold:
                    execution_summary['skipped_count'] += 1
                    execution_summary['details'][symbol] = {
                        "status": "skipped",
                        "reason": f"AI置信度 {ai_confidence:.2f} < {confidence_threshold} (Alpha Arena标准)"
                    }
                    continue

                # 全局市场置信度过低也跳过
                if global_confidence < 0.6:
                    execution_summary['skipped_count'] += 1
                    execution_summary['details'][symbol] = {
                        "status": "skipped",
                        "reason": f"全局置信度 {global_confidence:.2f} < 0.6"
                    }
                    continue

                # 处理不同信号
                if signal == "HOLD":
                    execution_summary['skipped_count'] += 1
                    execution_summary['details'][symbol] = {
                        "status": "skipped",
                        "reason": "信号为HOLD，保持持仓"
                    }

                elif signal == "CLOSE":
                    result = await self.mcp_tools.place_order(
                        symbol=symbol,
                        side="SELL",
                        order_type="MARKET",
                        quantity=abs(quantity),
                        reduce_only=True,
                        close_position=True
                    )

                    execution_summary['details'][symbol] = {
                        "status": "executed" if result.get('success') else "failed",
                        "action": "close_position",
                        "result": result
                    }

                    if result.get('success'):
                        execution_summary['executed_count'] += 1
                    else:
                        execution_summary['errors'].append(f"{symbol}: {result.get('message')}")

                elif signal in ["BUY", "SELL"]:
                    # 开仓操作
                    leverage_result = await self.mcp_tools.set_leverage(
                        symbol=symbol,
                        leverage=3
                    )

                    if not leverage_result.get('success'):
                        execution_summary['errors'].append(
                            f"{symbol} 设置杠杆失败: {leverage_result.get('message')}"
                        )
                        continue

                    order_result = await self.mcp_tools.place_order(
                        symbol=symbol,
                        side=signal,
                        order_type="MARKET",
                        quantity=quantity,
                        reduce_only=False
                    )

                    execution_summary['details'][symbol] = {
                        "status": "executed" if order_result.get('success') else "failed",
                        "action": "open_position",
                        "leverage_result": leverage_result,
                        "order_result": order_result
                    }

                    if order_result.get('success'):
                        execution_summary['executed_count'] += 1
                    else:
                        execution_summary['errors'].append(f"{symbol}: {order_result.get('message')}")

            # 生成摘要
            executed = execution_summary['executed_count']
            skipped = execution_summary['skipped_count']
            errors = len(execution_summary['errors'])

            if executed > 0:
                execution_summary['summary'] = f"成功执行 {executed} 个决策"
                if skipped > 0:
                    execution_summary['summary'] += f"，跳过 {skipped} 个"
                if errors > 0:
                    execution_summary['summary'] += f"，{errors} 个错误"
            else:
                execution_summary['summary'] = "未执行任何交易决策"
                if errors > 0:
                    execution_summary['summary'] += f"，{errors} 个错误"

        except Exception as e:
            execution_summary['success'] = False
            execution_summary['summary'] = f"执行异常: {str(e)}"
            execution_summary['errors'].append(str(e))

        return execution_summary
