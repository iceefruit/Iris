"""Entrypoint for the Iris Desktop Assistant CLI."""

import sys
from rich.console import Console
from rich.panel import Panel

from config import config
from core.client import MikoClient
from core.memory import ConversationMemory
from core.agent import IrisAgent

console = Console()


def initialize_agent() -> IrisAgent:
    if not config.api_key:
        console.print(
            "[bold red]Error:[/bold red] MIKO_API_KEY is not set.\n"
            "Please open [cyan].env[/cyan] and set your API key."
        )
        sys.exit(1)

    client = MikoClient(
        base_url=config.base_url,
        api_key=config.api_key,
        default_model=config.model,
        timeout=config.timeout_seconds
    )
    memory = ConversationMemory(
        system_prompt=config.system_prompt,
        max_messages=config.max_history_messages
    )
    return IrisAgent(client=client, memory=memory)


def main():
    console.print(
        Panel.fit(
            f"[bold magenta]Iris Core Assistant[/bold magenta]\n"
            f"[dim]Endpoint:[/dim] {config.base_url}\n"
            f"[dim]Model:[/dim]    {config.model}\n"
            f"[dim]Commands:[/dim] Type [yellow]'exit'[/yellow] to quit, [yellow]'clear'[/yellow] to reset context.",
            title="✨ Iris Initialized",
            border_style="cyan"
        )
    )

    agent = initialize_agent()

    while True:
        try:
            user_input = console.input("\n[bold green]You > [/bold green]").strip()
            if not user_input:
                continue

            if user_input.lower() in ("exit", "quit", "q"):
                console.print("[dim]Goodbye![/dim]")
                break

            if user_input.lower() == "clear":
                agent.memory.clear()
                console.print("[yellow]Context history cleared.[/yellow]")
                continue

            console.print("[bold cyan]Iris > [/bold cyan]", end="")
            for chunk in agent.ask(user_input):
                console.print(chunk, end="", style="white")
            console.print()

        except KeyboardInterrupt:
            console.print("\n[dim]Interrupted. Type 'exit' to quit.[/dim]")
        except Exception as err:
            console.print(f"\n[bold red]Unexpected Error:[/bold red] {err}")


if __name__ == "__main__":
    main()
