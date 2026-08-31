# Iris - Local Desktop AI Assistant

A lightweight, extensible, and modular local desktop AI assistant powered by the [Miko API](https://api-miko.yokoya.space/docs.md).

## 🚀 Core Logic Systems & Capabilities
- **🔄 Multi-Step Autonomous ReAct Loop (`core/loop.py`):** Closed-loop autonomous desktop goal execution (`Observe -> Reason -> Act -> Verify`) with intermediate reflection.
- **🧠 Persistent Long-Term Memory & User Vault (`core/memory_store.py`):** SQLite-backed conversation persistence and learned user preferences injected automatically into prompts.
- **📋 Smart Clipboard & Active Selection Engine (`tools/clipboard.py`):** Non-destructive highlighted text capture across any Windows application without losing original clipboard contents.
- **🎨 Autonomous Image Generation Tool (`tools/image_gen.py`):** Multi-modal image generation and local caching via Miko's `/image` endpoint.
- **⚡ n8n External Workflow Integration (`tools/n8n_tool.py` & `integrations/n8n.py`):** Zero-code webhook trigger for Telegram, Notion, Smart Home, and email.
- **⏰ Background Task Scheduler & System Watcher (`core/scheduler.py`):** Threaded one-shot timers, recurring interval jobs, and proactive battery monitoring.
- **🎙️ Voice Engine (TTS & STT):** Free, ultra-natural neural speech synthesis via `edge-tts` (in-memory streaming with `sounddevice`) and low-latency speech recognition via `faster-whisper`.
- **🚨 Global Panic Killswitch (`core/killswitch.py`):** Global background shortcut (`Ctrl+Shift+K`) that immediately freezes actuation, releases stuck mouse buttons/keys, and halts loops.
- **👁️ Visual Grounding Grid (Set-of-Marks):** Renders high-contrast $[0, 1000]$ normalized coordinate grids over screen captures for pinpoint spatial accuracy.
- **🛠️ 16 Registered Desktop Tools:** Mouse (`click`, `move_cursor`, `drag`, `scroll`), Keyboard (`type_text`, `press_hotkey`), Shell (`execute_powershell`), OS (`launch_application`, `open_browser_url`, `get_system_status`, `file_operation`), Clipboard (`get_clipboard`, `set_clipboard`, `get_active_selection`), Generation (`generate_image`), and Integrations (`trigger_n8n_workflow`).

## 📦 Setup & Run
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Configure `.env`:
   ```bash
   copy .env.example .env
   # Edit .env and insert your MIKO_API_KEY
   ```
3. Customize Prompt (Optional):
   Edit `prompts.json` to change how Iris responds.
4. Run:
   ```bash
   python main.py
   ```

## 🎮 CLI Commands
- `/goal <task>`: Executes an autonomous multi-step ReAct goal loop (e.g. `'/goal Open Spotify and play music'`).
- `/act <query>`: Visually inspects the desktop screen with grounding and executes actions (clicks, typing, hotkeys, PowerShell, apps, files).
- `/selection <query>`: Non-destructively captures text currently highlighted by the user in any application.
- `/remember <k=v>`: Teaches Iris a persistent fact or preference (e.g. `'/remember preferred_editor=VS Code'`).
- `/facts`: Displays all remembered user preferences in a rich table.
- `/forget <key>`: Removes a remembered fact from the knowledge vault.
- `/tasks`: Lists all running background scheduled timers and watchers.
- `/screen <query>`: Captures entire primary screen, registers active application metadata (app name, title, bounds, DPI), and sends to Iris.
- `/screen-grid <query>`: Captures screen with a $[0, 1000]$ visual coordinate grid overlay for precise element grounding.
- `/screen-window <query>`: Captures only the active foreground application window.
- `/speak <query>`: Asks Iris and speaks the answer out loud using Microsoft Edge Neural TTS.
- `/voice`: Records 5 seconds of speech from microphone via `faster-whisper` and submits query hands-free.
- `clear`: Resets local and server-side conversation history.
- `exit`: Quits the assistant.
- **Emergency Panic Abort:** Press `Ctrl+Shift+K` at any time to immediately kill any running automation.

