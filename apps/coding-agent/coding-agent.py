import warnings

warnings.filterwarnings("ignore")

import os


from google.genai import types

from tiny_agent.agent.tiny_coding_agent import TinyCodingAgent
from tiny_agent.tools.decorator import *
from tiny_agent.tools.eco.fin import get_currency_exchange_rate, get_stock_data

_PROVIDER_CONFIG = {
    "vertexai": bool(os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", True)),
    "vertexai_location": os.environ.get("GOOGLE_CLOUD_LOCATION", "europe-west4"),
    "vertexai_project": os.environ.get(
        "GOOGLE_CLOUD_PROJECT", "hg-hjghjg-ai-ft-exp-pr-hjjkhljhlhjkl"
    ),
    "google_ai_studio_api_key": os.environ.get("GOOGLE_AI_STUDIO_API_KEY", ""),
}

_PYTHON_CODING_AGENT_MODEL = "gemini-3.1-pro-preview"
_PYTHON_CODING_AGENT_MODEL_CONFIG = {
    "temperature": 1.0,
    "seed": 42,
    "top_p": 1.0,
    "top_k": 60,
    "thinking_config": types.ThinkingConfig(
        thinking_level=types.ThinkingLevel.HIGH,
        include_thoughts=False,
    ),
}

# python ./coding-agent.py --output ./coding-agent-output
if __name__ == "__main__":
    print("Coding Agent")
    import argparse

    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument(
        "--output", type=str, required=True, help="The output of the application"
    )
    args = parser.parse_args()

    if os.path.exists(args.output):
        import shutil

        shutil.rmtree(args.output)

    agent = TinyCodingAgent(
        name="python-coding-agent",
        model=_PYTHON_CODING_AGENT_MODEL,
        output_root=args.output,
        perf_libs=["pandas", "matplotlib", "numpy", "seaborn", "plotly"],
        coding_tools=[get_stock_data, get_currency_exchange_rate],
        genai_stuff={**_PYTHON_CODING_AGENT_MODEL_CONFIG, **_PROVIDER_CONFIG},
    )

    task = f"""Complete two financial and stock inquiry tasks:
1. Get exchange rates for U.S. dollar, Euro, and Chinese Yuan from 2026-01-01 to today.
2. Get stock prices for Apple, Alphabet, Amazon, Nvidia, AMD, Intel, Microsoft, and Oracle from 2025-01-01 to today.
3. Generate an exchange rate chart plot to "currency_exchange_rate_chart.png".
4. Generate a stock prices chart plot to "stock_prices_chart.png".
5. Perform the reflection to confirm the existence of the generated chart files. If not found, regenerate them.

All code files, templates, and chart image files can be saved in the folder: {agent.output_location}.
"""
    format_text(task, "⚑ Coding Agent")
    result = agent(contents=task)
    format_text(result.text, "❀ Coding Agent result")
