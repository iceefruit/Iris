"""Multi-Step Autonomous ReAct Loop with Visual Reflection and Verification."""

import time
from dataclasses import dataclass, field
from typing import Any, Dict, Generator, List, Optional, Tuple

from config import config
from core.client import MikoClient
from core.killswitch import GlobalPanicKillswitch
from core.protocols import StreamChunk
from tools.registry import ToolRegistry
from vision.engine import VisionEngine


@dataclass
class GoalStep:
    step_number: int
    thought: str
    tool_name: str
    tool_args: Dict[str, Any]
    result: str
    screenshot_path: Optional[str] = None


@dataclass
class GoalResult:
    goal: str
    status: str  # "COMPLETED" | "ABORTED" | "MAX_STEPS_REACHED" | "ERROR"
    total_steps: int
    steps: List[GoalStep] = field(default_factory=list)
    summary: str = ""


class AutonomousGoalRunner:
    """Orchestrates closed-loop visual goal solving through repeated Observe-Reason-Act steps."""

    def __init__(
        self,
        client: MikoClient,
        tools: ToolRegistry,
        vision_engine: VisionEngine,
        killswitch: GlobalPanicKillswitch,
    ):
        self.client = client
        self.tools = tools
        self.vision = vision_engine
        self.killswitch = killswitch

    def run(
        self,
        goal: str,
        max_steps: int = 8,
        cooldown_seconds: float = 0.5,
    ) -> Generator[Dict[str, Any], None, GoalResult]:
        """Executes an autonomous goal loop, yielding progress events at each step."""
        clean_goal = goal.strip()
        steps_history: List[GoalStep] = []

        # Reset killswitch state
        self.killswitch.reset()

        yield {
            "type": "goal_started",
            "goal": clean_goal,
            "max_steps": max_steps,
        }

        for step_num in range(1, max_steps + 1):
            if self.killswitch.is_aborted:
                yield {"type": "goal_aborted", "reason": "Killswitch triggered by user."}
                return GoalResult(
                    goal=clean_goal,
                    status="ABORTED",
                    total_steps=len(steps_history),
                    steps=steps_history,
                    summary="Execution stopped by Global Panic Killswitch.",
                )

            # 1. PERCEIVE: Capture fresh screen with coordinate grid
            _, img_path, win_ctx = self.vision.capture_with_context(
                user_query=clean_goal,
                with_grid=True,
            )

            # 2. Upload frame
            server_files = self.client.upload_files([img_path])

            # 3. Build trajectory context
            trajectory_lines = []
            for s in steps_history:
                trajectory_lines.append(
                    f"- Step {s.step_number}: Executed `{s.tool_name}` with {s.tool_args} -> Result: {s.result}"
                )
            trajectory_str = "\n".join(trajectory_lines) if trajectory_lines else "None (Starting step 1)"

            prompt = (
                f"{win_ctx.format_prompt_header()}\n"
                f"### ULTIMATE GOAL: \"{clean_goal}\"\n"
                f"### CURRENT PROGRESS: Step {step_num} of {max_steps}\n"
                f"### PREVIOUS ACTIONS TAKEN:\n{trajectory_str}\n\n"
                f"### INSTRUCTIONS:\n"
                f"1. Examine the visual screen frame (grid coordinates 0-1000) and current active window.\n"
                f"2. Decide the next concrete action to move closer to achieving the goal.\n"
                f"3. If the goal is fully accomplished, call `complete_goal` tool.\n\n"
                f"To execute an action, output an action block:\n"
                f"```action\n"
                f'{{\n  "tool": "tool_name",\n  "arguments": {{ ... }}\n}}\n'
                f"```\n"
                f"If the goal is finished:\n"
                f"```action\n"
                f'{{\n  "tool": "complete_goal",\n  "arguments": {{ "summary": "Detailed explanation of what was accomplished" }}\n}}\n'
                f"```"
            )

            yield {
                "type": "step_started",
                "step": step_num,
                "max_steps": max_steps,
                "screenshot": img_path,
                "active_app": win_ctx.process_name,
            }

            # 4. REASON: Call Miko with goal_prompt cognitive instructions
            sys_prompt = f"{config.system_prompt}\n\n{config.goal_prompt}\n\n{self.tools.format_system_prompt_tools()}"
            messages = [{"role": "user", "content": prompt}]

            response_accumulator = []
            thought_accumulator = []

            for chunk in self.client.stream_chat(
                messages=messages,
                service=config.vision_service,
                search=False,
                thinking=config.thinking,
                system_prompt=sys_prompt,
                files=server_files,
            ):
                if self.killswitch.is_aborted:
                    break
                if chunk.chunk_type == "content":
                    response_accumulator.append(chunk.text)
                    yield {"type": "content", "text": chunk.text}
                elif chunk.chunk_type == "thinking":
                    thought_accumulator.append(chunk.text)
                    yield {"type": "thinking", "text": chunk.text}

            if self.killswitch.is_aborted:
                return GoalResult(
                    goal=clean_goal,
                    status="ABORTED",
                    total_steps=len(steps_history),
                    steps=steps_history,
                    summary="Execution stopped by Global Panic Killswitch.",
                )

            full_reply = "".join(response_accumulator)
            actions = self.tools.extract_action_blocks(full_reply)

            if not actions:
                # No action block outputted -> record fallback step
                step_obj = GoalStep(
                    step_number=step_num,
                    thought="".join(thought_accumulator),
                    tool_name="none",
                    tool_args={},
                    result="Model provided textual answer without action.",
                    screenshot_path=img_path,
                )
                steps_history.append(step_obj)
                yield {"type": "step_finished", "step": step_obj}
                break

            # 5. ACT & OBSERVE
            executed_any_finish = False
            last_summary = ""

            for tool_name, args in actions:
                if tool_name == "complete_goal":
                    executed_any_finish = True
                    last_summary = args.get("summary") or "Goal completed successfully."
                    break

                yield {
                    "type": "action_executing",
                    "tool": tool_name,
                    "arguments": args,
                }

                res = self.tools.execute(tool_name, args)

                yield {
                    "type": "action_result",
                    "tool": tool_name,
                    "result": str(res),
                    "success": res.success,
                }

                # Visual Verification for GUI actions
                ver_observation = ""
                if tool_name in ("click", "type_text", "press_hotkey", "drag", "scroll"):
                    time.sleep(0.3)
                    _, post_img, _ = self.vision.capture_with_context(user_query=clean_goal, with_grid=False)
                    from core.verifier import VisualActionVerifier
                    ver_res = VisualActionVerifier.verify(
                        before_image_path=img_path,
                        after_image_path=post_img,
                        expected_tool=tool_name,
                    )
                    ver_observation = f" | Visual State: {ver_res.observation}"
                    yield {
                        "type": "visual_verification",
                        "outcome": ver_res.outcome.value,
                        "change_ratio": ver_res.change_ratio,
                        "observation": ver_res.observation,
                    }

                step_obj = GoalStep(
                    step_number=step_num,
                    thought="".join(thought_accumulator),
                    tool_name=tool_name,
                    tool_args=args,
                    result=(str(res) + ver_observation),
                    screenshot_path=img_path,
                )
                steps_history.append(step_obj)

            if executed_any_finish:
                yield {"type": "goal_completed", "summary": last_summary}
                return GoalResult(
                    goal=clean_goal,
                    status="COMPLETED",
                    total_steps=len(steps_history),
                    steps=steps_history,
                    summary=last_summary,
                )

            # Wait cooldown for UI updates
            time.sleep(cooldown_seconds)

        # Reached max steps
        yield {"type": "goal_max_steps", "steps": max_steps}
        return GoalResult(
            goal=clean_goal,
            status="MAX_STEPS_REACHED",
            total_steps=len(steps_history),
            steps=steps_history,
            summary=f"Reached maximum step limit ({max_steps}) without explicit completion.",
        )
