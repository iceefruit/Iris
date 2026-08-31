# 🤖 IRIS DEVELOPMENT & AGENT GUIDELINES

Welcome to the **Iris** codebase. This document defines the engineering standards, architecture patterns, and rules for any AI agent (Claude, Cursor, Antigravity, Copilot) or human engineer modifying or extending this project.

---

## 🏛️ 1. Architecture Philosophy
- **Modular & Decoupled:** Components communicate through abstract protocols defined in `core/protocols.py`. Never hardcode vendor-specific logic into the Agent core.
- **Fail-Safe & Non-Blocking:** All external calls (network, OS interactions) must have strict timeouts and error-trapping boundaries.
- **Strict Typing:** All new functions and classes must use Python type hints (`typing` / `dataclasses` / `pydantic`).

---

## 🗂️ 2. Directory Layout & Layer Responsibilities
```
Iris/
├── config.py          # Single source of truth for runtime variables (Pydantic BaseSettings)
├── core/
│   ├── protocols.py   # Interface contracts (Memory, Client, Tool)
│   ├── client.py      # LLM HTTP streaming client (OpenAI SSE format)
│   ├── memory.py      # Conversation history & token window management
│   └── agent.py       # Central orchestrator loop
├── integrations/      # Third-party bridges (n8n, webhooks, Slack, Discord)
├── tools/             # (Future) Action registry for OS execution, clicks, typing
├── vision/            # (Future) Screen capture, scaling, and OCR/visual grounding
└── main.py            # CLI runtime entrypoint
```

---

## 🧭 3. Rules for AI Agents Modifying This Codebase
1. **Never write bloated boilerplate:** Keep implementations clean, direct, and readable.
2. **Preserve the protocols:** If you add a new memory store (e.g., SQLite/Redis) or a new LLM provider, implement the protocol in `core/protocols.py`.
3. **No global variables:** Pass dependencies via constructor injection (`IrisAgent(client, memory)`).
4. **Coordinate Handling (When adding Vision/GUI Tools):**
   - Windows DPI scaling must always be normalized.
   - Screen coordinates must use a normalized $[0, 1000]$ coordinate space or calculate scaling factors via `ctypes.windll.user32.GetDpiForSystem()`.
5. **Always provide a Killswitch:** Any automated mouse/keyboard actuation must adhere to `pyautogui.FAILSAFE = True` and a dedicated abort hotkey.

---

## 🔌 4. Roadmap & Expansion Points
- [ ] **Phase 2 (Vision Engine):** Implement `vision/capture.py` using `mss` to capture screen frames on demand.
- [ ] **Phase 3 (Actuator / Tool Calling):** Implement `tools/` with standard JSON function calling schema for mouse clicks, typing, and PowerShell command execution.
- [ ] **Phase 4 (n8n Automations):** Bind `integrations/n8n.py` to trigger custom webhooks based on LLM intent.
