#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Trading Tools - LangChain标准工具定义
按照LangChain/LangGraph文档规范，使用@tool装饰器
"""

import asyncio
import json
import hmac
import hashlib
from typing import Any, Dict, Optional, List
import os
import time
import requests
from dotenv import load_dotenv
from langchain_core.tools import tool
from pydantic import BaseModel, Field

# 加载.env文件
load_dotenv(dotenv_path="D:/AI_deepseek_trader/crypto_trader/.env")


# ==================== Pydantic模型定义 ====================

class OrderInput(BaseModel):
    """下单输入参数"""
    symbol: str = Field(description="交易对符号，如 BTCUSDT")
    side: str = Field(description="买卖方向: BUY 或 SELL")
    quantity: float = Field(description="订单数量")
    price: Optional[float] = Field(default=None, description="订单价格，市价单不需要")
    order_type: str = Field(default="MARKET", description="订单类型: MARKET 或 LIMIT")
    reduce_only: bool = Field(default=False, description="是否仅减仓")
    close_position: bool = Field(default=False, description="是否全平")


class LeverageInput(BaseModel):
    """设置杠杆输入参数"""
    symbol: str = Field(description="交易对符号")
    leverage: int = Field(description="杠杆倍数", ge=1, le=125)


class QueryOrderInput(BaseModel):
    """查询订单输入参数"""
    symbol: str = Field(description="交易对符号")
    order_id: Optional[int] = Field(default=None, description="订单ID")
    orig_client_order_id: Optional[str] = Field(default=None, description="客户端订单ID")


class CancelOrderInput(BaseModel):
    """取消订单输入参数"""
    symbol: str = Field(description="交易对符号")
    order_id: Optional[int] = Field(default=None, description="订单ID")
    orig_client_order_id: Optional[str] = Field(default=None, description="客户端订单ID")


# ==================== 币安API客户端 ====================

class BinanceFuturesClient:
    """币安期货API客户端"""

    def __init__(self, testnet: bool = False):
        """初始化客户端"""
        self.testnet = testnet
        self._init_credentials()
        self.session = requests.Session()
        self.session.headers.update({"X-MBX-APIKEY": self.api_key})

    def _init_credentials(self):
        """初始化API凭据"""
        if self.testnet:
            self.api_key = os.getenv("TESTNET_BINANCE_API_KEY")
            self.api_secret = os.getenv("TESTNET_BINANCE_SECRET_KEY")
            self.base_url = "https://testnet.binancefuture.com"
        else:
            self.api_key = os.getenv("BINANCE_API_KEY")
            self.api_secret = os.getenv("BINANCE_SECRET_KEY")
            self.base_url = "https://fapi.binance.com"

        if not self.api_key or not self.api_secret:
            env_name = "TESTNET_BINANCE_API_KEY" if self.testnet else "BINANCE_API_KEY"
            raise ValueError(f"请在.env文件中配置{env_name}和对应的SECRET_KEY")

    def _sign_request(self, params: Dict[str, Any]) -> str:
        """生成API请求签名"""
        # 过滤掉None值并排序
        filtered_params = {k: v for k, v in sorted(params.items()) if v is not None}
        query_string = "&".join([f"{k}={v}" for k, v in filtered_params.items()])
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature

    async def _api_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """发送API请求"""
        if params is None:
            params = {}

        # 记录原始参数用于签名
        params_for_sign = dict(params)

        # 添加时间戳
        timestamp = int(time.time() * 1000)
        params_for_sign["timestamp"] = str(timestamp)

        # 生成签名
        signature = self._sign_request(params_for_sign)

        # 添加签名和时间戳到最终参数
        params["timestamp"] = str(timestamp)
        params["signature"] = signature

        url = f"{self.base_url}{endpoint}"

        try:
            if method == "GET":
                response = self.session.get(url, params=params)
            elif method == "POST":
                # POST请求将参数放在请求体中（form-urlencoded）
                # 将参数字典转换为字符串格式
                form_data = "&".join([f"{k}={v}" for k, v in sorted(params.items())])
                headers = {"Content-Type": "application/x-www-form-urlencoded"}
                response = self.session.post(url, data=form_data, headers=headers)
            elif method == "DELETE":
                response = self.session.delete(url, params=params)
            else:
                raise ValueError(f"不支持的HTTP方法: {method}")

            if response.status_code == 200:
                return {"success": True, "data": response.json()}
            else:
                return {
                    "success": False,
                    "status_code": response.status_code,
                    "error": response.text
                }

        except Exception as e:
            return {"success": False, "error": str(e)}


# 全局客户端实例
_client = None

def get_client() -> BinanceFuturesClient:
    """获取全局客户端实例"""
    global _client
    if _client is None:
        # 检查是否在测试模式 - 优先使用FUTURES_TESTNET配置
        testnet = os.getenv("FUTURES_TESTNET", os.getenv("ENABLE_TESTNET", "true")).lower() == "true"
        _client = BinanceFuturesClient(testnet=testnet)
    return _client


# ==================== LangChain标准工具 ====================

@tool
async def set_leverage_tool(input_data: LeverageInput) -> str:
    """设置交易对杠杆倍数

    Args:
        symbol: 交易对符号，如 BTCUSDT
        leverage: 杠杆倍数 (1-125)
    """
    try:
        client = get_client()
        result = await client._api_request(
            "POST",
            "/fapi/v1/leverage",
            {"symbol": input_data.symbol, "leverage": str(input_data.leverage)}
        )

        if result["success"]:
            data = result["data"]
            return f"[SUCCESS] 成功设置 {data.get('symbol')} 杠杆为 {data.get('leverage')}x"
        else:
            return f"[ERROR] 设置杠杆失败: {result.get('error')}"

    except Exception as e:
        return f"[ERROR] 设置杠杆异常: {str(e)}"


@tool
async def place_order_tool(input_data: OrderInput) -> str:
    """下单交易

    Args:
        symbol: 交易对符号，如 BTCUSDT
        side: 买卖方向 BUY 或 SELL
        quantity: 订单数量
        order_type: 订单类型，MARKET（市价）或 LIMIT（限价）
        price: 限价单价格，市价单不需要
        reduce_only: 是否仅减仓
        close_position: 是否全平
    """
    try:
        client = get_client()

        # 构建参数
        params = {
            "symbol": input_data.symbol,
            "side": input_data.side.upper(),
            "type": input_data.order_type.upper(),
            "quantity": str(input_data.quantity),
            "reduceOnly": "true" if input_data.reduce_only else "false",
            "closePosition": "true" if input_data.close_position else "false"
        }

        if input_data.price is not None:
            params["price"] = str(input_data.price)

        # 执行下单
        result = await client._api_request("POST", "/fapi/v1/order", params)

        if result["success"]:
            data = result["data"]
            action = "平仓" if input_data.reduce_only else "开仓"
            return f"[SUCCESS] 成功{action}: {input_data.side} {input_data.order_type} {input_data.quantity} {input_data.symbol}\n订单ID: {data.get('orderId')}"
        else:
            return f"[ERROR] 下单失败: {result.get('error')}"

    except Exception as e:
        return f"[ERROR] 下单异常: {str(e)}"


@tool
async def query_order_tool(input_data: QueryOrderInput) -> str:
    """查询订单详情

    Args:
        symbol: 交易对符号
        order_id: 订单ID
        orig_client_order_id: 客户端订单ID
    """
    try:
        client = get_client()

        params = {"symbol": input_data.symbol}
        if input_data.order_id is not None:
            params["orderId"] = str(input_data.order_id)
        elif input_data.orig_client_order_id is not None:
            params["origClientOrderId"] = input_data.orig_client_order_id
        else:
            return "[ERROR] 必须提供order_id或orig_client_order_id"

        result = await client._api_request("GET", "/fapi/v1/order", params)

        if result["success"]:
            data = result["data"]
            return f"[SUCCESS] 订单查询成功:\n状态: {data.get('status')}\n数量: {data.get('executedQty')}/{data.get('origQty')}\n价格: {data.get('price')}"
        else:
            return f"[ERROR] 查询订单失败: {result.get('error')}"

    except Exception as e:
        return f"[ERROR] 查询订单异常: {str(e)}"


@tool
async def cancel_order_tool(input_data: CancelOrderInput) -> str:
    """取消订单

    Args:
        symbol: 交易对符号
        order_id: 订单ID
        orig_client_order_id: 客户端订单ID
    """
    try:
        client = get_client()

        params = {"symbol": input_data.symbol}
        if input_data.order_id is not None:
            params["orderId"] = str(input_data.order_id)
        elif input_data.orig_client_order_id is not None:
            params["origClientOrderId"] = input_data.orig_client_order_id
        else:
            return "❌ 必须提供order_id或orig_client_order_id"

        result = await client._api_request("DELETE", "/fapi/v1/order", params)

        if result["success"]:
            return "[SUCCESS] 成功取消订单"
        else:
            return f"[ERROR] 取消订单失败: {result.get('error')}"

    except Exception as e:
        return f"[ERROR] 取消订单异常: {str(e)}"


@tool
async def get_account_balance_tool() -> str:
    """获取账户余额信息"""
    try:
        client = get_client()
        result = await client._api_request("GET", "/fapi/v2/account")

        if result["success"]:
            data = result["data"]
            total_wallet_balance = float(data.get('totalWalletBalance', 0))
            available_balance = float(data.get('availableBalance', 0))

            return f"""[SUCCESS] 账户余额信息:
总余额: {total_wallet_balance:.2f} USDT
可用余额: {available_balance:.2f} USDT
余额更新: {data.get('updateTime')}"""
        else:
            return f"[ERROR] 获取余额失败: {result.get('error')}"

    except Exception as e:
        return f"[ERROR] 获取余额异常: {str(e)}"


@tool
async def get_position_info_tool(symbol: Optional[str] = None) -> str:
    """获取持仓信息

    Args:
        symbol: 交易对符号（可选，不指定则获取所有持仓）
    """
    try:
        client = get_client()
        params = {}
        if symbol:
            params["symbol"] = symbol

        result = await client._api_request("GET", "/fapi/v2/positionRisk", params)

        if result["success"]:
            positions = result["data"]
            if not positions:
                return "[SUCCESS] 当前无持仓"

            output_lines = ["[SUCCESS] 当前持仓信息:"]
            for pos in positions:
                if float(pos.get('positionAmt', 0)) != 0:
                    symbol = pos.get('symbol')
                    position_amt = float(pos.get('positionAmt', 0))
                    entry_price = float(pos.get('entryPrice', 0))
                    unrealized_pnl = float(pos.get('unRealizedProfit', 0))
                    percentage = float(pos.get('percentage', 0))

                    output_lines.append(f"""
{symbol}:
  持仓量: {position_amt:.4f}
  入场价: ${entry_price:.2f}
  未实现盈亏: {unrealized_pnl:.2f} USDT ({percentage:.2f}%)""")

            return "\n".join(output_lines)
        else:
            return f"[ERROR] 获取持仓失败: {result.get('error')}"

    except Exception as e:
        return f"[ERROR] 获取持仓异常: {str(e)}"


@tool
async def get_server_time_tool() -> str:
    """获取服务器时间"""
    try:
        client = get_client()
        result = await client._api_request("GET", "/fapi/v1/time")

        if result["success"]:
            server_time = result["data"]["serverTime"]
            local_time = int(time.time() * 1000)
            return f"""[SUCCESS] 服务器时间信息:
服务器时间: {server_time}
本地时间: {local_time}
时间差: {server_time - local_time}ms"""
        else:
            return f"[ERROR] 获取时间失败: {result.get('error')}"

    except Exception as e:
        return f"[ERROR] 获取时间异常: {str(e)}"


# ==================== 工具列表 ====================
# 🔥 只保留交易相关工具，移除所有数据查询工具
# 数据已通过User Prompt提供，无需查询

TRADING_TOOLS = [
    set_leverage_tool,      # 设置杠杆（开仓前必须）
    place_order_tool,       # 下单交易（核心工具）
    query_order_tool,       # 查询订单（实用工具）
    cancel_order_tool,      # 取消订单（实用工具）
]

if __name__ == "__main__":
    # 测试工具
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    # 简单测试
    async def test_tools():
        print("=== 测试LangChain标准工具 ===")
        # 注意：这里需要配置API密钥才能实际测试
        try:
            result = await get_server_time_tool.ainvoke({})
            print(result)
        except Exception as e:
            print(f"测试失败: {e}")

    asyncio.run(test_tools())
