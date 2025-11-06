# AI加密货币量化交易系统

## 项目概述

这是一个基于DeepSeek AI的加密货币量化交易系统，使用事件驱动架构，结合WebSocket实时数据流和技术指标分析，实现智能交易决策。系统已升级至期货合约交易模式，采用Alpha Arena提示词格式，支持LangSmith监控。

## 核心特性

- ✅ **真正的AI决策**: 使用DeepSeek LLM进行市场分析
- ✅ **实时数据流**: WebSocket监听市场数据，Redis缓存
- ✅ **技术指标**: RSI、MACD、EMA、ATR等（已修复存储问题）
- ✅ **期货合约**: 支持U本位期货合约交易
- ✅ **三级置信度系统**: 高(>0.75)/中(0.6-0.75)/低(<0.6)风险分级
- ✅ **智能工具调用**: LangChain Structured Output + ToolStrategy
- ✅ **LangSmith集成**: AI输出监控和追踪
- ✅ **Alpha Arena格式**: 标准化提示词格式
- ✅ **限流控制**: ReAct最大8次调用限制
- ✅ **自动重连**: WebSocket连接自动处理和重连
- ✅ **测试网模式**: 安全的虚拟资金交易

## 快速开始

### 1. 启动AI交易系统

```bash
cd D:/AI_deepseek_trader
python crypto_trader/core/event_system.py
```

系统将：
- 初始化WebSocket数据引擎（期货合约数据）
- 连接Redis缓存
- 启动AI交易Agent
- 监听市场数据并做交易决策

### 2. 测试交易工具

```bash
python crypto_trader/test/test_trading_only_tools.py
```

### 3. 测试置信度逻辑

```bash
python crypto_trader/test/test_confidence_logic.py
```

### 4. 完整系统测试

```bash
python crypto_trader/test/test_comprehensive_integration.py
```

## 系统架构

```
┌─────────────────────────────────────────┐
│       EventDrivenTradingSystem         │
│         (事件驱动主协调器)                │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│           DataEngine                    │
│    (WebSocket + Redis + 指标计算)        │
│  - NumPy类型转换                         │
│  - 预加载历史K线                         │
│  - 期货合约数据                          │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│      TradingAgentV3 (Alpha Arena)       │
│      (DeepSeek AI决策引擎)              │
│  ┌─ ToolStrategy + Structured Output   │
│  ├─ 3-Level Confidence System          │
│  ├─ ReAct Call Limit (Max 8)          │
│  └─ LangSmith Integration             │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│         AlphaArenaFormatter             │
│      (标准化市场数据格式)                │
│  - Real Market Data (Binance API)      │
│  - Technical Indicators (Fixed)        │
│  - Market Sentiment Analysis           │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│         DeepSeek API                    │
│        (真正AI分析)                      │
└─────────────────────────────────────────┘
```

## 核心更新日志

### v2.0.0 (2025-11-05) - Alpha Arena架构升级

#### 🔧 数据层修复
- ✅ **技术指标修复**: 修复EMA、MACD、ATR、RSI显示0.0/50.0问题
- ✅ **NumPy类型转换**: 实现Redis存储前的Python原生类型转换
- ✅ **字段映射修复**: 修复macd_line vs macd字段名不匹配问题
- ✅ **历史数据预加载**: 自动预加载足够的历史K线数据用于指标计算
- ✅ **期货合约切换**: 完全切换至U本位期货合约数据

#### 🤖 AI系统升级
- ✅ **Alpha Arena格式**: 集成标准化的Alpha Arena提示词格式
- ✅ **LangSmith集成**: 添加AI输出可观测性和追踪
- ✅ **Structured Output**: 使用Pydantic模型确保类型安全
- ✅ **ToolStrategy**: LangChain v1.0+ 工具调用机制
- ✅ **三级置信度系统**:
  - 高置信度(>0.75): 2%风险单元
  - 中置信度(0.6-0.75): 1%风险单元
  - 低置信度(<0.6): HOLD无仓位

#### 🛠️ 工具优化
- ✅ **精简工具集**: 保留4个核心交易工具
  - set_leverage_tool
  - place_order_tool
  - query_order_tool
  - cancel_order_tool
- ✅ **移除数据查询**: 删除所有数据获取工具（数据来自User Prompt）
- ✅ **ReAct限流**: ToolCallLimitMiddleware限制最大8次调用
- ✅ **System Prompt**: 完整系统提示词 + 工具调用限制说明

#### ⚡ 性能优化
- ✅ **智能触发器**: 修复频率控制逻辑（120次/小时）
- ✅ **AND条件优化**: 修复智能触发器OR/AND逻辑错误
- ✅ **Redis状态管理**: 优化系统状态更新和显示

## 配置文件

### AI配置 (.env)

```env
# DeepSeek API密钥
OPENAI_API_KEY=your_api_key

# API基础URL
OPENAI_BASE_URL=https://api.deepseek.com

# 模型名称
OPENAI_MODEL=deepseek-chat

# LangSmith配置（可选）
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your_langsmith_key
```

### 交易配置

```env
# 测试网模式（true=虚拟资金，false=真实资金）
ENABLE_TESTNET=true

# 三级置信度配置
HIGH_CONFIDENCE_THRESHOLD=0.75
MEDIUM_CONFIDENCE_THRESHOLD=0.60

# 杠杆倍数
LEVERAGE=20

# 风险单元配置
HIGH_RISK_UNIT=0.02
MEDIUM_RISK_UNIT=0.01
LOW_RISK_UNIT=0.00

# 最大持仓数量
MAX_POSITIONS=2
```

### 币安API配置

```env
# 测试网API（开发用）
TESTNET_BINANCE_API_KEY=your_testnet_key
TESTNET_BINANCE_SECRET_KEY=your_testnet_secret

# 生产网API（真实交易用）
BINANCE_API_KEY=your_production_key
BINANCE_SECRET_KEY=your_production_secret
```

## 交易决策流程

### 1. 数据收集
- WebSocket实时价格数据（期货合约）
- 技术指标计算（RSI、MACD、EMA等）- 已修复存储问题
- Alpha Arena格式标准化
- 市场情绪分析

### 2. AI分析
- 使用Alpha Arena格式提示词
- DeepSeek分析价格趋势、技术指标、市场情绪
- 生成结构化交易信号（BUY/SELL/HOLD）
- 置信度评分（0-1）
- LangSmith追踪记录

### 3. 三级风险决策
- **高置信度(>0.75)**: 执行交易，使用2%风险单元
- **中置信度(0.6-0.75)**: 执行交易，使用1%风险单元
- **低置信度(<0.6)**: HOLD观望，不建仓位

### 4. 工具调用
- ReAct循环最多8次调用
- 优先使用结构化工具输出
- 降级机制确保稳定性

## Alpha Arena提示词格式

### System Prompt (简化版)
```
你是一个专业的加密货币期货交易员。

决策框架：
1. 市场趋势分析
2. 技术指标确认
3. 风险管理

三级置信度系统：
- 高置信度(>0.75): 2%风险单元
- 中置信度(0.6-0.75): 1%风险单元
- 低置信度(<0.6): HOLD无仓位

工具调用限制：最大8次ReAct调用
```

### User Prompt (数据格式)
```
Alpha Arena Market Snapshot:
Symbol: BTCUSDT
Current Price: $103,500.00
24h Change: +2.50%

Technical Indicators:
- RSI(14): 65.5
- EMA(20): $102,800.00
- MACD: 150.25
- ATR(14): 1,250.00

Recent Klines (Last 5):
[OHLCV data...]

请分析并输出交易决策。
```

## 技术亮点

### 1. NumPy类型转换
```python
# 修复Redis存储的NumPy类型问题
def _convert_numpy_types(obj):
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    return obj
```

### 2. Alpha Arena格式化
```python
# 标准化市场数据格式
def format_for_ai(self, symbol: str, market_data: dict) -> dict:
    return {
        "symbol": symbol,
        "current_price": market_data.get('price', 0),
        "change_24h": market_data.get('change_24h', 0),
        "technical_indicators": {
            "rsi": redis_data.get('rsi', 0),
            "ema20": redis_data.get('ema20', 0),
            "macd": redis_data.get('macd', 0),
            "atr": redis_data.get('atr', 0)
        },
        # ...
    }
```

### 3. 结构化输出
```python
# 使用Pydantic模型确保类型安全
class TradingDecision(BaseModel):
    symbol: str
    action: str  # BUY/SELL/HOLD
    confidence: float
    reasoning: str
    risk_unit: float
```

### 4. 三级置信度逻辑
```python
def _calculate_risk_unit(self, confidence: float) -> float:
    if confidence > 0.75:
        return 0.02  # 2%
    elif confidence >= 0.60:
        return 0.01  # 1%
    else:
        return 0.00  # HOLD
```

## 目录结构

```
AI_deepseek_trader/
├── crypto_trader/
│   ├── core/                    # 核心模块
│   │   ├── event_system.py      # 事件系统主程序
│   │   ├── data_engine.py       # WebSocket数据引擎（已修复）
│   │   ├── smart_trigger.py     # 智能触发器（已修复）
│   │   └── redis_manager.py     # Redis管理
│   ├── agent/
│   │   └── trading_agent.py     # AI交易Agent v3 (Alpha Arena)
│   ├── configs/
│   │   └── config.py            # 系统配置（期货）
│   ├── utils/
│   │   ├── tools.py             # 交易工具（仅4个）
│   │   ├── alpha_arena_prompt.py # Alpha Arena格式
│   │   └── market_data.py       # 市场数据
│   └── test/                    # 测试套件
│       ├── test_ai_decision.py
│       ├── test_confidence_logic.py
│       ├── test_trading_only_tools.py
│       └── ... (共42个测试文件)
├── README.md                    # 项目文档
├── CLAUDE.md                    # 项目说明
└── .gitignore                   # Git忽略文件
```

## 测试套件

### 核心测试
- `test_ai_decision.py` - AI决策测试
- `test_confidence_logic.py` - 三级置信度逻辑测试
- `test_trading_only_tools.py` - 交易工具测试
- `test_comprehensive_integration.py` - 完整集成测试

### 数据质量测试
- `test_indicators_fix_verification.py` - 技术指标修复验证
- `test_numpy_types.py` - NumPy类型转换测试
- `test_real_market_data.py` - 真实市场数据测试
- `test_data_flow.py` - 数据流测试

### 提示词测试
- `test_alpha_arena_prompt_fixed.py` - Alpha Arena格式测试
- `test_event_system_alpha_arena.py` - 系统集成测试

**总计**: 42个测试文件（已移至crypto_trader/test/目录）

## 故障排除

### 1. WebSocket错误
如果看到 "Read loop has been closed" 错误：
- 这是正常现象，系统会自动重连
- 已在data_engine.py中实现自动重连机制

### 2. 技术指标显示0.0
已修复：
- NumPy类型转换问题
- 字段映射问题（macd_line -> macd）
- 历史数据预加载问题

### 3. AI决策格式错误
已修复：
- 使用ToolStrategy + Structured Output
- Pydantic模型确保类型安全
- _convert_decision_format()方法

### 4. 工具调用失败
已修复：
- 精简工具集至4个核心交易工具
- 移除数据查询工具
- ReAct最大8次调用限制
- System Prompt完整性

### 5. 触发频率异常
已修复：
- 修复OR/AND逻辑错误
- 全局间隔控制机制
- Redis计数器重置优化

## 性能监控

系统提供实时监控：
- WebSocket连接状态
- Redis缓存状态
- AI决策次数和置信度分布
- 系统运行时间
- 处理事件总数
- LangSmith追踪数据

## 风险提示

1. **仅使用测试网**: 当前配置使用测试网，虚拟资金，无风险
2. **AI仅供参考**: AI决策仅供参考，实际交易需谨慎
3. **风险控制**: 严格遵循三级置信度和仓位管理
4. **实时监控**: 建议实时监控系统运行状态和LangSmith数据
5. **期货交易**: 使用杠杆交易，注意风险控制

## 更新日志

### v2.0.0 (2025-11-05) - Alpha Arena架构升级
- ✅ Alpha Arena提示词格式集成
- ✅ LangSmith可观测性集成
- ✅ ToolStrategy + Structured Output机制
- ✅ 三级置信度系统（0.6/0.75/0.75+）
- ✅ 技术指标存储问题修复
- ✅ NumPy类型转换修复
- ✅ 字段映射问题修复
- ✅ 历史数据预加载
- ✅ 期货合约数据切换
- ✅ 智能触发器频率修复
- ✅ 工具集精简（4个交易工具）
- ✅ ReAct最大8次调用限制
- ✅ System Prompt完整性

### v1.0.0 (2024-11-05)
- ✅ 启用真正的AI决策（DeepSeek）
- ✅ 修复WebSocket重连问题
- ✅ 修复Redis数据获取问题
- ✅ 完善错误处理机制
- ✅ 添加完整的测试套件

## 技术支持

系统开发者: AI Assistant
项目地址: D:\\AI_deepseek_trader

---

**⚠️ 重要提醒**: 这是一个AI交易系统原型，仅供学习和研究使用。期货交易有杠杆风险，请谨慎决策。
