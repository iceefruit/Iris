"""Response formatting and Voice/Text extraction utilities for Iris UI."""

import json
import re
from typing import List


def clean_markdown_for_speech(text: str) -> str:
    """Cleans raw markdown, code blocks, ASCII charts, and tables to produce natural spoken speech."""
    if not text:
        return ""

    # 1. Remove action blocks ```action ... ``` and code blocks ```...```
    cleaned = re.sub(r"```[\s\S]*?```", "", text)

    # 2. Remove inline code `...`
    cleaned = re.sub(r"`([^`]+)`", r"\1", cleaned)

    # 3. Remove ASCII art & table box drawing characters
    box_chars = r"[┌┐└┘├┤┬┴┼─│═║╔╗╚╝╠╣╦╩╬▀▄█▌▐░▒▓■□▪▫▲▼▶◀◆◇\+\-\|]{3,}"
    lines: List[str] = []
    for line in cleaned.splitlines():
        line_stripped = line.strip()
        # Skip table divider lines or ASCII diagram lines
        if re.search(box_chars, line_stripped) or (line_stripped.startswith("|") and line_stripped.endswith("|")):
            continue
        # Skip pure symbols or divider lines
        if re.match(r"^[-=_*~#]{3,}$", line_stripped):
            continue
        lines.append(line)

    cleaned = "\n".join(lines)

    # 4. Remove Markdown links [text](url) -> text
    cleaned = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", cleaned)

    # 5. Remove raw URLs
    cleaned = re.sub(r"https?://\S+", "", cleaned)

    # 6. Remove Markdown headers, bold, italics, strikethrough, blockquotes
    cleaned = re.sub(r"^#+\s*", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"\*\*([^*]+)\*\*", r"\1", cleaned)
    cleaned = re.sub(r"\*([^*]+)\*", r"\1", cleaned)
    cleaned = re.sub(r"__([^_]+)__", r"\1", cleaned)
    cleaned = re.sub(r"_([^_]+)_", r"\1", cleaned)
    cleaned = re.sub(r"~~([^~]+)~~", r"\1", cleaned)
    cleaned = re.sub(r"^>\s*", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"^[\*\-\+]\s+", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"^\d+\.\s+", "", cleaned, flags=re.MULTILINE)

    # 7. Normalize spaces and line breaks
    cleaned = re.sub(r"\n+", ". ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    return cleaned


def extract_action_spoken_summary(raw_text: str) -> str:
    """If the output is purely an action block without text, generates a clean spoken confirmation."""
    if not raw_text:
        return ""

    action_match = re.search(r"```action\s*(\{[\s\S]*?\})\s*```", raw_text)
    if action_match:
        try:
            data = json.loads(action_match.group(1))
            tool = data.get("tool", "")
            args = data.get("arguments", {})
            if tool == "launch_application":
                app = args.get("app_name", "the application")
                return f"Opening {app}."
            elif tool == "spotify_control":
                action = args.get("action", "")
                track = args.get("track_or_playlist", "")
                if track:
                    return f"Playing {track} on Spotify."
                return f"Spotify {action}."
            elif tool == "open_browser_url":
                return f"Opening {args.get('url', 'the webpage')} in your browser."
            elif tool == "click":
                return "Clicking element."
            elif tool == "complete_goal":
                return args.get("summary", "Task completed.")
        except Exception:
            pass
    return ""


def extract_concise_spoken_summary(text: str, max_sentences: int = 2) -> str:
    """Extracts a short, compact, resourceful spoken summary (1-3 sentences) suitable for voice TTS."""
    cleaned = clean_markdown_for_speech(text)
    if not cleaned:
        action_summary = extract_action_spoken_summary(text)
        if action_summary:
            return action_summary
        return ""

    # Split into sentences
    sentences = re.split(r"(?<=[.!?])\s+", cleaned)
    selected = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 3]

    if not selected:
        action_summary = extract_action_spoken_summary(text)
        if action_summary:
            return action_summary
        return cleaned[:150]

    # Pick first 1-2 most informative sentences
    summary = " ".join(selected[:max_sentences])
    if len(summary) > 220:
        summary = summary[:217] + "..."
    return summary
