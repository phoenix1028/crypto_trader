#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TradingAgentV3 - 使用正确的LangChain API
基于 langchain.agents.create_agent
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv

# 加载.env文件
load_dotenv(dotenv_path="D:/AI_deepseek_trader/crypto_trader/.env")

# LangChain imports
from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from langchain.agents.middleware import ToolCallLimitMiddleware
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

# LangSmith imports
from langsmith import Client, tracing_context, traceable

# 项目模块导入
from configs.config import Config
from utils.tools import TRADING_TOOLS
from utils.alpha_arena_formatter import AlphaArenaFormatter
from prompts.alpha_arena_prompt import AlphaArenaTradingPrompt


# ==================== Agent输出格式定义 ====================

class AgentResponse(BaseModel):
    """Agent响应格式"""
    final_decision: str = Field(description="最终决策: HOLD/BUY/SELL/CLOSE")
    reasoning: str = Field(description="决策推理链")
    confidence: float = Field(description="决策置信度 0.0-1.0", ge=0.0, le=1.0)
    executed_trades: List[Dict[str, Any]] = Field(default=[], description="已执行的交易列表")


class TradingAgentV3:
    """基于create_agent的正确交易Agent"""

    def __init__(self):
        """初始化Agent"""
        # 支持的交易对
        self.tradeable_symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "DOGEUSDT"]

        # 初始化LLM
        self.llm = self._init_llm()

        # 初始化数据提供者
        self.data_provider = None

        # 初始化LangSmith追踪
        self._init_langsmith()

        # 初始化Alpha Arena格式化器
        self.formatter = AlphaArenaFormatter()

        # 构建Agent（使用create_agent）
        self.agent = self._build_agent()

        print(f"[INFO] AgentV3初始化完成，支持币种: {', '.join(self.tradeable_symbols)}")

    def _get_risk_unit(self, confidence: float) -> float:
        """获取风险单位（基于置信度）"""
        if confidence >= Config.HIGH_CONFIDENCE_THRESHOLD:
            return 0.025  # 高置信度：2.5%风险单位
        elif confidence >= Config.MEDIUM_CONFIDENCE_THRESHOLD:
            return 0.0175  # 中置信度：1.75%风险单位
        elif confidence >= Config.LOW_CONFIDENCE_THRESHOLD:
            return 0.01  # 低置信度：1%风险单位
        else:
            return 0.0  # 极低置信度：无持仓

    def _init_llm(self) -> Optional[ChatOpenAI]:
        """初始化DeepSeek LLM"""
        try:
            openai_api_key = os.getenv("OPENAI_API_KEY")
            openai_base_url = os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com")

            if not openai_api_key:
                print("[WARNING] 未配置OPENAI_API_KEY，Agent将以模拟模式运行")
                return None

            llm = ChatOpenAI(
                api_key=openai_api_key,
                base_url=openai_base_url,
                model="deepseek-chat",
                temperature=0.1  # 低温度确保决策稳定性
            )

            print("[INFO] LLM初始化成功")
            return llm

        except Exception as e:
            print(f"[ERROR] LLM初始化失败: {e}")
            return None

    def _init_langsmith(self):
        """初始化LangSmith追踪"""
        try:
            langsmith_api_key = os.getenv("LANGSMITH_API_KEY")
            if langsmith_api_key:
                # 创建LangSmith客户端
                self.langsmith_client = Client(
                    api_key=langsmith_api_key,
                    api_url="https://api.smith.langchain.com"
                )

                print("[INFO] LangSmith客户端初始化成功")
            else:
                print("[WARNING] 未配置LANGSMITH_API_KEY，跳过LangSmith初始化")
                self.langsmith_client = None

        except Exception as e:
            print(f"[ERROR] LangSmith初始化失败: {e}")
            self.langsmith_client = None

    def _build_agent(self, state_data: Dict[str, Any] = None):
        """构建Agent

        Args:
            state_data: 状态数据，用于构建系统提示词
        """
        # 如果没有LLM，返回None
        if not self.llm:
            return None

        # 构建系统提示词（使用状态数据）
        system_prompt = self._build_system_prompt(state_data)

        # 🔥 创建工具调用限制中间件（Agent最多8次工具调用）
        limiter = ToolCallLimitMiddleware(
            run_limit=8,  # 限制Agent最多8次工具调用
            exit_behavior="end"  # 达到限制后优雅结束
        )

        # ✅ 使用create_agent创建标准LangChain Agent
        # AI会自主决定何时调用set_leverage_tool和place_order_tool
        agent = create_agent(
            model=self.llm,
            tools=TRADING_TOOLS,  # 工具列表，AI可以自主调用
            system_prompt=system_prompt,
            # 移除AgentResponse，让AI直接返回文本
            middleware=[limiter]  # 应用限制
        )

        return agent

    def _build_system_prompt(self, state_data: Dict[str, Any] = None) -> str:
        """构建系统提示词"""
        # 如果提供了状态数据，包含当前市场信息
        market_info = ""
        if state_data and state_data.get('market_data'):
            first_symbol = list(state_data['market_data'].keys())[0]
            data = state_data['market_data'][first_symbol]
            market_info = f"""
当前市场信息 ({first_symbol}):
- 价格: ${data.get('current_price', 0):,.2f}
- 24h变化: {data.get('price_change_percent_24h', 0):+.2f}%
- RSI: {data.get('indicators', {}).get('rsi_14', 'N/A')}
- MACD: {data.get('indicators', {}).get('macd', 'N/A')}
"""

        return f"""你是专业的量化交易AI助手，专注于短线高频交易。

当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{market_info}

🚀 核心指令：你是真正的交易Agent，**必须通过工具调用执行真实交易**，不能只输出决策！

可用工具:
- **set_leverage_tool**: 设置交易对杠杆倍数（开仓前必须调用）
- **place_order_tool**: 下单交易（核心工具，支持市价单和限价单）

🔥 强制工作流程:
1. 分析已提供的市场数据和账户信息
2. 基于技术指标做交易决策
3. **如果决定BUY或SELL**（置信度>0.4）：
   a. **必须先调用set_leverage_tool设置杠杆20**
   b. **然后必须调用place_order_tool下单**
   c. 获取工具执行结果（订单ID等）
4. **根据置信度计算交易数量**：
   - 中置信度(>0.4): 1.75%风险单位
   - 高置信度(>0.7): 2.5%风险单位
5. **在executed_trades中记录所有已执行交易**
6. 最终输出AgentResponse格式

决策原则:
- 使用已提供的数据做决策
- 关注RSI、MACD、EMA等技术指标
- **积极交易，合适的时机就出手！**
- 置信度>0.4就要执行交易
- **记住：必须实际调用工具执行交易，不能只是说"我要交易"！**

最终输出格式:
```json
{{
  "final_decision": "BUY",  // 或HOLD/SELL/CLOSE
  "reasoning": "详细分析...",
  "confidence": 0.65,
  "executed_trades": [
    {{
      "symbol": "BTCUSDT",
      "side": "BUY",
      "quantity": 0.001,
      "order_type": "MARKET",
      "status": "SUCCESS",
      "order_id": 123456
    }}
  ]
}}
```

重要：executed_trades必须包含实际通过工具执行的所有交易！如果HOLD则为空数组[]。"""

    async def make_trading_decision(self, symbol: str, state_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """执行交易决策（主入口）

        Args:
            symbol: 交易对符号
            state_data: 准备好的状态数据，包含market_data和account_info
        """
        try:
            print(f"[AGENT] 开始为 {symbol} 生成交易决策...")
            print(f"[AGENT] 数据状态: {'已准备' if state_data else '未准备'}")

            # 首先尝试使用真正的AI决策
            if self.llm and self.agent and state_data and state_data.get('market_data'):
                return await self._ai_decision(symbol, state_data)
            else:
                # 如果没有LLM，使用模拟决策
                print("[WARNING] 未配置LLM，使用模拟决策")
                return self._simulate_decision(symbol, state_data)

        except Exception as e:
            print(f"[ERROR] 交易决策生成失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "decisions": {},
                "chain_of_thought": f"决策生成失败: {str(e)}"
            }

    @traceable(run_type="tool", name="Trading Decision Analysis")
    async def _ai_decision(self, symbol: str, state_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """使用AI做交易决策 - AI会自主调用交易工具"""
        print(f"[AI] 调用DeepSeek AI分析 {symbol}...")
        print(f"[AI] Agent会自主调用交易工具执行真实交易")

        try:
            # 使用Alpha Arena格式准备数据
            formatted_state = self._prepare_alpha_arena_state(state_data, symbol)

            # 构建User Prompt
            user_prompt = AlphaArenaTradingPrompt.get_user_prompt(formatted_state)

            # 🚨 强制要求AI调用工具执行交易
            enforcement_prompt = f"""

[强制执行指令]
基于以上市场数据，你现在是真正的交易Agent。
如果你决定交易（BUY/SELL），你必须：
1. 先调用 set_leverage_tool，设置 {symbol} 杠杆为20
2. 然后调用 place_order_tool，下单 {symbol}
3. 获取工具执行结果（订单ID）
4. 在最终响应中包含 executed_trades 字段记录实际执行的交易

[警告] 不能只输出决策文本，必须实际调用工具！
[正确] 调用工具 → 获取结果 → 记录交易 → 输出响应

现在请分析数据并执行交易！"""

            # 合并User Prompt和强制执行指令
            full_user_prompt = user_prompt + enforcement_prompt

            print(f"[AI] 发送分析请求到DeepSeek...")
            print(f"[AI] User Prompt长度: {len(full_user_prompt)}")

            # ✅ 调用Agent (在LangSmith追踪上下文中)
            # Agent会自动进行工具调用循环：模型→工具→观察→模型
            if self.langsmith_client:
                with tracing_context(
                    client=self.langsmith_client,
                    project_name="AI_Crypto_Trader",
                    enabled=True
                ):
                    result = await self.agent.ainvoke({
                        "messages": [{"role": "user", "content": full_user_prompt}]
                    })
            else:
                result = await self.agent.ainvoke({
                    "messages": [{"role": "user", "content": full_user_prompt}]
                })

            # 提取文本响应
            # 尝试从不同字段获取响应
            agent_content = result.get("output", "") or result.get("messages", [])
            if isinstance(agent_content, list) and agent_content:
                # 从messages中提取最后的AIMessage内容
                last_message = agent_content[-1]
                if hasattr(last_message, 'content'):
                    agent_content = last_message.content
                else:
                    agent_content = str(last_message)
            elif not agent_content:
                print(f"[AI] 未收到响应，完整结果键: {list(result.keys())}")
                # 尝试从messages中提取
                messages = result.get("messages", [])
                if messages:
                    for msg in reversed(messages):
                        if hasattr(msg, 'content') and msg.content:
                            agent_content = msg.content
                            break

            if not agent_content:
                print(f"[AI] 未收到响应，完整结果: {result}")
                raise ValueError("AI未返回响应")

            print(f"[AI] 收到Agent响应 (文本格式)")
            print(f"[AI] 响应内容: {agent_content[:200]}...")

            # 解析文本响应中的交易信息
            return self._parse_agent_text_response(agent_content, symbol, state_data)

        except Exception as e:
            print(f"[AI] AI决策失败: {e}")
            import traceback
            traceback.print_exc()
            # 降级到模拟决策
            print("[AI] 降级到模拟决策")
            return self._simulate_decision(symbol, state_data)

    def _format_market_data_for_ai(self, state_data: Dict[str, Any], symbol: str) -> str:
        """格式化市场数据供AI分析"""
        market_data = state_data.get('market_data', {}).get(symbol, {})

        current_price = market_data.get('current_price', 0)
        price_change = market_data.get('price_change_percent_24h', 0)
        high_24h = market_data.get('high_24h', 0)
        low_24h = market_data.get('low_24h', 0)
        volume = market_data.get('volume', 0)
        indicators = market_data.get('indicators', {})

        # 转换数值为float（防止字符串类型）
        try:
            current_price = float(current_price) if current_price else 0.0
        except (ValueError, TypeError):
            current_price = 0.0

        try:
            price_change = float(price_change) if price_change else 0.0
        except (ValueError, TypeError):
            price_change = 0.0

        try:
            high_24h = float(high_24h) if high_24h else 0.0
        except (ValueError, TypeError):
            high_24h = 0.0

        try:
            low_24h = float(low_24h) if low_24h else 0.0
        except (ValueError, TypeError):
            low_24h = 0.0

        try:
            volume = float(volume) if volume else 0.0
        except (ValueError, TypeError):
            volume = 0.0

        # 处理EMA值
        ema_20 = indicators.get('ema_20', 0)
        ema_50 = indicators.get('ema_50', 0)
        try:
            ema_20 = float(ema_20) if ema_20 else 0.0
        except (ValueError, TypeError):
            ema_20 = 0.0
        try:
            ema_50 = float(ema_50) if ema_50 else 0.0
        except (ValueError, TypeError):
            ema_50 = 0.0

        return f"""
{symbol} 实时数据:
- 当前价格: ${current_price:,.2f}
- 24小时变化: {price_change:+.2f}%
- 24小时最高: ${high_24h:,.2f}
- 24小时最低: ${low_24h:,.2f}
- 24小时成交量: {volume:,.0f}

技术指标:
- RSI(14): {indicators.get('rsi_14', 'N/A')}
- EMA(20): ${ema_20:,.2f}
- EMA(50): ${ema_50:,.2f}
- MACD: {indicators.get('macd', 'N/A')}
- ATR(14): {indicators.get('atr_14', 'N/A')}

市场情绪: {market_data.get('market_sentiment', 'NEUTRAL')}
"""

    def _simulate_decision(self, symbol: str, state_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """模拟决策（无LLM时使用）"""
        print(f"[SIMULATION] 模拟 {symbol} 决策...")

        try:
            # 使用提供的数据而不是自己获取
            if not state_data or not state_data.get('market_data'):
                return {
                    "success": False,
                    "error": "缺少市场数据",
                    "decisions": {},
                    "chain_of_thought": "缺少市场数据"
                }

            symbol_data = state_data['market_data'].get(symbol, {})
            current_price = symbol_data.get('current_price', 0)
            price_change = symbol_data.get('price_change_percent_24h', 0)
            indicators = symbol_data.get('indicators', {})

            # 基于技术指标决策
            rsi_14 = indicators.get('rsi_14', 50)
            ema_20 = indicators.get('ema_20', 0)
            macd = indicators.get('macd', 0)

            if rsi_14 < 30 and price_change < -2:
                signal = "BUY"
                confidence = 0.85
                reasoning = f"RSI({rsi_14:.1f})超卖，24h下跌{price_change:.2f}%，技术反弹"
            elif rsi_14 > 70 and price_change > 2:
                signal = "SELL"
                confidence = 0.85
                reasoning = f"RSI({rsi_14:.1f})超买，24h上涨{price_change:.2f}%，技术回调"
            elif macd > 0 and ema_20 > 0 and current_price > ema_20:
                signal = "BUY"
                confidence = 0.80
                reasoning = f"MACD({macd:.2f})为正，价格高于EMA20，趋势向上"
            elif macd < 0 and ema_20 > 0 and current_price < ema_20:
                signal = "SELL"
                confidence = 0.80
                reasoning = f"MACD({macd:.2f})为负，价格低于EMA20，趋势向下"
            else:
                signal = "HOLD"
                confidence = 0.90
                reasoning = f"技术指标中性，RSI({rsi_14:.1f})，横盘整理"

            # 计算交易数量（基于账户余额和风险单位）
            account_info = state_data.get('account_info', {})
            account_value = account_info.get('current_balance', 10000.0)  # 默认账户余额
            risk_unit = self._get_risk_unit(confidence)

            if risk_unit <= 0 or signal == "HOLD":
                quantity = 0.0
            else:
                # 计算交易金额 = 账户余额 * 风险单位
                trade_value = account_value * risk_unit
                # 计算数量 = 交易金额 / 当前价格
                quantity = trade_value / current_price if current_price > 0 else 0.0

                # 确保数量在合理范围内
                if quantity < 0.001:
                    quantity = 0.001
                elif quantity > 1.0:
                    quantity = round(quantity, 3)

            return {
                "success": True,
                "decisions": {
                    symbol: {
                        "signal": signal,
                        "quantity": quantity,
                        "confidence": confidence,
                        "reasoning": reasoning,
                        "current_price": current_price,
                        "price_change_24h": price_change
                    }
                },
                "high_confidence_decisions": [
                    {
                        "symbol": symbol,
                        "signal": signal,
                        "confidence": confidence,
                        "quantity": quantity,
                        "side": signal if signal in ["BUY", "SELL"] else "BUY",  # 🔧 确保包含side字段
                        "reasoning": reasoning
                    }
                ] if signal != "HOLD" and confidence >= Config.MEDIUM_CONFIDENCE_THRESHOLD else [],
                "chain_of_thought": f"基于技术分析: {reasoning}",
                "total_decisions": 1,
                "high_confidence_count": 1 if signal != "HOLD" and confidence >= Config.MEDIUM_CONFIDENCE_THRESHOLD else 0
            }

        except Exception as e:
            print(f"[ERROR] 模拟决策失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "decisions": {},
                "chain_of_thought": f"模拟决策失败: {str(e)}"
            }

    def _parse_agent_text_response(self, agent_content: str, symbol: str, state_data: Dict[str, Any]) -> Dict[str, Any]:
        """解析Agent文本响应，提取交易信息"""
        try:
            print(f"[PARSER] 解析Agent文本响应...")
            print(f"[PARSER] 内容长度: {len(agent_content)}")

            # 从工具调用结果中提取交易信息
            executed_trades = []
            reasoning = agent_content

            # 查找SUCCESS订单信息
            import re
            order_id_pattern = r'订单ID[:\s]*(\d+)'
            success_pattern = r'\[SUCCESS\]'

            if re.search(success_pattern, agent_content):
                # 提取订单ID
                order_id_match = re.search(order_id_pattern, agent_content)
                if order_id_match:
                    order_id = int(order_id_match.group(1))

                    # 尝试提取交易详情
                    # 查找下单格式：BUY MARKET 0.001 BTCUSDT
                    order_pattern = r'(BUY|SELL)\s+MARKET\s+([\d\.]+)\s+(\w+)'
                    order_match = re.search(order_pattern, agent_content)

                    if order_match:
                        side = order_match.group(1)
                        quantity = float(order_match.group(2))
                        trade_symbol = order_match.group(3)

                        executed_trades.append({
                            "symbol": trade_symbol,
                            "side": side,
                            "quantity": quantity,
                            "order_type": "MARKET",
                            "status": "SUCCESS",
                            "order_id": order_id
                        })
                        print(f"[PARSER] 提取交易: {side} {quantity} {trade_symbol}, 订单ID: {order_id}")

            # 确定最终决策
            signal = "HOLD"
            confidence = 0.5
            if executed_trades:
                # 如果有交易执行，根据交易方向确定信号
                trade_side = executed_trades[0]["side"]
                if trade_side == "BUY":
                    signal = "BUY"
                    confidence = 0.65
                elif trade_side == "SELL":
                    signal = "SELL"
                    confidence = 0.65

            # 计算交易数量
            quantity = 0.0
            if signal in ["BUY", "SELL"] and confidence >= Config.MEDIUM_CONFIDENCE_THRESHOLD:
                # 计算交易数量
                account_info = state_data.get('account_info', {})
                account_value = account_info.get('current_balance', 10000.0)
                risk_unit = self._get_risk_unit(confidence)

                symbol_data = state_data.get('market_data', {}).get(symbol, {})
                current_price = symbol_data.get('current_price', 0)

                if risk_unit > 0 and current_price > 0:
                    trade_value = account_value * risk_unit
                    quantity = trade_value / current_price
                    if quantity < 0.001:
                        quantity = 0.001
                    elif quantity > 1.0:
                        quantity = round(quantity, 3)

            # 构建决策结果
            decision_result = {
                "signal": signal,
                "confidence": confidence,
                "reasoning": reasoning[:500],  # 限制长度
                "symbol": symbol,
                "quantity": quantity,
                "side": signal if signal in ["BUY", "SELL"] else "BUY"
            }

            # 构建完整返回格式
            return {
                "success": True,
                "decisions": {
                    symbol: decision_result
                },
                "high_confidence_decisions": [
                    {
                        "symbol": symbol,
                        "signal": signal,
                        "confidence": confidence,
                        "quantity": quantity,
                        "side": decision_result["side"],
                        "reasoning": reasoning[:200]
                    }
                ] if signal != "HOLD" and confidence >= Config.MEDIUM_CONFIDENCE_THRESHOLD else [],
                "chain_of_thought": reasoning[:500],
                "agent_executed_trades": executed_trades,  # Agent实际执行的交易
                "total_decisions": 1,
                "high_confidence_count": 1 if signal != "HOLD" and confidence >= Config.MEDIUM_CONFIDENCE_THRESHOLD else 0
            }

        except Exception as e:
            print(f"[ERROR] 解析Agent文本响应失败: {e}")
            import traceback
            traceback.print_exc()
            # 返回默认HOLD决策
            return {
                "success": False,
                "error": f"解析失败: {str(e)}",
                "decisions": {},
                "chain_of_thought": f"解析错误: {str(e)}"
            }

    def _parse_agent_response(self, content: str, symbol: str) -> Dict[str, Any]:
        """解析Agent响应"""
        print(f"[PARSER] 解析Agent响应...")

        try:
            # 简单的决策解析
            content_lower = content.lower()

            # 检测决策类型
            if "买入" in content_lower or "buy" in content_lower:
                if "hold" in content_lower:
                    signal = "HOLD"
                    confidence = 0.90
                else:
                    signal = "BUY"
                    confidence = 0.85
            elif "卖出" in content_lower or "sell" in content_lower:
                if "hold" in content_lower:
                    signal = "HOLD"
                    confidence = 0.90
                else:
                    signal = "SELL"
                    confidence = 0.85
            else:
                signal = "HOLD"
                confidence = 0.90

            # 计算数量（基于风险单位和模拟账户余额）
            risk_unit = self._get_risk_unit(confidence)
            if risk_unit <= 0 or signal == "HOLD":
                quantity = 0.0
            else:
                # 模拟账户余额为10000 USDT
                account_value = 10000.0
                trade_value = account_value * risk_unit
                # 模拟BTC价格为50000（实际中会从state_data获取）
                current_price = 50000.0
                quantity = trade_value / current_price
                if quantity < 0.001:
                    quantity = 0.001
                elif quantity > 1.0:
                    quantity = round(quantity, 3)

            # 生成决策
            decision = {
                "signal": signal,
                "quantity": quantity,
                "confidence": confidence,
                "reasoning": content[:200] if len(content) > 200 else content,
                "current_price": 0,  # Agent会自己获取
                "price_change_24h": 0  # Agent会自己获取
            }

            # 可执行决策（中和高置信度）
            high_confidence_decisions = []
            if signal != "HOLD" and confidence >= Config.MEDIUM_CONFIDENCE_THRESHOLD:
                high_confidence_decisions.append({
                    "symbol": symbol,
                    "signal": signal,
                    "confidence": confidence,
                    "quantity": quantity,
                    "side": signal if signal in ["BUY", "SELL"] else "BUY",  # 🔧 确保包含side字段
                    "reasoning": decision["reasoning"]
                })

            return {
                "success": True,
                "decisions": {symbol: decision},
                "high_confidence_decisions": high_confidence_decisions,
                "chain_of_thought": content[:500] if len(content) > 500 else content,
                "total_decisions": 1,
                "high_confidence_count": len(high_confidence_decisions)
            }

        except Exception as e:
            print(f"[PARSER] 解析异常: {e}")
            return {
                "success": False,
                "error": str(e),
                "decisions": {},
                "chain_of_thought": f"解析失败: {str(e)}"
            }

    def _prepare_alpha_arena_state(self, state_data: Dict[str, Any], symbol: str) -> Dict[str, Any]:
        """准备Alpha Arena格式的状态数据"""
        if not state_data:
            return {}

        # 格式化市场数据
        raw_market_data = state_data.get('market_data', {})
        formatted_market_data = {}
        for sym, data in raw_market_data.items():
            if isinstance(data, dict):
                # 如果已经是字典格式，转换为EnhancedMarketData对象
                from types import SimpleNamespace
                data_obj = SimpleNamespace(**data)
                formatted_market_data[sym] = data_obj

        formatted_market_data = self.formatter.format_market_data(formatted_market_data)

        # 格式化账户信息
        account_info = self.formatter.format_account_info(state_data.get('account_info', {}))

        # 格式化运行统计
        runtime_stats = self.formatter.format_runtime_stats({
            'start_time': datetime.now(),
            'call_count': 1
        })

        return {
            'runtime_stats': runtime_stats,
            'market_data': formatted_market_data,
            'account_info': account_info,
            'positions': account_info.get('positions', [])
        }


# 全局Agent实例
agent_v3 = None

def get_agent_v3() -> TradingAgentV3:
    """获取全局Agent实例"""
    global agent_v3
    if agent_v3 is None:
        agent_v3 = TradingAgentV3()
    return agent_v3


if __name__ == "__main__":
    # 测试Agent
    async def test_agent():
        agent = get_agent_v3()
        result = await agent.make_trading_decision("BTCUSDT")
        print(result)

    asyncio.run(test_agent())
