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
│   └── agent.py       # Central orchestrator loop
├── integrations/      # External automation dispatchers (n8n webhooks)
├── tools/             # (Future) Action registry for OS execution, clicks, typing
├── vision/            # (Future) Screen capture and visual coordinate grounding
└── main.py            # CLI runtime entrypoint
```

---

## 🧭 3. Rules for AI Agents Modifying This Codebase
1. **Never write bloated boilerplate:** Keep implementations concise, modular, and readable.
2. **Preserve protocols:** When adding new LLM providers or storage backends, implement the interfaces in `core/protocols.py`.
3. **No global state:** Inject dependencies via constructors (`IrisAgent(client, memory)`).
4. **Coordinate Normalization (Future Vision/GUI Tools):**
   - Windows DPI scaling must always be normalized via `ctypes.windll.user32.GetDpiForSystem()`.
   - Use normalized $[0, 1000]$ coordinate bounding boxes.
5. **Always provide a Killswitch:** Any automated mouse/keyboard actuation must adhere to `pyautogui.FAILSAFE = True` and a dedicated abort hotkey.

---

## 🔌 4. Roadmap & Expansion Points
- [ ] **Phase 2 (Vision Engine):** Implement `vision/capture.py` using `mss` to capture screen frames and upload via `/upload-files` or vision service.
- [ ] **Phase 3 (Actuator / Tool Calling):** Implement `tools/` with standard JSON function calling schema for mouse clicks, typing, and PowerShell command execution.
- [ ] **Phase 4 (n8n Automations):** Bind `integrations/n8n.py` to trigger custom webhooks based on LLM intent.
