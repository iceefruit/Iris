"""Central Agent coordinator for Iris."""

from pathlib import Path
from typing import Generator, List, Optional, Dict, Any, Tuple
from core.protocols import LLMClientProtocol, MemoryProtocol, StreamChunk
from config import config


from core.killswitch import killswitch as default_killswitch, GlobalPanicKillswitch
from core.loop import AutonomousGoalRunner, GoalResult
from core.router import IntentRouter, IntentCategory, ParsedIntent
from tools.registry import default_registry, ToolRegistry
from vision.engine import VisionEngine


class IrisAgent:
    def __init__(
        self,
        client: LLMClientProtocol,
        memory: MemoryProtocol,
        tools: Optional[ToolRegistry] = None,
        killswitch: Optional[GlobalPanicKillswitch] = None,
        vision_engine: Optional[VisionEngine] = None,
    ):
        self.client = client
        self.memory = memory
        self.tools = tools or default_registry
        self.killswitch = killswitch or default_killswitch
        self.vision = vision_engine or VisionEngine()
        self.router = IntentRouter(client=self.client)
        self._goal_runner = AutonomousGoalRunner(
            client=self.client,
            tools=self.tools,
            vision_engine=self.vision,
            killswitch=self.killswitch,
        )

    def ask(
        self,
        user_input: str,
        file_paths: Optional[List[str]] = None,
        service: Optional[str] = None,
        execute_actions: bool = False,
    ) -> Generator[StreamChunk, None, None]:
        """Sends the user turn to Miko API and streams back chunk events.
        
        Miko API maintains conversational context on the server side using
        (username, userid). Thus, we send only the new prompt message to the API,
        while maintaining local memory for display and logging.
        """
        # Reset killswitch state for new turn
        if self.killswitch:
            self.killswitch.reset()

        # Store in local history
        self.memory.add_message(role="user", content=user_input)

        # Upload files if provided
        server_files = None
        if file_paths:
            server_files = self.client.upload_files(file_paths)

        # Use vision service if files are present and no explicit service passed
        effective_service = service or (config.vision_service if server_files else config.service)

        # System prompt with User Knowledge Vault + Tool Instructions
        sys_prompt = config.system_prompt
        if hasattr(self.memory, "format_vault_prompt"):
            vault_text = self.memory.format_vault_prompt()
            if vault_text:
                sys_prompt = f"{sys_prompt}\n\n{vault_text}"

        if execute_actions and self.tools:
            sys_prompt = f"{sys_prompt}\n\n{self.tools.format_system_prompt_tools()}"

        # If system prompt exceeds threshold (32k+ characters), upload as file
        if len(sys_prompt) > getattr(config, "max_inline_system_prompt_chars", 32000):
            cache_dir = Path(config.vision_cache_dir)
            cache_dir.mkdir(parents=True, exist_ok=True)
            sys_file = cache_dir / "system_instructions.txt"
            with open(sys_file, "w", encoding="utf-8") as f:
                f.write(sys_prompt)
            uploaded_sys = self.client.upload_files([str(sys_file)])
            server_files = (server_files or []) + uploaded_sys
            sys_prompt = (
                "CRITICAL SYSTEM INSTRUCTIONS AND TOOL SCHEMAS ARE ATTACHED IN THE UPLOADED FILE "
                "'system_instructions.txt'. Read and strictly follow all guidelines and tool definitions specified in this file."
            )

        # If user input exceeds threshold (16k+ characters), upload as file
        effective_user_input = user_input
        if len(user_input) > getattr(config, "max_inline_user_chars", 16000):
            cache_dir = Path(config.vision_cache_dir)
            cache_dir.mkdir(parents=True, exist_ok=True)
            user_file = cache_dir / f"user_doc_{hash(user_input) % 1000000}.txt"
            with open(user_file, "w", encoding="utf-8") as f:
                f.write(user_input)
            uploaded_user = self.client.upload_files([str(user_file)])
            server_files = (server_files or []) + uploaded_user
            effective_user_input = (
                "I have attached the long document/content in the uploaded file. "
                "Please analyze and fulfill the user request based on the attached document."
            )

        # Send only the new user message to Miko API as per Miko docs specification
        messages_payload = [{"role": "user", "content": effective_user_input}]

        full_response_accumulator = []

        try:
            for chunk in self.client.stream_chat(
                messages=messages_payload,
                service=effective_service,
                search=config.search,
                thinking=config.thinking,
                system_prompt=sys_prompt,
                files=server_files,
            ):
                if self.killswitch and self.killswitch.is_aborted:
                    yield StreamChunk(
                        chunk_type="error",
                        text="\n[CRITICAL: Operation aborted by Global Panic Killswitch.]"
                    )
                    return

                if chunk.chunk_type == "content":
                    full_response_accumulator.append(chunk.text)
                yield chunk

            # Store completed turn into local memory
            full_response = "".join(full_response_accumulator)
            if full_response:
                self.memory.add_message(role="assistant", content=full_response)

            # If actions are enabled, check and execute any parsed action blocks
            if execute_actions and full_response:
                actions = self.tools.extract_action_blocks(full_response)
                for tool_name, args in actions:
                    if self.killswitch and self.killswitch.is_aborted:
                        yield StreamChunk(
                            chunk_type="error",
                            text=f"\n[Action '{tool_name}' halted: Panic Killswitch triggered.]"
                        )
                        break

                    yield StreamChunk(
                        chunk_type="function_call",
                        text=f"Executing {tool_name}({args})",
                        metadata={"tool": tool_name, "args": args},
                    )
                    res = self.tools.execute(tool_name, args)
                    yield StreamChunk(
                        chunk_type="function_result",
                        text=str(res),
                        metadata=res.to_dict(),
                    )

        except Exception as e:
            error_chunk = StreamChunk(
                chunk_type="error",
                text=f"\n[Error communicating with Miko API: {str(e)}]"
            )
            yield error_chunk

    def run_goal(
        self,
        goal: str,
        max_steps: int = 8,
    ) -> Generator[Dict[str, Any], None, GoalResult]:
        """Runs an autonomous multi-step visual ReAct loop towards achieving a desktop goal."""
        return self._goal_runner.run(goal=goal, max_steps=max_steps)

    def process_input(
        self,
        user_input: str,
    ) -> Generator[Dict[str, Any], None, None]:
        """Automatically classifies natural language input and dispatches to the right subsystem."""
        intent = self.router.route(user_input)

        yield {
            "type": "intent_detected",
            "category": intent.category.value,
            "query": intent.clean_query,
        }

        # 1. MEMORY FACT
        if intent.category == IntentCategory.MEMORY and intent.memory_key and intent.memory_value:
            if hasattr(self.memory, "remember_fact"):
                self.memory.remember_fact(intent.memory_key, intent.memory_value)
                yield {
                    "type": "memory_stored",
                    "key": intent.memory_key,
                    "value": intent.memory_value,
                }
                return

        # 2. MULTI-STEP RE-ACT GOAL
        if intent.category == IntentCategory.GOAL:
            for goal_event in self.run_goal(goal=intent.clean_query, max_steps=8):
                yield goal_event
            return

        # 3. SINGLE DESKTOP ACTION (Needs Screen + Actuator)
        if intent.category == IntentCategory.ACTION:
            _, img_path, win_ctx = self.vision.capture_with_context(
                user_query=intent.clean_query,
                with_grid=True,
            )
            yield {
                "type": "vision_context",
                "app": win_ctx.process_name,
                "title": win_ctx.active_window_title,
                "screenshot": img_path,
            }
            for chunk in self.ask(
                user_input=f"{config.actuator_prompt}\n\nTask: {intent.clean_query}",
                file_paths=[img_path],
                execute_actions=True,
            ):
                yield {
                    "type": "chunk",
                    "chunk_type": chunk.chunk_type,
                    "text": chunk.text,
                    "metadata": chunk.metadata,
                }
            return

        # 4. SCREEN VISION INQUIRY (Needs Screen, Read-Only)
        if intent.category == IntentCategory.VISION:
            _, img_path, win_ctx = self.vision.capture_with_context(
                user_query=intent.clean_query,
                with_grid=False,
            )
            yield {
                "type": "vision_context",
                "app": win_ctx.process_name,
                "title": win_ctx.active_window_title,
                "screenshot": img_path,
            }
            for chunk in self.ask(
                user_input=f"{config.vision_prompt}\n\nQuestion: {intent.clean_query}",
                file_paths=[img_path],
                execute_actions=False,
            ):
                yield {
                    "type": "chunk",
                    "chunk_type": chunk.chunk_type,
                    "text": chunk.text,
                    "metadata": chunk.metadata,
                }
            return

        # 5. CHAT (Conversational / Web Search)
        for chunk in self.ask(
            user_input=intent.clean_query,
            execute_actions=False,
        ):
            yield {
                "type": "chunk",
                "chunk_type": chunk.chunk_type,
                "text": chunk.text,
                "metadata": chunk.metadata,
            }

    def clear(self) -> bool:
        """Clears both local context window and Miko server-side session memory."""
        self.memory.clear()
        return self.client.clear_history()
