import sys
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from config import config
from core.client import MikoClient
from core.memory_store import PersistentMemoryStore
from core.agent import IrisAgent
from core.killswitch import killswitch
from core.scheduler import scheduler
from vision import VisionEngine
from voice import VoiceEngine
from tools.clipboard import GetActiveSelectionTool

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
    memory = PersistentMemoryStore(db_path=config.memory_db_path)
    return IrisAgent(client=client, memory=memory, killswitch=killswitch)


def main():
    # Start global panic killswitch and task scheduler listeners
    killswitch.start()
    scheduler.start()

    console.print(
        Panel.fit(
            f"[bold magenta]Iris Autonomous Desktop AI Assistant[/bold magenta]\n"
            f"[dim]Endpoint:[/dim] {config.base_url} | Service: {config.service} | Vision: {config.vision_service}\n"
            f"[dim]User:[/dim]     {config.username} ({config.userid})\n"
            f"[dim]Memory:[/dim]   Persistent SQLite Vault at [cyan]{config.memory_db_path}[/cyan]\n"
            f"[dim]Safety:[/dim]   Panic Killswitch: [bold red]{config.killswitch_hotkey}[/bold red] (Press anytime to freeze)\n"
            f"[dim]Commands:[/dim]\n"
            f"  [yellow]'/goal <task>'[/yellow]          - Execute autonomous multi-step ReAct goal loop\n"
            f"  [yellow]'/act <query>'[/yellow]          - Visually inspect screen & execute single action\n"
            f"  [yellow]'/selection <query>'[/yellow]    - Non-destructively read highlighted text across apps\n"
            f"  [yellow]'/screen-grid <query>'[/yellow]  - Capture screen with [0-1000] visual coordinate grid\n"
            f"  [yellow]'/screen <query>'[/yellow]       - Full screen capture + active app metadata\n"
            f"  [yellow]'/remember <k=v>'[/yellow]      - Store user preference in persistent memory vault\n"
            f"  [yellow]'/facts'[/yellow]                - View stored user profile facts and preferences\n"
            f"  [yellow]'/voice-loop'[/yellow]           - Start always-on 'Hey Iris' hands-free voice loop\n"
            f"  [yellow]'/voice'[/yellow]                - Record 5s from microphone and ask Iris (STT)\n"
            f"  [yellow]'/speak <query>'[/yellow]        - Ask Iris and speak the response out loud (TTS)\n"
            f"  [yellow]'/tasks'[/yellow]                - View background scheduled tasks\n"
            f"  [yellow]'clear'[/yellow]                 - Reset conversation session\n"
            f"  [yellow]'exit'[/yellow]                  - Quit assistant",
            title="✨ Iris Core Logic Engine (All 6 Pillars Active)",
            border_style="cyan",
        )
    )

    agent = initialize_agent()
    vision_engine = VisionEngine()
    voice_engine = VoiceEngine()
    selection_tool = GetActiveSelectionTool()
    from integrations.discord import DiscordIrisBridge
    discord_bridge = DiscordIrisBridge(agent=agent)

    if getattr(config, "discord_autostart", False) and config.discord_user_token:
        discord_bridge.start_background()
        console.print("[dim green]✔ Discord Userbot Gateway auto-started in background.[/dim green]")

    try:
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
                    voice_engine.stop()
                    console.print("[yellow]Local context and server session history cleared.[/yellow]")
                    continue

                file_paths = None
                prompt_to_send = user_input
                execute_actions = False
                should_speak = config.voice_enabled

                # Command Routing
                is_vision_cmd = False
                crop_active = False
                use_grid = False

                # Voice Continuous Wake-Word Loop (/voice-loop)
                if user_input.lower().startswith(("/voice-loop", "/listen-loop", "/wake")):
                    if voice_engine.is_listening_loop:
                        voice_engine.stop_wake_word_loop()
                        console.print("[yellow]🎙️ 'Hey Iris' hands-free voice loop stopped.[/yellow]")
                    else:
                        def _voice_callback(clean_query: str):
                            console.print(f"\n[bold green]🎙️ Wake-Word Heard:[/bold green] [italic]'{clean_query}'[/italic]")
                            spoken_parts = []
                            for ev in agent.process_input(clean_query):
                                if ev.get("type") in ("chunk", "content"):
                                    txt = ev.get("text", "")
                                    if ev.get("chunk_type") == "content" or ev.get("type") == "content":
                                        spoken_parts.append(txt)
                            if spoken_parts:
                                resp_txt = "".join(spoken_parts)
                                clean_resp = "\n".join([l for l in resp_txt.splitlines() if not l.startswith("```")])
                                voice_engine.speak_async(clean_resp)

                        voice_engine.start_wake_word_loop(on_command_callback=_voice_callback)
                        console.print("[green]🎙️ 'Hey Iris' continuous wake-word listener active! Say 'Hey Iris <command>' anytime.[/green]")
                    continue

                # Voice STT Command (/voice)
                elif user_input.lower().startswith("/voice"):
                    console.print("[dim yellow]🎙️ Listening to microphone for 5 seconds...[/dim yellow]")
                    recorded_text = voice_engine.listen(duration_seconds=5.0)
                    if not recorded_text:
                        console.print("[dim red]No speech detected. Try again.[/dim red]")
                        continue
                    console.print(f"[bold green]Heard:[/bold green] [italic]{recorded_text}[/italic]")
                    user_input = recorded_text
                    should_speak = True

                # Voice Speak Command (/speak)
                elif user_input.lower().startswith("/speak"):
                    should_speak = True
                    parts = user_input.split(" ", 1)
                    user_input = parts[1] if len(parts) > 1 else "Hello!"

                # Smart Active Selection Command (/selection)
                elif user_input.lower().startswith(("/selection", "/highlight")):
                    res = selection_tool.execute()
                    if not res.success or not res.output:
                        console.print(f"[dim red]{res.error or 'No text selected.'}[/dim red]")
                        continue
                    parts = user_input.split(" ", 1)
                    action_query = parts[1] if len(parts) > 1 else "Explain and analyze this selected text or code."
                    user_input = f"{action_query}\n\n```text\n{res.output}\n```"
                    console.print(
                        Panel(
                            res.output[:500] + ("..." if len(res.output) > 500 else ""),
                            title="📋 Captured Selection from Active Window",
                            border_style="cyan",
                        )
                    )

                # Background Tasks Command (/tasks)
                elif user_input.lower() == "/tasks":
                    tasks = scheduler.list_tasks()
                    if tasks:
                        tbl = Table(title="⏰ Active Scheduled Tasks", border_style="magenta")
                        tbl.add_column("Task Name", style="bold yellow")
                        tbl.add_column("Type", style="cyan")
                        tbl.add_column("Next Run In", style="green")
                        tbl.add_column("Last Run At", style="dim")
                        for t in tasks:
                            ttype = f"Interval ({t['interval_seconds']}s)" if t['recurring'] else "One-Shot"
                            tbl.add_row(t['name'], ttype, f"{t['seconds_until_next_run']}s", t['last_run_at'] or "Never")
                        console.print(tbl)
                    else:
                        console.print("[dim yellow]No active background tasks scheduled.[/dim yellow]")
                    continue

                # Session Management Commands (/sessions, /session, /session-new)
                elif user_input.lower() == "/sessions":
                    from core.sessions import session_manager
                    sessions = session_manager.list_sessions()
                    tbl = Table(title="📁 Workspace Conversation Sessions", border_style="cyan")
                    tbl.add_column("Session Name", style="bold yellow")
                    tbl.add_column("Messages", style="green")
                    tbl.add_column("Last Active", style="dim")
                    tbl.add_column("Status", style="bold magenta")
                    for s in sessions:
                        active_tag = "👉 Active" if s["is_active"] else ""
                        tbl.add_row(s["name"], str(s["message_count"]), s["last_active_at"], active_tag)
                    console.print(tbl)
                    continue

                elif user_input.lower().startswith("/session-new"):
                    from core.sessions import session_manager
                    parts = user_input.split(" ", 1)
                    if len(parts) > 1:
                        sname = parts[1].strip()
                        if session_manager.create_session(sname):
                            session_manager.switch_session(sname)
                            console.print(f"[green]✔ Created and switched to new workspace:[/green] [bold]{sname}[/bold]")
                        else:
                            console.print(f"[dim red]Session '{sname}' already exists.[/dim red]")
                    continue

                elif user_input.lower().startswith("/session"):
                    from core.sessions import session_manager
                    parts = user_input.split(" ", 1)
                    if len(parts) > 1:
                        sname = parts[1].strip()
                        session_manager.switch_session(sname)
                        console.print(f"[green]✔ Switched active workspace to:[/green] [bold]{sname}[/bold]")
                    else:
                        console.print(f"[yellow]Active session:[/yellow] [bold]{session_manager.active_session}[/bold]")
                    continue

                # Discord Userbot Commands (/discord, /discord-start, /discord-stop)
                elif user_input.lower().startswith(("/discord", "/userbot")):
                    from integrations.discord import DiscordIrisBridge
                    parts = user_input.split(" ", 1)
                    sub = parts[1].strip().lower() if len(parts) > 1 else "status"

                    if sub in ("start", "connect", "on"):
                        if not config.discord_user_token:
                            console.print("[dim red]No DISCORD_USER_TOKEN set in config or .env.[/dim red]")
                        else:
                            console.print("[cyan]Starting Discord Userbot Gateway connection...[/cyan]")
                            if not discord_bridge.is_running:
                                discord_bridge.start_background()
                                console.print("[green]✔ Discord Userbot Gateway running in background.[/green]")
                            else:
                                console.print("[yellow]Discord Userbot is already running.[/yellow]")

                    elif sub in ("stop", "disconnect", "off"):
                        discord_bridge.stop()
                        console.print("[yellow]✔ Discord Userbot disconnected.[/yellow]")

                    else:
                        status_str = "[bold green]Online / Listening[/bold green]" if discord_bridge.is_running else "[dim red]Offline[/dim red]"
                        user_info = discord_bridge.gateway.user
                        uname = f"{user_info.get('username')}#{user_info.get('discriminator', '0000')}" if user_info else "Not logged in"
                        tbl = Table(title="🤖 Discord Userbot Bridge Status", border_style="cyan")
                        tbl.add_column("Property", style="bold yellow")
                        tbl.add_column("Value", style="white")
                        tbl.add_row("Connection Status", status_str)
                        tbl.add_row("User Account", uname)
                        tbl.add_row("Trigger Keyword", f"[bold cyan]{config.discord_trigger_word}[/bold cyan]")
                        tbl.add_row("Token Configured", "✔ Yes" if bool(config.discord_user_token) else "❌ No")
                        tbl.add_row("Allowed Users", config.discord_allowed_users or "All users (DM & Channel)")
                        console.print(tbl)
                        console.print("[dim]Use '/discord start' to connect or '/discord stop' to disconnect.[/dim]")
                    continue

                # Persistent Facts Command (/facts)
                elif user_input.lower() in ("/facts", "/vault", "/memory"):
                    if hasattr(agent.memory, "get_all_facts"):
                        facts = agent.memory.get_all_facts()
                        if facts:
                            tbl = Table(title="🧠 Stored User Profile & Preferences", border_style="cyan")
                            tbl.add_column("Key", style="bold yellow")
                            tbl.add_column("Value", style="white")
                            for k, v in facts.items():
                                tbl.add_row(k, v)
                            console.print(tbl)
                        else:
                            console.print("[dim yellow]User knowledge vault is empty. Tell Iris what to remember anytime![/dim yellow]")
                    continue

                # Explicit Forget Command (/forget)
                elif user_input.lower().startswith("/forget"):
                    parts = user_input.split(" ", 1)
                    if len(parts) > 1 and hasattr(agent.memory, "forget_fact"):
                        key = parts[1].strip()
                        if agent.memory.forget_fact(key):
                            console.print(f"[yellow]✔ Forgot fact:[/yellow] {key}")
                        else:
                            console.print(f"[dim red]Key '{key}' not found in memory vault.[/dim red]")
                    continue

                # --- UNIFIED NATURAL LANGUAGE EXECUTION ---
                in_thinking = False
                sources_to_show = []
                spoken_response_acc = []
                printed_prompt_header = False

                for event in agent.process_input(user_input=user_input):
                    ev_type = event.get("type")

                    if ev_type == "intent_detected":
                        cat = event.get("category")
                        if cat in ("GOAL", "ACTION", "VISION"):
                            console.print(f"[dim yellow]⚡ Auto-Detected Intent:[/dim yellow] [bold]{cat}[/bold] -> [dim]{event.get('query')}[/dim]")

                    elif ev_type == "memory_stored":
                        console.print(f"[green]✔ Remembered preference:[/green] [bold]{event['key']}[/bold] = [cyan]{event['value']}[/cyan]")

                    elif ev_type == "vision_context":
                        console.print(
                            Panel(
                                f"[bold]Active Application:[/bold] [cyan]{event['app']}[/cyan]\n"
                                f"[bold]Window Title:[/bold] {event['title']}\n"
                                f"[dim]Screenshot:[/dim] [yellow]{event['screenshot']}[/yellow]",
                                title="📸 Context & Vision Grounding",
                                border_style="dim green",
                            )
                        )

                    # Multi-Step Goal Events
                    elif ev_type == "step_started":
                        console.print(f"\n[bold cyan]Step {event['step']}/{event['max_steps']}:[/bold cyan] [dim]App: {event['active_app']}[/dim]")
                    elif ev_type == "action_executing":
                        console.print(f"\n[bold yellow]⚡ Action Call:[/bold yellow] [dim]{event['tool']}({event['arguments']})[/dim]")
                    elif ev_type == "action_result":
                        status_color = "green" if event.get("success") else "red"
                        console.print(f"[{status_color}]✔ Action Result:[/{status_color}] [dim]{event['result']}[/dim]")
                    elif ev_type == "visual_verification":
                        console.print(f"[dim cyan]👁️ Visual Verifier:[/dim cyan] [dim]{event['observation']}[/dim]")
                    elif ev_type == "goal_completed":
                        console.print(f"\n[bold green]🎉 Goal Completed:[/bold green] {event['summary']}")
                    elif ev_type == "goal_aborted":
                        console.print(f"\n[bold red]🛑 Goal Aborted:[/bold red] {event['reason']}")

                    # Streaming Chunk Events
                    elif ev_type == "chunk":
                        chunk_kind = event.get("chunk_type")
                        chunk_text = event.get("text", "")
                        chunk_meta = event.get("metadata") or {}

                        if not printed_prompt_header and chunk_kind in ("content", "thinking"):
                            console.print("[bold cyan]Iris > [/bold cyan]", end="")
                            printed_prompt_header = True

                        if chunk_kind == "function_call":
                            console.print(f"\n[bold yellow]⚡ Action Call:[/bold yellow] [dim]{chunk_text}[/dim]")
                        elif chunk_kind == "function_result":
                            console.print(f"[bold green]✔ Action Result:[/bold green] [dim]{chunk_text}[/dim]")
                        elif chunk_kind == "thinking":
                            if not in_thinking:
                                console.print("\n[dim italic]Thinking: ", end="")
                                in_thinking = True
                            console.print(chunk_text, end="", style="dim italic")
                        elif chunk_kind == "content":
                            if in_thinking:
                                console.print("[/dim italic]\n")
                                in_thinking = False
                            console.print(chunk_text, end="", style="white")
                            spoken_response_acc.append(chunk_text)
                        elif chunk_kind == "final":
                            if isinstance(chunk_meta, dict):
                                urls = chunk_meta.get("searched_urls", [])
                                if urls:
                                    sources_to_show = urls
                        elif chunk_kind == "error":
                            console.print(chunk_text, style="bold red")

                    elif ev_type == "thinking":
                        console.print(event.get("text", ""), end="", style="dim italic")
                    elif ev_type == "content":
                        console.print(event.get("text", ""), end="", style="white")
                        spoken_response_acc.append(event.get("text", ""))

                if sources_to_show:
                    console.print("\n\n[dim cyan]🌐 Sources:[/dim cyan]")
                    for idx, url in enumerate(sources_to_show, 1):
                        console.print(f"  [dim][{idx}] {url}[/dim]")

                console.print()

                # Text-To-Speech Playback if requested
                if should_speak and spoken_response_acc:
                    full_text = "".join(spoken_response_acc)
                    clean_spoken = "\n".join([line for line in full_text.splitlines() if not line.startswith("```")])
                    voice_engine.speak_async(clean_spoken)

            except KeyboardInterrupt:
                console.print("\n[dim]Interrupted. Type 'exit' to quit.[/dim]")
            except Exception as err:
                console.print(f"\n[bold red]Unexpected Error:[/bold red] {err}")

    finally:
        killswitch.stop()
        scheduler.shutdown()
        voice_engine.stop()
        discord_bridge.stop()


if __name__ == "__main__":
    main()
