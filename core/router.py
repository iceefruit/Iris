"""Intent Router and Classifier for zero-prefix natural language execution in Iris."""

import json
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional, Tuple

from config import config
from core.client import MikoClient


class IntentCategory(str, Enum):
    GOAL = "GOAL"            # Multi-step autonomous ReAct workflow
    ACTION = "ACTION"        # Single OS/desktop actuator action
    VISION = "VISION"        # Screen inspection / active window inquiry
    MEMORY = "MEMORY"        # Remembering facts or user preferences
    CHAT = "CHAT"            # General conversational or coding question


@dataclass
class ParsedIntent:
    category: IntentCategory
    clean_query: str
    memory_key: Optional[str] = None
    memory_value: Optional[str] = None
    confidence: float = 1.0


class IntentRouter:
    """Classifies raw user input into the appropriate execution mode."""

    def __init__(self, client: Optional[MikoClient] = None):
        self.client = client

    def route(self, user_input: str) -> ParsedIntent:
        """Determines the target intent using fast-path regex rules or semantic fallback."""
        text = user_input.strip()
        lower = text.lower()

        # 1. Check explicit slash command prefixes
        if lower.startswith("/goal"):
            parts = text.split(" ", 1)
            return ParsedIntent(
                category=IntentCategory.GOAL,
                clean_query=parts[1] if len(parts) > 1 else "",
            )
        if lower.startswith(("/act", "/action")):
            parts = text.split(" ", 1)
            return ParsedIntent(
                category=IntentCategory.ACTION,
                clean_query=parts[1] if len(parts) > 1 else "",
            )
        if lower.startswith(("/screen", "/vision")):
            parts = text.split(" ", 1)
            return ParsedIntent(
                category=IntentCategory.VISION,
                clean_query=parts[1] if len(parts) > 1 else "",
            )
        if lower.startswith("/remember"):
            parts = text.split(" ", 1)
            body = parts[1] if len(parts) > 1 else ""
            if "=" in body:
                k, v = body.split("=", 1)
                return ParsedIntent(
                    category=IntentCategory.MEMORY,
                    clean_query=text,
                    memory_key=k.strip(),
                    memory_value=v.strip(),
                )
            return ParsedIntent(category=IntentCategory.MEMORY, clean_query=body)

        # 2. Fast-Path Pattern Matching for Memory Facts
        remember_match = re.search(
            r"^(?:please\s+)?remember\s+(?:that\s+)?(?:my\s+)?(.+?)\s+(?:is|=|as)\s+(.+)$",
            text,
            re.IGNORECASE,
        )
        if remember_match:
            k, v = remember_match.group(1).strip(), remember_match.group(2).strip()
            return ParsedIntent(
                category=IntentCategory.MEMORY,
                clean_query=text,
                memory_key=k,
                memory_value=v,
            )

        # 3. Fast-Path Pattern Matching for Multi-Step Goals
        # Patterns like: "open X and play Y", "go to X server and tell Y", "search for X and save to Y"
        goal_conjunctions = [
            r"\b(?:open|launch|start|switch to|go to)\b.+\b(?:and|then)\b.+\b(?:play|click|search|type|find|save|write|tell|send|ping|message)\b",
            r"\b(?:search|google|find)\b.+\b(?:and|then)\b.+\b(?:save|download|write|copy|open)\b",
            r"\b(?:create|make|write)\b.+\b(?:and|then)\b.+\b(?:run|execute|save|open)\b",
            r"\b(?:go to|browse to|open|switch to)\b.+\b(?:server|channel|discord|slack|browser|chat)\b.+\b(?:and|then)?\b.+\b(?:tell|message|send|ping|write|say|post)\b",
            r"\b(?:send|post|type|message|tell|ping)\b.+\b(?:in|on|to)\b.+\b(?:discord|server|channel|chat)\b",
        ]
        for pattern in goal_conjunctions:
            if re.search(pattern, lower):
                return ParsedIntent(category=IntentCategory.GOAL, clean_query=text)

        # 4. Fast-Path Pattern Matching for Single Desktop Actions
        action_patterns = [
            r"^(?:click|double click|right click|move mouse|scroll down|scroll up|press|type)\b",
            r"^(?:open url|browse to|open browser to)\b",
            r"^(?:launch|start|open)\s+(?:app|application|calculator|notepad|spotify|chrome|code|browser|settings|terminal)\b",
            r"^(?:play|pause|resume|skip|next song|next track|previous song|previous track)\b",
            r"^(?:play\s+.+\s+(?:on\s+spotify|music))\b",
            r"^(?:set volume|turn volume|volume up|volume down|mute|unmute|mute audio)\b",
            r"^(?:snap window|minimize|maximize|restore window|focus window|bring to front)\b",
            r"^(?:check|get|show)\s+(?:my\s+)?(?:cpu|ram|battery|system status|hardware)\b",
            r"^(?:take a screenshot|capture screen|show screen)\b",
            r"^(?:generate an image|create an image|draw a picture|generate art)\b",
        ]
        for pattern in action_patterns:
            if re.search(pattern, lower):
                return ParsedIntent(category=IntentCategory.ACTION, clean_query=text)

        # 5. Fast-Path Pattern Matching for Screen Vision Inquiries
        vision_patterns = [
            r"\b(?:on my screen|on the screen|look at my screen|what's on my screen|read this error|what error is showing)\b",
            r"\b(?:active window|foreground window|current app|what window is open)\b",
        ]
        for pattern in vision_patterns:
            if re.search(pattern, lower):
                return ParsedIntent(category=IntentCategory.VISION, clean_query=text)

        # 6. Default to CHAT (Conversational / Coding / Web Search)
        return ParsedIntent(category=IntentCategory.CHAT, clean_query=text)
