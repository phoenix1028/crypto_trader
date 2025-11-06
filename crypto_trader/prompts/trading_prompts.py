"""
AI加密货币交易提示词系统
基于Alpha Arena模式和DeepSeek成功经验
"""

from typing import Dict, Any, List
from datetime import datetime

class AlphaArenaPrompt:
    """Alpha Arena风格的交易决策提示"""

    @staticmethod
    def get_decision_prompt(state: Dict[str, Any]) -> str:
        """
        获取交易决策提示词

        Args:
            state: 当前交易状态

        Returns:
            完整的决策提示词
        """
        market_data = state.get("market_data", {})
        positions = state.get("positions", {})
        config = state.get("config", {})

        return f"""
你是专业的AI量化交易员，遵循Alpha Arena竞赛的获胜策略。

=== 当前市场状态 ===
时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

市场数据:
{_format_market_data(market_data)}

当前持仓:
{_format_positions(positions)}

=== Alpha Arena获胜策略 ===
1. **高置信度决策**: 只有置信度>0.8才执行交易
2. **集中投资**: 最多同时持有{config.get('max_positions', 2)}个仓位
3. **高杠杆策略**: 使用{config.get('leverage', 20)}x杠杆放大收益
4. **严格止损**: {config.get('stop_loss_pct', 0.015)*100}%强制止损保护
5. **实时评估**: 每2-3分钟重新评估市场

=== 决策流程 ===
1. 分析当前市场趋势和信号强度
2. 评估技术指标和价格行为
3. 检查持仓风险敞口
4. 确认交易机会的风险收益比
5. 计算置信度 (0-1之间)

=== 输出格式 ===
请严格按照以下JSON格式回复:
{{
    "action": "BUY/SELL/HOLD",
    "symbol": "BTCUSDT/ETHUSDT",
    "confidence": 0.85,
    "reasoning": "详细分析市场情况、信号强度、风险评估...",
    "risk_management": {{
        "stop_loss_pct": 0.015,
        "take_profit_pct": 0.03,
        "position_size_pct": 0.3
    }}
}}

=== 重要提示 ===
- 只在有足够高置信度时交易
- 避免过度交易，保持耐心
- 优先选择强势币种
- 考虑市场情绪和流动性
- 详细说明决策依据
"""

    @staticmethod
    def get_evaluation_prompt(trade_result: Dict[str, Any]) -> str:
        """
        获取交易复盘提示词

        Args:
            trade_result: 交易结果

        Returns:
            复盘分析提示词
        """
        return f"""
分析这次交易的执行情况:

交易详情: {trade_result}

请从以下角度评估:
1. 决策准确性 (置信度vs实际结果)
2. 执行效率 (价格滑点、时机把握)
3. 风险管理 (止损止盈设置)
4. 仓位管理 (大小控制)
5. 学习收获 (可改进的地方)

请提供简洁的评估报告。
"""

    @staticmethod
    def get_risk_warning_prompt(state: Dict[str, Any]) -> str:
        """
        获取风险警告提示词

        Args:
            state: 当前状态

        Returns:
            风险警告提示
        """
        positions = state.get("positions", {})
        active_positions = len([p for p in positions.values() if isinstance(p, dict) and p.get("quantity", 0) > 0])

        return f"""
=== 风险控制检查 ===

当前活跃仓位: {active_positions}
最大允许仓位: {state.get('config', {}).get('max_positions', 2)}

风险检查清单:
1. 是否超过最大仓位限制?
2. 当前杠杆是否过高?
3. 市场波动率是否异常?
4. 是否有未设置止损的订单?
5. 资金使用率是否健康?

如果发现风险，请立即降低风险敞口。

当前状态检查: {_check_risk_state(state)}
"""

class DeepSeekStrategy:
    """DeepSeek通用决策能力实现"""

    @staticmethod
    def get_pattern_recognition_prompt(market_data: Dict[str, Any]) -> str:
        """
        模式识别提示词

        Args:
            market_data: 市场数据

        Returns:
            模式识别提示
        """
        return f"""
使用通用AI推理能力分析市场模式:

市场数据: {market_data}

请识别以下模式:
1. 趋势强度 (强/中/弱)
2. 交易信号 (明确/模糊/无)
3. 市场阶段 (突破/回调/震荡/反转)
4. 关键支撑/阻力位
5. 成交量确认情况

输出模式分析结果，置信度0-1。
"""

    @staticmethod
    def get_adaptive_reasoning_prompt(context: Dict[str, Any]) -> str:
        """
        自适应推理提示词

        Args:
            context: 当前上下文

        Returns:
            自适应推理提示
        """
        return f"""
基于当前上下文进行自适应推理:

{context}

请应用通用AI推理能力:
1. 因果关系分析
2. 概率评估
3. 风险-收益权衡
4. 多维度决策
5. 不确定性处理

输出综合推理结果和置信度。
"""

class ConfidenceAssessment:
    """置信度评估框架"""

    @staticmethod
    def calculate_confidence(market_data: Dict[str, Any], technical_indicators: Dict[str, Any]) -> float:
        """
        计算交易置信度

        Args:
            market_data: 市场数据
            technical_indicators: 技术指标

        Returns:
            0-1之间的置信度值
        """
        confidence = 0.0

        # 价格趋势强度
        trend_strength = _assess_trend_strength(market_data)
        confidence += trend_strength * 0.3

        # 技术指标信号
        signal_strength = _assess_signal_strength(technical_indicators)
        confidence += signal_strength * 0.4

        # 市场条件
        market_condition = _assess_market_condition(market_data)
        confidence += market_condition * 0.2

        # 风险因素
        risk_factor = _assess_risk_factor(technical_indicators)
        confidence -= risk_factor * 0.1

        return max(0.0, min(1.0, confidence))

    @staticmethod
    def get_confidence_breakdown(confidence: float) -> str:
        """
        获取置信度分解说明

        Args:
            confidence: 置信度值

        Returns:
            置信度分解说明
        """
        if confidence >= 0.9:
            return "极高置信度: 所有信号强烈一致，市场条件完美"
        elif confidence >= 0.8:
            return "高置信度: 大部分信号支持，少数不确定"
        elif confidence >= 0.6:
            return "中等置信度: 部分信号支持，需要更多确认"
        elif confidence >= 0.4:
            return "低置信度: 信号模糊，不建议交易"
        else:
            return "极低置信度: 市场信号混乱，建议观望"

# 辅助函数
def _format_market_data(market_data: Dict[str, Any]) -> str:
    """格式化市场数据"""
    if not market_data:
        return "无市场数据"

    formatted = []
    for symbol, data in market_data.items():
        price = data.get("price", 0)
        change = data.get("change_pct_24h", 0)
        trend = data.get("indicators", {}).get("trend", "NEUTRAL")

        formatted.append(
            f"{symbol}: ${price:.2f} (24h变化: {change:+.2f}%, 趋势: {trend})"
        )

    return "\n".join(formatted)

def _format_positions(positions: Dict[str, Any]) -> str:
    """格式化持仓数据"""
    if not positions:
        return "无持仓信息"

    formatted = []
    for symbol, pos in positions.items():
        if symbol == "CASH":
            formatted.append(f"现金: ${pos:.2f}")
        elif pos.get("quantity", 0) > 0:
            formatted.append(
                f"{symbol}: {pos['quantity']:.4f} ({pos['side']}) "
                f"浮盈: ${pos.get('unrealized_pnl', 0):.2f}"
            )

    return "\n".join(formatted) if formatted else "无活跃仓位"

def _assess_trend_strength(market_data: Dict[str, Any]) -> float:
    """评估趋势强度"""
    if not market_data:
        return 0.0

    total_strength = 0.0
    count = 0

    for data in market_data.values():
        change_24h = abs(data.get("change_pct_24h", 0))
        if change_24h > 2.0:
            strength = 0.9
        elif change_24h > 1.0:
            strength = 0.7
        elif change_24h > 0.5:
            strength = 0.5
        else:
            strength = 0.3

        total_strength += strength
        count += 1

    return total_strength / count if count > 0 else 0.0

def _assess_signal_strength(technical_indicators: Dict[str, Any]) -> float:
    """评估信号强度"""
    if not technical_indicators:
        return 0.5

    rsi = technical_indicators.get("rsi", 50)
    macd = technical_indicators.get("macd", 0)
    trend = technical_indicators.get("trend", "NEUTRAL")

    signal_score = 0.0

    # RSI信号
    if 30 <= rsi <= 70:
        signal_score += 0.3
    elif 20 <= rsi <= 80:
        signal_score += 0.2

    # MACD信号
    if macd > 0:
        signal_score += 0.3

    # 趋势信号
    if trend in ["BULLISH", "BEARISH"]:
        signal_score += 0.4

    return min(1.0, signal_score)

def _assess_market_condition(market_data: Dict[str, Any]) -> float:
    """评估市场条件"""
    if not market_data:
        return 0.5

    # 简化处理：基于24小时变化幅度评估流动性
    volatility = sum(abs(data.get("change_pct_24h", 0)) for data in market_data.values())
    avg_volatility = volatility / len(market_data)

    if 0.5 <= avg_volatility <= 2.0:
        return 0.8  # 良好流动性
    elif avg_volatility < 0.5:
        return 0.6  # 低波动
    else:
        return 0.4  # 高波动风险

def _assess_risk_factor(technical_indicators: Dict[str, Any]) -> float:
    """评估风险因素"""
    if not technical_indicators:
        return 0.5

    rsi = technical_indicators.get("rsi", 50)

    # 极值RSI表示高风险
    if rsi > 80 or rsi < 20:
        return 0.8
    elif rsi > 70 or rsi < 30:
        return 0.5
    else:
        return 0.2

def _check_risk_state(state: Dict[str, Any]) -> str:
    """检查风险状态"""
    positions = state.get("positions", {})
    config = state.get("config", {})

    active_count = len([
        p for p in positions.values()
        if isinstance(p, dict) and p.get("quantity", 0) > 0
    ])
    max_allowed = config.get("max_positions", 2)

    if active_count > max_allowed:
        return f"警告: 活跃仓位数({active_count})超过限制({max_allowed})"
    elif active_count == max_allowed:
        return f"注意: 已达到最大仓位限制({max_allowed})"
    else:
        return f"安全: 剩余仓位空间({max_allowed - active_count})"
