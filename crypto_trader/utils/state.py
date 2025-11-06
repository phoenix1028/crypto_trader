#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Graph State Definition
按照LangChain/LangGraph文档规范组织
"""

from datetime import datetime
from typing import Any, Dict, TypedDict


class TradingState(TypedDict):
    """交易状态"""
    timestamp: datetime
    market_data: Dict[str, Any]
    account_info: Dict[str, Any]
    trading_decisions: Dict[str, Any]
    chain_of_thought: str
    trading_decisions_output: str
