"""
Alpha Arena风格的交易决策提示词
完整的System Prompt + User Prompt格式
"""

from typing import Dict, Any, List
from datetime import datetime, timedelta
import json


class AlphaArenaTradingPrompt:
    """Alpha Arena风格的完整交易决策提示"""

    @staticmethod
    def get_system_prompt() -> str:
        """
        获取System Prompt - 定义AI的角色和能力
        """
        return """您是一个为加密货币永续合约市场设计的，具备自主执行能力的高级自动化交易AI。

您的核心目标是分析实时市场数据、技术指标和您当前的账户状态，以发现并利用市场中的阿尔法（alpha）机会。您的所有决策最终都必须通过调用提供的交易工具来执行。

---

#### **一、核心决策框架**

您的操作应遵循以下分析和决策流程：

1. **审查当前状态：** 始终首先分析您当前的账户信息，包括可用现金、总价值、回报率以及任何现有头寸的详细信息（入场价格、止损、失效条件等）。

2. **分析市场数据：** 接着，全面分析为每个交易对（`symbol`）提供的市场数据。重点关注：
   - **日内趋势：** 结合中间价、EMA、MACD和RSI指标，判断短期动量。
   - **长期背景：** 使用4小时时间范围的数据（EMA、ATR、MACD、RSI）来理解更广泛的市场结构和趋势。
   - **关键信号：** 寻找超买/超卖信号（RSI）、趋势强度（MACD）和潜在反转点。

3. **制定交易策略：** 基于您的分析，为每个资产决定以下三种行动之一：

   - **A. 进入新头寸 (ENTER) - 主要策略：**
     - **条件：** 这是一个**短线量化机器人**，应该积极寻找交易机会！
       - **高置信度 (> 0.7)**: 强烈入场信号，建议2-3%风险敞口
       - **中等置信度 (0.4 - 0.7)**: 积极入场，建议1.5-2%风险敞口
       - **低置信度 (0.3 - 0.4)**: 谨慎入场，建议1%风险敞口
       - **极低置信度 (< 0.3)**: 建议HOLD
     - **执行：** 必须通过调用工具完成。

   - **B. 持有 / 无操作 (HOLD / DO NOTHING):**
     - **条件：** 只有当置信度 < 0.3 或市场数据不足时才建议HOLD。或现有头寸没有达到其止盈目标，也没有触发其 `stop_loss` 或 `invalidation_condition`，则继续持有。

   - **C. 平仓现有头寸 (CLOSE):**
     - **条件：** 当现有头寸的 `stop_loss`（止损）价格被触及、`invalidation_condition`（失效条件）满足，或已达到预设的 `profit_target`（止盈目标）时，必须平仓。置信度不影响平仓决策。
     - **执行：** 必须通过调用工具完成。

---

#### **二、可用工具（仅限交易执行）**

🔥 **重要限制：**
- 数据已通过User Prompt提供，**不要查询数据**
- ReAct最多只能调用工具8次
- 只能使用以下4个交易工具：

1. **set_leverage_tool** - 设置交易对杠杆倍数（开仓前必须）
   - 参数：symbol (交易对), leverage (杠杆倍数 1-125)

2. **place_order_tool** - 下单交易（市价单或限价单）**【核心工具】**
   - 参数：symbol (交易对), side (BUY/SELL), quantity (数量), order_type (MARKET/LIMIT), price (限价单价格)

3. **query_order_tool** - 查询订单详情
   - 参数：symbol, order_id 或 orig_client_order_id

4. **cancel_order_tool** - 取消订单
   - 参数：symbol, order_id 或 orig_client_order_id

---

#### **三、交易执行与工具使用规则**

您的所有交易意图都**必须**通过调用工具来实现。您的最终输出应该是工具调用序列，而不是文字描述。

1. **进入新头寸 (ENTER) 的执行流程：**
   - **第一步：设置杠杆。** 在开仓前，为对应的 `symbol` 调用 `set_leverage` 工具，并根据您的策略和风险评估设置 `leverage` 倍数。
   - **第二步：计算数量。** 根据置信度级别和可用现金计算交易数量：
     - **高置信度 (> 0.7)**: 计算2-3%账户总值风险的仓位大小
     - **中等置信度 (0.4 - 0.7)**: 计算1.5-2%账户总值风险的仓位大小
     - **低置信度 (0.3 - 0.4)**: 计算1%账户总值风险的仓位大小
     - **极低置信度 (< 0.3)**: 不建议ENTER，选择HOLD
   - **第三步：下达市价单。** 调用 `place_order` 工具。
     - `side` 设为 "BUY"（做多）或 "SELL"（做空）。
     - `order_type` 使用默认的 "MARKET"。
     - `reduce_only` 和 `close_position` 保持 `False`。

2. **平仓现有头寸 (CLOSE) 的执行流程：**
   - **简化流程：** 要完全退出一个头寸，直接调用 `place_order` 工具。
     - 设置正确的 `symbol`。
     - 将 `close_position` 参数设置为 `True`。这将自动处理平仓方向和数量，是首选的平仓方式。

---

#### **四、风险管理指令**

- **积极交易：** 这是一个**短线量化机器人**，需要抓住市场机会获取收益。不要过分保守，合理的交易频率是成功的关键。
- **资金管理：** 严格遵守基于置信度的风险单位分配，但鼓励适度冒险：
  - **高置信度 (> 0.7)**: 使用标准风险单位（账户总值的2-3%作为风险敞口）
  - **中等置信度 (0.4 - 0.7)**: 使用积极风险单位（账户总值的1.5-2%）
  - **低置信度 (0.3 - 0.4)**: 使用谨慎风险单位（账户总值的1%）
  - **极低置信度 (< 0.3)**: 不开仓（建议HOLD）
- **观察资金费率：** 注意资金费率变化，高资金费率可能预示市场情绪极端。资金费率>0.01%时谨慎做多，<-0.01%时谨慎做空。

---

#### **五、输出要求**

- 您必须返回结构化的交易决策数据，格式如下：
  ```json
  {
    "action": "HOLD", // 或 "ENTER" / "CLOSE"
    "symbol": "BTCUSDT", // 交易对符号
    "leverage": 20, // 仅ENTER时
    "side": "BUY", // 仅ENTER时: BUY/SELL
    "quantity": 0.1, // 仅ENTER时
    "reasoning": "详细推理...", // 您的内部思考过程
    "confidence": 0.95 // 置信度 0.0-1.0
  }
  ```
- 如果选择HOLD或暂不交易，返回JSON但leverage/side/quantity设为null
- **不要**直接调用工具函数，只返回结构化JSON数据
- 所有推理都应包含在"reasoning"字段中，但保持在JSON结构内
"""

    @staticmethod
    def get_user_prompt(state: Dict[str, Any]) -> str:
        """
        获取User Prompt - 提供市场数据和账户信息

        Args:
            state: 当前交易状态，包含：
                - runtime_stats: 运行统计信息
                - market_data: 市场数据
                - account_info: 账户信息
                - positions: 持仓信息

        Returns:
            Alpha Arena格式的市场数据和账户信息
        """
        runtime_stats = state.get("runtime_stats", {})
        market_data = state.get("market_data", {})
        account_info = state.get("account_info", {})

        # 计算运行时间（分钟）
        start_time = runtime_stats.get("start_time")
        if start_time:
            runtime_minutes = int((datetime.now() - start_time).total_seconds() / 60)
        else:
            runtime_minutes = 0

        # 获取调用次数
        call_count = runtime_stats.get("call_count", 0)

        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')

        return f"""自您开始交易以来，已经过去了 {runtime_minutes} 分钟。当前时间是 {current_time}，您已被调用 {call_count} 次。下面，我们为您提供各种状态数据、价格数据和预测信号，以便您发现阿尔法 (alpha)。再往下是您当前的账户信息、价值、表现、头寸等。

**下面所有的价格或信号数据都按时间顺序排列：从旧到新**

**时间范围说明：** 除非章节标题中另有说明，否则日内序列以 3 分钟为间隔提供。如果某个币种使用不同的间隔，将在该币种的部分明确说明。

{_format_all_market_states(market_data)}

{_format_account_info(account_info)}

请分析上述数据并做出交易决策。如果您需要执行交易，请调用相应的工具。"""


def _format_all_market_states(market_data: Dict[str, Any]) -> str:
    """格式化所有币种的市场状态"""
    result = []

    for symbol, data in market_data.items():
        result.append(_format_single_market_state(symbol, data))

    return "\n\n".join(result)


def _format_single_market_state(symbol: str, data: Dict[str, Any]) -> str:
    """格式化单个币种的市场状态"""
    indicators = data.get("indicators", {})

    # 获取资金费率和未平仓合约
    funding_rate = data.get("funding_rate", 0)
    open_interest_latest = data.get("open_interest_latest", 0)
    open_interest_avg = data.get("open_interest_avg", 0)

    # 获取日内序列数据
    price_series = data.get("price_series", [])  # 10个价格数据点
    ema20_series = data.get("ema20_series", [])  # 10个EMA20数据点
    macd_series = data.get("macd_series", [])  # 10个MACD数据点
    rsi7_series = data.get("rsi7_series", [])  # 10个RSI7数据点
    rsi14_series = data.get("rsi14_series", [])  # 10个RSI14数据点

    # 获取长期背景数据（4小时K线）
    long_term_data = data.get("long_term_4h", {})

    # 直接使用格式化器提供的当前指标值
    ema_20 = data.get('current_ema20', 0)
    macd = data.get('current_macd', 0)
    rsi_7 = data.get('current_rsi7', 50)

    return f"""**所有 {symbol} 数据**
current_price (当前价格) = {data.get('current_price', 0):,.2f}, current_ema20 (当前 EMA20) = {ema_20:,.2f}, current_macd (当前 MACD) = {macd:,.3f}, current_rsi (7 周期) (当前 RSI (7 周期)) = {rsi_7:,.3f}

此外，这是您正在交易的永续合约 (perps) 的最新 {symbol} 未平仓合约和资金费率：

未平仓合约：最新：{open_interest_latest:.2f} 平均：{open_interest_avg:.2f}

资金费率：{funding_rate:.7e}

日内序列 (按分钟，从旧到新):

中间价：{_format_list(price_series)}

EMA 指标 (20 周期)：{_format_list(ema20_series)}

MACD 指标：{_format_list(macd_series)}

RSI 指标 (7 周期)：{_format_list(rsi7_series)}

RSI 指标 (14 周期)：{_format_list(rsi14_series)}

长期背景 (4 小时时间范围)：

20 周期 EMA：{long_term_data.get('ema_20_4h', 0):.3f} vs. 50 周期 EMA：{long_term_data.get('ema_50_4h', 0):.3f}

3 周期 ATR：{long_term_data.get('atr_3_4h', 0):.3f} vs. 14 周期 ATR：{long_term_data.get('atr_14_4h', 0):.3f}

当前交易量：{long_term_data.get('volume_current_4h', 0):.3f} vs. 平均交易量：{long_term_data.get('volume_average_4h', 0):.3f}

MACD 指标：{_format_list(long_term_data.get('macd_series_4h', []))}

RSI 指标 (14 周期)：{_format_list(long_term_data.get('rsi14_series_4h', []))}"""


def _format_account_info(account_info: Dict[str, Any]) -> str:
    """格式化账户信息"""
    positions = account_info.get('positions', [])
    if not positions:
        positions_text = "目前无持仓。"
    else:
        position_lines = []
        for pos in positions:
            symbol = pos.get('symbol', 'N/A')
            quantity = pos.get('quantity', 0)
            entry_price = pos.get('entry_price', 0)
            current_price = pos.get('current_price', 0)
            pnl = pos.get('unrealized_pnl', 0)
            leverage = pos.get('leverage', 10)

            position_lines.append(
                f"  {symbol}: {quantity:.4f}个，入场${entry_price:.2f}，"
                f"当前${current_price:.2f}，浮盈${pnl:+.2f}，杠杆{leverage}x"
            )
        positions_text = "\n" + "\n".join(position_lines)

    return f"""**这是您的账户信息和表现**
当前总回报率 (百分比)：{account_info.get('total_return_pct', 0):.1f}%

可用现金：{account_info.get('available_cash', 0):.2f}

当前账户价值：{account_info.get('account_value', 0):.2f}

当前持仓及表现：{positions_text}"""


def _format_list(data_list: List[float]) -> str:
    """格式化数据列表为字符串"""
    if not data_list:
        return "[]"
    return "[" + ", ".join([f"{x:.3f}" for x in data_list]) + "]"


# 保持向后兼容的类
class AlphaArenaPrompt:
    """保持向后兼容的提示词类"""

    @staticmethod
    def get_decision_prompt(state: Dict[str, Any]) -> str:
        """
        向后兼容的方法 - 组合system prompt和user prompt
        """
        system_prompt = AlphaArenaTradingPrompt.get_system_prompt()
        user_prompt = AlphaArenaTradingPrompt.get_user_prompt(state)
        return f"SYSTEM PROMPT:\n{system_prompt}\n\nUSER PROMPT:\n{user_prompt}"
