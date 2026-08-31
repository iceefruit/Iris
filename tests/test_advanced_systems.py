"""Unit tests for the 6 Advanced Core Systems in Iris."""

import os
import sys
import tempfile
from pathlib import Path
from PIL import Image, ImageDraw

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.verifier import VisualActionVerifier, ActionVisualOutcome
from tools.web_scraper import ReadWebpageTool
from core.rag import LocalRAGStore
from tools.rag_tool import IndexDirectoryTool, SearchKnowledgeBaseTool
from voice.listener import ContinuousVoiceListener
from core.sessions import SessionManager
from core.diagnostics import SystemDiagnostics
from tools.diagnostics_tool import DiagnoseEnvironmentTool
from tools.registry import default_registry


def test_visual_action_verifier():
    print("[1] Testing VisualActionVerifier (Screen Diffing & Self-Correction)...")
    with tempfile.TemporaryDirectory() as tmp_dir:
        p1 = Path(tmp_dir) / "screen1.png"
        p2 = Path(tmp_dir) / "screen2.png"
        p3 = Path(tmp_dir) / "screen3.png"

        # Image 1: Plain white canvas
        img1 = Image.new("RGB", (400, 300), color="white")
        img1.save(p1)

        # Image 2: Identical to Image 1
        img2 = Image.new("RGB", (400, 300), color="white")
        img2.save(p2)

        # Image 3: Localized change (a blue rectangle simulating button click)
        img3 = Image.new("RGB", (400, 300), color="white")
        draw = ImageDraw.Draw(img3)
        draw.rectangle([50, 50, 150, 100], fill="blue")
        img3.save(p3)

        # Test Static Screen (No Effect)
        res_static = VisualActionVerifier.verify(str(p1), str(p2), expected_tool="click")
        assert res_static.outcome == ActionVisualOutcome.NO_EFFECT_STATIC
        print(f"    Identical comparison -> {res_static.outcome.value} (diff: {res_static.change_ratio}) (PASS)")

        # Test Localized UI Change (Success)
        res_changed = VisualActionVerifier.verify(str(p1), str(p3), expected_tool="click")
        assert res_changed.outcome == ActionVisualOutcome.SUCCESS_CHANGED
        print(f"    Button click comparison -> {res_changed.outcome.value} (diff: {res_changed.change_ratio}) (PASS)")


def test_headless_web_scraper():
    print("\n[2] Testing Headless Web Scraper Tool...")
    scraper = ReadWebpageTool()
    sample_html = """
    <!DOCTYPE html>
    <html>
    <head><title>Iris Documentation</title></head>
    <body>
        <nav><a href="/">Home</a></nav>
        <h1>Welcome to Iris</h1>
        <p>Iris is an advanced agentic desktop assistant.</p>
        <pre><code>python main.py</code></pre>
        <ul>
            <li>Screen Vision</li>
            <li>Desktop Actuator</li>
        </ul>
        <footer>Copyright 2026</footer>
    </body>
    </html>
    """
    md = scraper._html_to_markdown(sample_html)
    assert "# Iris Documentation" in md
    assert "Welcome to Iris" in md
    assert "Iris is an advanced agentic desktop assistant." in md
    assert "`python main.py`" in md or "python main.py" in md
    assert "Screen Vision" in md
    assert "Copyright 2026" not in md  # Footer stripped
    print("    HTML -> Markdown extraction and clutter stripping verified. (PASS)")


def test_local_rag_store():
    print("\n[3] Testing Local Semantic RAG & BM25 Codebase Search...")
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = Path(tmp_dir) / "test_rag.db"
        rag = LocalRAGStore(db_path=str(db_path))

        # Create sample files
        code_file = Path(tmp_dir) / "auth_service.py"
        code_file.write_text("def authenticate_user(username, password):\n    # Validate JWT token\n    return token\n", encoding="utf-8")

        doc_file = Path(tmp_dir) / "architecture.md"
        doc_file.write_text("# Iris Architecture\nIris uses a protocol-first architecture with MikoClient.\n", encoding="utf-8")

        files_cnt, chunks_cnt = rag.index_directory(tmp_dir)
        assert files_cnt == 2
        assert chunks_cnt >= 2
        print(f"    Indexed {files_cnt} files into {chunks_cnt} search chunks. (PASS)")

        # Search for JWT authentication
        results = rag.search("JWT token authenticate")
        assert len(results) > 0
        assert "auth_service.py" in results[0].file_path
        print(f"    BM25 query 'JWT token authenticate' matched: {results[0].file_path} (Score: {results[0].score}) (PASS)")


def test_continuous_voice_listener():
    print("\n[4] Testing Continuous Voice Listener...")
    listener = ContinuousVoiceListener(samplerate=16000, energy_threshold=0.05)
    assert not listener.is_listening
    print("    ContinuousVoiceListener initialization verified. (PASS)")


def test_session_manager():
    print("\n[5] Testing Multi-Session & Workspace Manager...")
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_p = Path(tmp_dir) / "test_session.db"
        sm = SessionManager(db_path=str(db_p))

        assert sm.active_session == "default"
        assert sm.create_session("coding", "Coding workspace")
        assert sm.switch_session("coding")
        assert sm.active_session == "coding"

        sessions = sm.list_sessions()
        session_names = [s["name"] for s in sessions]
        assert "default" in session_names
        assert "coding" in session_names
        print(f"    Active sessions: {session_names} (Active: {sm.active_session}) (PASS)")


def test_system_diagnostics():
    print("\n[6] Testing System Diagnostics & Environment Tool...")
    diag_tool = DiagnoseEnvironmentTool()
    res = diag_tool.execute()
    assert res.success
    assert "System & Environment Telemetry" in res.output
    assert "Python" in res.output
    print("    System Telemetry and Developer CLI status generated. (PASS)")


def test_full_registry_count():
    print("\n[7] Testing Total Tool Registry Count...")
    all_tools = default_registry.list_tools()
    tool_names = [t.name for t in all_tools]
    print(f"    Total registered tools ({len(all_tools)}): {tool_names}")
    assert len(all_tools) == 20
    assert "read_webpage" in tool_names
    assert "index_directory" in tool_names
    assert "search_knowledge_base" in tool_names
    assert "diagnose_environment" in tool_names
    print("    All 20 tools registered in default registry. (PASS)")


if __name__ == "__main__":
    test_visual_action_verifier()
    test_headless_web_scraper()
    test_local_rag_store()
    test_continuous_voice_listener()
    test_session_manager()
    test_system_diagnostics()
    test_full_registry_count()
    print("\nAll 6 Advanced Core Systems Passed Verification Successfully!")
