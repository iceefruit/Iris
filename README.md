# Iris - Local Desktop AI Assistant

A lightweight, extensible, and modular local desktop AI assistant powered by the [Miko API](https://api-miko.yokoya.space/docs.md).

## 🚀 Features
- **Native Miko API Integration:** Direct support for `qwen-max`, `qwen-coder`, `deepseek-default`, and other Miko services.
- **Real-Time Streaming:** Low-latency SSE streaming with thinking mode visualization and rich CLI formatting.
- **Multi-Modal Ready:** Pre-wired support for file uploads (`/upload-files`), image generation (`/image`), and web search.
- **Protocol-Driven Architecture:** Decoupled client, memory, and orchestrator layers.
- **n8n Automation Ready:** Pre-built webhook dispatcher for zero-code external service triggers.
- **AI Agent Friendly:** Complete instructions and developer contract in [AGENTS.md](AGENTS.md).

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
3. Run:
   ```bash
   python main.py
   ```
