# Iris - Local Desktop AI Assistant

A lightweight, extensible, and modular local desktop AI assistant powered by the Miko API.

## 🚀 Features
- **Streaming Responses:** Low-latency SSE text generation with rich CLI formatting.
- **Protocol-driven Architecture:** Decoupled client, memory, and orchestrator layers.
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
