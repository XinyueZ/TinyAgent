from rich.markdown import Markdown
from rich.panel import Panel
from rich.console import Console
from rich.theme import Theme
import os

# GitHub-style theme for markdown
github_theme = Theme(
    {
        "markdown.h1": "bold #0969da",
        "markdown.h2": "bold #0969da",
        "markdown.h3": "bold #0969da",
        "markdown.h4": "bold #0969da",
        "markdown.h5": "bold #0969da",
        "markdown.h6": "bold #0969da",
        "markdown.code": "on #f6f8fa",
        "markdown.code_block": "on #f6f8fa",
        "markdown.link": "#0969da underline",
        "markdown.link_url": "#0969da",
        "markdown.item.bullet": "#57606a",
        "markdown.item.number": "#57606a",
        "markdown.block_quote": "italic #57606a",
        "markdown.hr": "#d0d7de",
        "markdown.strong": "bold",
        "markdown.emph": "italic",
    }
)

console = Console(theme=github_theme)


def format_text(
    text: str,
    title: str = "Title",
    border_style: str = "blue",
):
    verbose = int(os.getenv("VERBOSE", "0")) > 0
    if not verbose:
        print("[VERBOSE]: 0")
        return

    try:
        formatted_text = Markdown(
            text,
            code_theme="github-dark",
            hyperlinks=True,
        )
        console.print(
            Panel(
                formatted_text,
                title=f"[bold green]{title}[/bold green]",
                border_style=border_style,
                width=console.width,
                padding=(1, 2),
            )
        )
    except Exception as e:
        import traceback

        console.print(f"Error: {e}")
        console.print(traceback.format_exc())
