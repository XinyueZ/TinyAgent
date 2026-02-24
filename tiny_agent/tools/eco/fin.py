import time
from pathlib import Path
from uuid import uuid4

import requests
import yfinance

from tiny_agent.tools.decorator import coding_tool, tool


@coding_tool()
@tool()
def get_currency_exchange_rate(
    currency_from: str, currency_to: str, start_date: str, end_date: str
) -> dict:
    """Get the currency exchange rate via frankfurter.app.

    Data source:
        https://www.frankfurter.app/

    Args:
        currency_from: Base currency code (ISO 4217), e.g. "USD".
        currency_to: Quote currency code (ISO 4217), e.g. "EUR".
        start_date: Start date (inclusive) in "YYYY-MM-DD".
        end_date: End date (inclusive) in "YYYY-MM-DD".

    Returns:
        A dict in one of the following forms:
        - Success:
            {
              "status": "success",
              "report": "<raw json string from frankfurter>"
            }
        - Error:
            {
              "status": "error",
              "error_message": "<http status + response text>"
            }
    """

    response = requests.get(
        f"https://api.frankfurter.app/{start_date}..{end_date}",
        params={"from": currency_from, "to": currency_to},
        timeout=30,
    )
    if response.status_code != 200:
        return {
            "status": "error",
            "error_message": (
                f"Failed to retrieve exchange rate: {response.status_code} {response.text}"
            ),
        }

    return {"status": "success", "report": response.text}


@coding_tool()
@tool()
def get_stock_data(
    stock_symbols: str, start_date: str, end_date: str, output_dir: str
) -> dict:
    """Download stock close prices via yfinance and persist artifacts.

    Notes:
        - `stock_symbols` must be a comma-separated string.
        - `output_dir` is provided by the caller.

    Args:
        stock_symbols: Comma-separated tickers, e.g. "AAPL,MSFT".
        start_date: Start date (inclusive) in "YYYY-MM-DD".
        end_date: End date (exclusive, yfinance convention) in "YYYY-MM-DD".
        output_dir:
            Output directory (absolute or relative to the current working directory).
            A unique run subfolder will be created under it.

    Returns:
        A dict in one of the following forms:
        - Success:
            {
              "status": "success",
              "symbols": ["AAPL", "MSFT"],
              "start_date": "2024-01-01",
              "end_date": "2024-02-01",
              "csv_path": "<absolute path>",
              "plot_path": "<absolute path>" | "",
              "preview_tail": "<string>"
            }
        - Error:
            {
              "status": "error",
              "error_message": "..."
            }

        `plot_path` is best-effort: if `matplotlib` is unavailable or plotting fails,
        it will be an empty string.
    """
    if not isinstance(stock_symbols, str) or not stock_symbols.strip():
        raise ValueError("stock_symbols must be a non-empty string")

    symbols = [s.strip() for s in stock_symbols.split(",") if s.strip()]
    if not symbols:
        raise ValueError("stock_symbols must contain at least one symbol")

    run_id = f"{int(time.time() * 1_000_000)}-{uuid4().hex}"

    if not isinstance(output_dir, str) or not output_dir.strip():
        raise ValueError("output_dir must be a non-empty string")

    out_dir = Path(output_dir) / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        stock_data = yfinance.download(
            tickers=symbols,
            start=start_date,
            end=end_date,
            group_by="column",
            auto_adjust=False,
            progress=False,
            threads=True,
        )
    except Exception as e:
        return {"status": "error", "error_message": f"yfinance download failed: {e}"}

    close = None
    try:
        close = stock_data.get("Close")
    except Exception:
        close = None

    if close is None:
        return {
            "status": "error",
            "error_message": "No Close price data returned.",
        }

    csv_path = out_dir / "close.csv"
    try:
        close.to_csv(csv_path)
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Failed to write CSV: {e}",
        }

    plot_path = None
    try:
        import matplotlib.pyplot as plt

        plt.figure(figsize=(10, 5))
        for col in close.columns:
            plt.plot(close.index, close[col], label=str(col))
        plt.title("Stock Close Prices")
        plt.xlabel("Date")
        plt.ylabel("Close")
        plt.legend()
        plt.grid(True)
        plot_path = out_dir / "close.png"
        plt.tight_layout()
        plt.savefig(plot_path)
        plt.close()
    except Exception:
        plot_path = None

    preview = None
    try:
        preview = close.tail(5).to_string()
    except Exception:
        preview = None

    return {
        "status": "success",
        "symbols": symbols,
        "start_date": start_date,
        "end_date": end_date,
        "csv_path": str(csv_path),
        "plot_path": str(plot_path) if plot_path else "",
        "preview_tail": preview or "",
    }
