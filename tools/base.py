"""Base interfaces and result containers for Iris tools."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class ToolResult:
    """Standardized output structure for tool execution."""
    success: bool
    output: str
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
        }

    def __str__(self) -> str:
        if self.success:
            return self.output
        return f"Error: {self.error or 'Action failed'}"


class BaseTool(ABC):
    """Abstract base class for all Iris actuator and system tools."""

    name: str = ""
    description: str = ""
    parameters: Dict[str, Any] = {}

    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        """Executes the tool logic with given arguments."""
        pass

    def to_schema(self) -> Dict[str, Any]:
        """Returns standard OpenAI / Miko function schema."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }
