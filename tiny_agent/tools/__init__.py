from tiny_agent.tools.eco.fin import get_currency_exchange_rate, get_stock_data
from typing import Callable

CODING_TOOLS: dict[str, Callable] = {
    "get_stock_data": get_stock_data,
    "get_currency_exchange_rate": get_currency_exchange_rate,
}
