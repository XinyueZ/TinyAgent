from typing import Callable

from tiny_agent.tools.buildins.utils import (
    get_current_datetime_in_local,
    get_current_datetime_in_utc,
)
from tiny_agent.tools.eco.fin import get_currency_exchange_rate, get_stock_data
from tiny_agent.tools.minimax.voice import get_voice, tts

CODING_TOOLS: dict[str, Callable] = {
    "tts": tts,
    "get_voice": get_voice,
    "get_stock_data": get_stock_data,
    "get_currency_exchange_rate": get_currency_exchange_rate,
    "get_current_datetime_in_utc": get_current_datetime_in_utc,
    "get_current_datetime_in_local": get_current_datetime_in_local,
}
