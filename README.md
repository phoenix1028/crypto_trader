# AI加密货币量化交易系统

基于DeepSeek AI的智能期货交易系统，采用LangChain Agent架构，实现自动化交易决策与执行。

## 核心特性

- **AI驱动交易**: DeepSeek LLM分析市场数据并生成交易信号
- **实时数据流**: WebSocket监听市场数据，Redis缓存技术指标
- **期货交易**: 支持币安U本位期货合约，自动杠杆管理
- **风险控制**: 三级置信度系统（高>0.75/中0.6-0.75/低<0.6）
- **智能工具调用**: LangChain Agent自动调用交易工具（杠杆/下单/查询/取消）
- **事件驱动**: 基于市场信号触发AI决策流程

## 快速开始

### 1. 启动交易系统

```bash
cd D:/AI_deepseek_trader
python crypto_trader/core/event_system.py
```

### 2. 测试交易工具

```bash
python crypto_trader/test/test_trading_only_tools.py
```

## 系统架构

```
市场数据流 → 技术指标计算 → AI分析决策 → Agent工具调用 → 交易执行
    ↓           ↓           ↓           ↓           ↓
WebSocket →  Redis缓存  → DeepSeek  → LangChain  → 币安API
期货数据    指标存储      LLM分析     Agent工具     订单执行
```

## 核心组件

### 1. 事件系统 (`event_system.py`)
主协调器，管理数据流、触发器、AI决策和交易执行

### 2. 数据引擎 (`data_engine.py`)
WebSocket数据采集 + Redis缓存 + 技术指标计算（RSI、MACD、EMA、ATR）

### 3. 交易Agent (`trading_agent.py`)
DeepSeek AI决策引擎，使用LangChain Agent架构进行工具调用

### 4. 交易工具 (`tools.py`)
- `set_leverage_tool`: 设置杠杆倍数
- `place_order_tool`: 下单交易
- `query_order_tool`: 查询订单
- `cancel_order_tool`: 取消订单

### 5. Alpha Arena格式化 (`alpha_arena_formatter.py`)
标准化市场数据格式，优化AI分析输入

## 配置文件

### 环境变量 (.env)

```env
# DeepSeek API
OPENAI_API_KEY=your_api_key
OPENAI_BASE_URL=https://api.deepseek.com
OPENAI_MODEL=deepseek-chat

# 交易配置
ENABLE_TESTNET=true
LEVERAGE=20
HIGH_CONFIDENCE_THRESHOLD=0.75
MEDIUM_CONFIDENCE_THRESHOLD=0.60
HIGH_RISK_UNIT=0.02
MEDIUM_RISK_UNIT=0.01

# 币安API（测试网）
TESTNET_BINANCE_API_KEY=your_key
TESTNET_BINANCE_SECRET_KEY=your_secret
```

## 交易流程

1. **数据采集**: WebSocket接收实时期货价格数据
2. **指标计算**: 计算RSI、MACD、EMA、ATR等技术指标
3. **AI分析**: DeepSeek分析市场趋势和技术指标
4. **置信度评级**: AI生成0-1置信度评分
5. **风险决策**:
   - 高置信度(>0.75): 使用2%风险单元
   - 中置信度(0.6-0.75): 使用1%风险单元
   - 低置信度(<0.6): HOLD不交易
6. **工具调用**: LangChain Agent自动调用交易工具执行订单
7. **订单监控**: 实时跟踪订单状态和执行结果

## 测试

系统包含完整的测试套件：
- AI决策逻辑测试
- 置信度系统测试
- 交易工具测试
- 事件系统集成测试

## 风险提示

⚠️ **重要提醒**:
- 当前使用测试网模式，虚拟资金无风险
- AI决策仅供参考，实际交易需谨慎
- 期货交易具有杠杆风险，请严格管理仓位
- 建议在充分测试后应用于实盘交易

---

## 商业合作
- 若有商业合作请发送邮箱至980499184@qq.com
