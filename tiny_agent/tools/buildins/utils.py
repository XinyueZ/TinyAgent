from datetime import datetime, timezone
from ..decorator import *


@tool()
def get_current_datetime_in_utc() -> str:
    """Get current datetime in UTC, it is NOW

    Return:
        in string format: the current datetime in UTC
    """

    current_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    return current_time


@tool()
def get_current_datetime_in_local() -> str:
    """Get current datetime in local timezone, it is NOW

    Return:
        in string format: the current datetime in local timezone
    """

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return current_time
