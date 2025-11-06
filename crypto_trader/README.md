# 事件驱动型AI量化交易系统

[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

基于事件驱动架构的AI量化交易系统，专为期货合约交易设计，集成LangGraph AI决策引擎和Redis数据缓存。

## ✨ 核心特性

### 🚀 高性能事件驱动
- **实时WebSocket数据流**：连接币安期货市场，获取15个并发数据流
- **毫秒级响应**：异步事件处理，实时响应市场变化
- **智能数据缓存**：Redis高效存储，跨组件数据共享

### 🤖 AI驱动决策
- **LangGraph集成**：基于状态图的AI决策引擎
- **AlphaArena策略**：专业量化交易策略（置信度>0.8，集中投资）
- **智能风险控制**：多层验证机制，确保交易安全

### 🎯 智能触发机制
- **动态频率控制**：基于市场波动的自适应触发
- **API保护机制**：120次/小时AI调用限制，避免过度消耗
- **兜底保障**：5分钟无数据强制触发，确保系统活跃

## 📊 交易标的

支持6大主流币种期货交易：
- **BTCUSDT** - 比特币
- **ETHUSDT** - 以太坊
- **SOLUSDT** - Solana
- **BNBUSDT** - 币安币
- **XRPUSDT** - Ripple
- **DOGEUSDT** - 狗狗币

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                    事件驱动AI交易系统                         │
├─────────────────────────────────────────────────────────────┤
│  WebSocket数据流 → 数据引擎 → Redis缓存 → 智能触发器 → AI Agent │
│       ↓              ↓          ↓           ↓            ↓     │
│    市场价格      技术指标     实时状态    事件过滤      决策执行 │
└─────────────────────────────────────────────────────────────┘
```

### 核心组件

| 组件 | 文件 | 功能描述 |
|------|------|----------|
| 事件系统 | `core/event_system.py` | 主协调器，系统生命周期管理 |
| 数据引擎 | `core/data_engine.py` | WebSocket数据监听与处理 |
| 智能触发器 | `core/smart_trigger.py` | AI调用时机控制 |
| Agent集成 | `core/agent_integration.py` | LangGraph桥接层 |
| Redis管理 | `services/redis_manager.py` | 数据缓存与状态管理 |
| 交易Agent | `agent/agent.py` | AI决策引擎 |

## 🚀 快速开始

### 环境要求

- Python 3.12+
- Redis Server
- 币安期货API密钥

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置环境变量

创建 `.env` 文件：

```bash
# 币安API配置
BINANCE_API_KEY=your_api_key
BINANCE_SECRET_KEY=your_secret_key

# DeepSeek AI配置
OPENAI_API_KEY=your_openai_api_key
OPENAI_BASE_URL=https://api.deepseek.com

# Redis配置
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
```

### 启动系统

```bash
python crypto_trader/core/event_system.py
```

### 监控运行状态

```bash
# 查看AI调用次数
python -c "from crypto_trader.services.redis_manager import redis_manager; print(f'AI调用次数: {redis_manager.get_ai_call_count()}')"

# 查看系统状态
python -c "from crypto_trader.services.redis_manager import redis_manager; import json; print(json.dumps(redis_manager.get_system_status(), indent=2, ensure_ascii=False))"
```

## ⚙️ 配置参数

### 智能触发器
```python
MIN_CALL_INTERVAL = 30          # 最小调用间隔（秒）
PRICE_VOLATILITY_THRESHOLD = 0.002  # 价格波动阈值（0.2%）
FALLBACK_INTERVAL = 300         # 兜底间隔（秒）
```

### 风险控制
```python
CONFIDENCE_THRESHOLD = 0.8      # AI决策置信度阈值
MAX_POSITIONS = 2               # 最大同时持仓数
STOP_LOSS_PERCENT = 0.015       # 止损比例（1.5%）
LEVERAGE = 20                   # 杠杆倍数
```

### AI调用限制
```python
MAX_AI_CALLS_PER_HOUR = 120     # 每小时最大AI调用次数
REDIS_EXPIRE_TIME = 3600        # 计数器重置时间（1小时）
```

## 📈 实际运行表现

### 系统状态（2025-11-04）

```
✅ WebSocket连接：已连接，监听15个数据流
✅ Redis连接：已连接，数据缓存正常
✅ 数据引擎：正常运行，处理K线数据
✅ 智能触发器：正常工作，频率控制有效
✅ AI集成：已集成，等待决策触发

📊 处理事件：1,000+
🤖 AI决策次数：7次
⏱️ 运行时间：2小时+
💰 实时价格：BTC $104,908, ETH $3,541
```

### 性能指标

- **响应延迟**：< 100ms
- **数据吞吐量**：15并发流/秒
- **Redis延迟**：< 1ms
- **AI决策速度**：平均2-3秒

## 🛡️ 安全机制

### 多层保护
1. **触发层**：智能触发器控制调用频率
2. **决策层**：AI置信度阈值验证
3. **执行层**：默认禁用真实交易
4. **监控层**：实时状态监控

### 降级策略
- Redis连接失败 → 内存缓存
- Agent不可用 → 暂停AI决策
- 网络异常 → 自动重连

## 📚 文档

- [`docs/PROJECT_SUMMARY.md`](docs/PROJECT_SUMMARY.md) - 详细项目总结
- [`docs/SYSTEM_SUMMARY.md`](docs/SYSTEM_SUMMARY.md) - 系统架构文档
- [`docs/flowchart.txt`](docs/flowchart.txt) - 系统流程图

## 🔧 开发指南

### 项目结构
```
crypto_trader/
├── configs/          # 配置文件
├── core/            # 核心业务逻辑
├── services/        # 服务层
├── utils/           # 工具模块
├── agent/           # AI Agent
├── prompts/         # 提示词
└── docs/            # 文档
```

### 测试
```bash
# 测试Redis连接
python -c "from crypto_trader.services.redis_manager import redis_manager; print('OK' if redis_manager.is_connected() else 'FAIL')"

# 测试数据引擎
python -c "from crypto_trader.core.data_engine import DataEngine; print('OK')"

# 测试智能触发器
python -c "from crypto_trader.core.smart_trigger import smart_trigger; print('OK')"
```

## 📊 交易策略

### AlphaArena策略
- **高置信度要求**：只有置信度>0.8才考虑交易
- **集中投资**：最多同时持有2个仓位
- **高杠杆使用**：20倍杠杆放大收益
- **严格止损**：1.5%止损比例保护本金

### 风险管理
- **动态阈值**：根据市场波动率调整参数
- **实时监控**：持续监控账户和持仓状态
- **异常处理**：完善的错误恢复机制

## 🚨 注意事项

1. **风险警示**：本系统用于期货交易，存在高风险，请谨慎使用
2. **API限制**：请确保币安API有足够的权限和配额
3. **网络稳定**：建议在稳定网络环境下运行
4. **资金安全**：首次使用建议先在测试环境验证

## 🤝 贡献

欢迎提交Issue和Pull Request来改进项目。

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

## 👨‍💻 作者

AI量化交易团队

---

**事件驱动AI交易系统** - 让AI为你的交易决策保驾护航 🚀
