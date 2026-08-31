# 🤖 IRIS DEVELOPMENT & AGENT GUIDELINES

Welcome to the **Iris** codebase. This document defines engineering standards, contracts, and guidelines for any AI agent or human developer working on Iris.

---

## 🏛️ 1. Architecture Philosophy
- **Modular & Protocol-First:** Components interact strictly via abstract protocols defined in `core/protocols.py`. Never hardcode vendor-specific logic inside `IrisAgent`.
- **Miko API Native:** Integrated with the official [Miko API](https://api-miko.yokoya.space/docs.md) specification:
  - Auth header: `X-API-Key`
  - Chat endpoint: `POST /chat` with `service`, `messages`, `username`, `userid`, `search`, `thinking`, `stream`
  - Upload endpoint: `POST /upload-files`
  - Image endpoint: `POST /image`
  - History clear: `POST /clear-history`
- **JSON Prompt Config:** System prompts and personality configurations are stored cleanly in `prompts.json`.
- **Low-Latency Streaming:** Streams real-time `content` and `thinking` tokens via Server-Sent Events (SSE).
- **Strict Typing:** All new functions and classes must use Python type hints (`typing` / `dataclasses` / `pydantic`).

---

## 🗂️ 2. Directory Layout & Layer Responsibilities
```
Iris/
├── prompts.json       # System prompt definitions and assistant behavior
├── config.py          # Single source of truth for runtime config (Pydantic BaseSettings)
├── core/
│   ├── protocols.py   # Interface contracts (MemoryProtocol, LLMClientProtocol, StreamChunk)
│   ├── client.py      # Miko API client (SSE streaming, file upload, image gen, clear history)
│   ├── memory.py      # Sliding-window conversation context management
│   ├── memory_store.py# SQLite persistent conversation history and user knowledge vault
│   ├── loop.py        # Autonomous multi-turn agent execution loop
│   ├── router.py      # Adaptive intent classifier and heuristic query router
│   ├── rag.py         # Local TF-IDF and BM25 hybrid retrieval engine
│   ├── verifier.py    # Visual action verification and diff validator
│   ├── scheduler.py   # Async background cron and delayed task runner
│   ├── sessions.py    # Multi-session and isolated workspace manager
│   ├── killswitch.py  # Global emergency abort mechanism (PyAutoGUI + hotkey)
│   └── agent.py       # Central orchestrator loop
├── integrations/      # External automation dispatchers (n8n webhooks)
├── tools/             # Action registry (20 registered tools: GUI, shell, files, scraper, RAG, etc.)
├── vision/            # Screen capture (MSS), active window context, and coordinate grid grounding
├── voice/             # Neural TTS (edge-tts) and local STT (faster-whisper) + continuous listener
├── tests/             # Unit and integration test suite
└── main.py            # CLI runtime entrypoint
```

---

## 🧭 3. Rules for AI Agents Modifying This Codebase
1. **Never write bloated boilerplate:** Keep implementations concise, modular, and readable.
2. **Preserve protocols:** When adding new LLM providers or storage backends, implement the interfaces in `core/protocols.py`.
3. **No global state:** Inject dependencies via constructors (`IrisAgent(client, memory)`).
4. **Coordinate Normalization (Vision/GUI Tools):**
   - Windows DPI scaling must always be normalized via `ctypes.windll.user32.GetDpiForSystem()`.
   - Use normalized $[0, 1000]$ coordinate bounding boxes.
5. **Always provide a Killswitch:** Any automated mouse/keyboard actuation must adhere to `pyautogui.FAILSAFE = True` and a dedicated abort hotkey.
6. **Always Commit & Push Every Time:**
   - AI agents must automatically stage, commit, and push all modifications to the remote repository (`git push origin <branch>`) after completing any feature, fix, or task.
   - Never leave uncommitted or unpushed work at the end of a session.

---

## 📝 4. Git & Commit Message Standards
Every commit must look like it was written by an experienced human software engineer:
- **Use Conventional Commit Prefixes:**
  - `feat:` for new capabilities, tools, or architectural features
  - `fix:` for bug fixes, schema corrections, or edge-case handling
  - `refactor:` for code restructuring without behavioral changes
  - `perf:` for performance optimizations and latency improvements
  - `test:` for unit and integration test additions or updates
  - `docs:` for documentation, docstrings, or guideline revisions
  - `chore:` for dependency updates, configuration tweaks, or tooling
- **Human-Grade Quality & Tone:**
  - Write concise, clear, and descriptive summaries in imperative mood (e.g., `feat: add continuous voice listener and wake word loop`, not `added voice listener` or `bot commit`).
  - Focus on what changed and why.
  - **Forbidden:** Generic robotic text (e.g. `update files`, `antigravity auto commit`, `fixes`, `agent update`, `wip`).

---

## 🔌 5. Roadmap & Expansion Points
- [x] **Phase 2 (Vision Engine):** Implement `vision/` with `mss`, Windows active application & context extraction, DPI normalization, and Miko file upload integration.
- [x] **Phase 3 (Actuator / Tool Calling):** Implement `tools/` with standard JSON function calling schema for mouse clicks, typing, hotkeys, scrolling, drag, and PowerShell execution.
- [x] **Phase 4 (n8n Automations & Advanced Core):** Bind `integrations/n8n.py`, multimodal image generation, persistent memory vault, local RAG knowledge base, and multi-session workspaces.
