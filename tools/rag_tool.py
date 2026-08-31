"""RAG Indexing and Codebase Search Tools for Iris."""

from typing import Dict, Any, Optional
from core.rag import LocalRAGStore
from tools.base import BaseTool, ToolResult

# Shared global store
_global_rag_store = LocalRAGStore()


class IndexDirectoryTool(BaseTool):
    """Tool for recursively indexing files in a local directory into the RAG vector store."""

    name = "index_directory"
    description = (
        "Recursively scans and indexes code, markdown, and text files within a local folder "
        "into the Iris local RAG search database."
    )
    parameters = {
        "type": "object",
        "properties": {
            "folder_path": {
                "type": "string",
                "description": "Path to the directory or codebase to index (e.g. './' or 'C:/Projects/MyRepo').",
            },
            "max_files": {
                "type": "integer",
                "default": 100,
                "description": "Maximum number of files to index.",
            },
        },
        "required": ["folder_path"],
    }

    def execute(self, folder_path: str, max_files: int = 100, **kwargs) -> ToolResult:
        try:
            files_cnt, chunks_cnt = _global_rag_store.index_directory(
                folder_path=folder_path,
                max_files=max_files,
            )
            return ToolResult(
                success=True,
                output=f"Successfully indexed {files_cnt} file(s) into {chunks_cnt} search chunks from '{folder_path}'.",
            )
        except Exception as e:
            return ToolResult(success=False, output="", error=f"Indexing failed: {str(e)}")


class SearchKnowledgeBaseTool(BaseTool):
    """Tool for searching indexed codebase snippets, documents, and notes."""

    name = "search_knowledge_base"
    description = (
        "Searches local indexed files, codebase repositories, and notes for snippets "
        "matching a keyword or conceptual query."
    )
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query, function name, error message, or question.",
            },
            "top_k": {
                "type": "integer",
                "default": 5,
                "description": "Number of top matching snippets to retrieve.",
            },
        },
        "required": ["query"],
    }

    def execute(self, query: str, top_k: int = 5, **kwargs) -> ToolResult:
        try:
            results = _global_rag_store.search(query=query, top_k=top_k)
            if not results:
                return ToolResult(
                    success=True,
                    output=f"No indexed snippets found matching query '{query}'. Tip: Use `index_directory` to index your folders first.",
                )

            formatted_snippets = []
            for idx, r in enumerate(results, 1):
                snippet_text = (
                    f"### Result {idx} [Score: {r.score}] - `{r.file_path}:{r.start_line}-{r.end_line}`\n"
                    f"```\n{r.content.strip()}\n```"
                )
                formatted_snippets.append(snippet_text)

            return ToolResult(success=True, output="\n\n".join(formatted_snippets))
        except Exception as e:
            return ToolResult(success=False, output="", error=f"RAG search failed: {str(e)}")
