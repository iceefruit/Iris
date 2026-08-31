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
        default_service=config.service,
        username=config.username,
        userid=config.userid,
        timeout=config.timeout_seconds,
    )
    memory = ConversationMemory(
        system_prompt=config.system_prompt,
        max_messages=config.max_history_messages,
    )
    return IrisAgent(client=client, memory=memory)


def main():
    console.print(
        Panel.fit(
            f"[bold magenta]Iris Core Assistant[/bold magenta]\n"
            f"[dim]Endpoint:[/dim] {config.base_url}\n"
            f"[dim]Service:[/dim]  {config.service}\n"
            f"[dim]User:[/dim]     {config.username} ({config.userid})\n"
            f"[dim]Features:[/dim] Search={config.search} | Thinking={config.thinking}\n"
            f"[dim]Commands:[/dim] [yellow]'clear'[/yellow] to reset session, [yellow]'exit'[/yellow] to quit.",
            title="✨ Iris Initialized (Miko API)",
            border_style="cyan",
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
                agent.clear()
                console.print("[yellow]Local context and server-side history cleared.[/yellow]")
                continue

            console.print("[bold cyan]Iris > [/bold cyan]", end="")
            in_thinking = False
            for chunk in agent.ask(user_input):
                if chunk.chunk_type == "thinking":
                    if not in_thinking:
                        console.print("\n[dim italic]Thinking: ", end="")
                        in_thinking = True
                    console.print(chunk.text, end="", style="dim italic")
                elif chunk.chunk_type == "content":
                    if in_thinking:
                        console.print("[/dim italic]\n")
                        in_thinking = False
                    console.print(chunk.text, end="", style="white")
                elif chunk.chunk_type == "error":
                    console.print(chunk.text, style="bold red")

            console.print()

        except KeyboardInterrupt:
            console.print("\n[dim]Interrupted. Type 'exit' to quit.[/dim]")
        except Exception as err:
            console.print(f"\n[bold red]Unexpected Error:[/bold red] {err}")


if __name__ == "__main__":
    main()
